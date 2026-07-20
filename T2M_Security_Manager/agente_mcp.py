# -*- coding: utf-8 -*-
"""
agente_mcp.py - Cliente MCP REAL para o T2M Security Manager.

Sobe o servidor Playwright MCP (Microsoft) como processo local, conecta via
stdio/JSON-RPC e roda um loop agentic onde a IA (Claude / Gemini / OpenAI)
chama as ferramentas do navegador de verdade (navigate, snapshot, click,
type, screenshot...) e reage ao estado real da pagina, ate concluir o objetivo.

Entrada (via STDIN, mesmo contrato do gerador_ia.py):
    linha 1 = chave de API   (AIza... | sk-ant-... | sk-...)
    linha 2 = URL alvo
    resto   = objetivo em linguagem natural (ex.: "Teste o login e verifique
              se campos aceitam SQL injection")

Saida (via STDOUT, mesmos marcadores que o C++ ja entende):
    CHAT_MSG_INICIO
    <relatorio final da IA>
    CHAT_MSG_FIM

Logs de progresso vao para STDERR para NAO poluir o parsing do C++.

Requisitos:
    Node.js 18+  ->  npx playwright install chromium
    pip install mcp anthropic google-generativeai openai
"""

import sys
import os
import json
import asyncio
import platform
import time

# Arquivo de memoria COMPARTILHADO com o chat (gerador_ia.py). Ambos usam o
# mesmo caminho (diretorio do proprio script) para que o agente MCP e o chat
# enxerguem a mesma conversa. E assim o agente "lembra" do que viu ao vivo.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_MEMORIA = os.path.join(SCRIPT_DIR, "memoria_chat.json")

# Instrucao comum aos tres provedores sobre relatorio + escolha de linguagem do script.
INSTRUCAO_LINGUAGEM = (
    "Ao final, escreva um relatorio claro do que testou e do que encontrou. Se fizer "
    "sentido gerar um script que reproduza o teste, escolha a linguagem mais adequada ao "
    "caso, PREFERINDO Robot Framework ou Python (padrao de trabalho em QA); use outra "
    "linguagem apenas se for claramente mais apropriada. Coloque o codigo em blocos "
    "```linguagem ... ```. Se a pagina nao suportar o objetivo (ex.: nao existe login), "
    "diga isso com clareza em vez de inventar um teste."
)

# ------------------------------------------------------------------ #
# Constantes de seguranca (guardrails de custo - recomendacao 2026)  #
# ------------------------------------------------------------------ #
MAX_TOKENS = 2048           # teto por resposta do modelo


def _carregar_configuracoes():
    """Le configuracoes.txt (chave=valor) gravado pelo app e devolve um dict.
    Permite ao usuario ajustar limites pela tela de Configuracoes."""
    cfg = {}
    try:
        # Preferencia: pasta gravavel do usuario (mesma que o app usa apos instalado).
        # Fallback: ao lado do script (modo de desenvolvimento).
        appdata = os.environ.get("APPDATA", "")
        candidatos = []
        if appdata:
            candidatos.append(os.path.join(appdata, "T2M Security Manager", "configuracoes.txt"))
        candidatos.append(os.path.join(SCRIPT_DIR, "configuracoes.txt"))
        caminho = next((c for c in candidatos if os.path.exists(c)), candidatos[-1])
        if os.path.exists(caminho):
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "=" in linha:
                        chave, valor = linha.split("=", 1)
                        cfg[chave.strip()] = valor.strip()
    except Exception:
        pass
    return cfg


def _cfg_int(cfg, chave, padrao, minimo, maximo):
    try:
        v = int(cfg.get(chave, padrao))
        return max(minimo, min(maximo, v))
    except Exception:
        return padrao


_CFG = _carregar_configuracoes()
MAX_ITERACOES = _cfg_int(_CFG, "max_passos", 15, 1, 60)      # teto de passos (custo)
MAX_LINHAS = _cfg_int(_CFG, "max_linhas", 100, 1, 5000)      # linhas por consulta
TIMEOUT_OPERACAO = _cfg_int(_CFG, "timeout", 120, 10, 3600)  # segundos

# Modelos usados por provedor. Configuraveis para o usuario equilibrar custo x capacidade.
# ATENCAO: modelos antigos (ex.: claude-3-5-sonnet) foram aposentados e falham se usados.
MODELO_CLAUDE = _CFG.get("modelo_claude", "claude-sonnet-5").strip() or "claude-sonnet-5"
MODELO_OPENAI = _CFG.get("modelo_openai", "gpt-4o-mini").strip() or "gpt-4o-mini"
HEADLESS = False            # False = voce ve o navegador agindo; True = invisivel


def log(msg):
    """Progresso vai para stderr, nunca para stdout (que o C++ le)."""
    print(msg, file=sys.stderr, flush=True)


def responder(texto):
    """Formato que a interface C++ espera no stdout."""
    print("CHAT_MSG_INICIO")
    print(texto)
    print("CHAT_MSG_FIM")


def tem_lib(modulo):
    try:
        __import__(modulo)
        return True
    except ImportError:
        return False


# ------------------------------------------------------------------ #
# Conversao de schema MCP -> Gemini (o velho clean_schema, agora util)#
# Gemini nao aceita algumas chaves do JSON Schema.                    #
# ------------------------------------------------------------------ #
def limpar_schema_gemini(schema):
    """
    O SDK antigo google.generativeai so aceita um subconjunto pequeno do JSON
    Schema. Em vez de listar campos proibidos (e descobrir um novo a cada erro),
    usamos uma WHITELIST: so passam os campos que o Gemini reconhece. Qualquer
    campo exotico (propertyNames, anyOf, $ref, etc.) e removido automaticamente.
    """
    if not isinstance(schema, dict):
        return schema

    permitidas = {"type", "description", "properties", "items",
                  "required", "enum", "nullable"}

    limpo = {}
    for k, v in schema.items():
        if k not in permitidas:
            continue
        if k == "properties" and isinstance(v, dict):
            # Limpa recursivamente cada propriedade
            limpo[k] = {nome: limpar_schema_gemini(sub) for nome, sub in v.items()}
        elif isinstance(v, dict):
            limpo[k] = limpar_schema_gemini(v)
        elif isinstance(v, list):
            limpo[k] = [limpar_schema_gemini(i) if isinstance(i, dict) else i for i in v]
        else:
            limpo[k] = v

    # Se sobrou um 'properties' vazio de type object, mantem coerencia
    if limpo.get("type") == "object" and "properties" not in limpo:
        limpo["properties"] = {}
    return limpo


def texto_do_resultado_mcp(resultado):
    """Extrai texto legivel do CallToolResult do MCP."""
    partes = []
    for bloco in getattr(resultado, "content", []) or []:
        t = getattr(bloco, "text", None)
        if t:
            partes.append(t)
    texto = "\n".join(partes) if partes else "(sem conteudo textual)"
    return texto[:8000]  # teto para nao estourar o contexto do modelo


# ================================================================== #
# LOOP ANTHROPIC (Claude) - tool-use nativo                          #
# ================================================================== #
async def loop_anthropic(session, api_key, objetivo, mcp_tools):
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    ferramentas = [{
        "name": t.name,
        "description": (t.description or "")[:1024],
        "input_schema": t.inputSchema,
    } for t in mcp_tools]

    system = ("Voce e um assistente de automacao de testes, QA e seguranca. Use as "
              "ferramentas de navegador para cumprir o objetivo passo a passo, observando o "
              "estado real da pagina antes de cada acao. Ao final, escreva um relatorio claro do que testou e do que encontrou. Se fizer sentido gerar um script que reproduza o teste, escolha a linguagem mais adequada ao caso, PREFERINDO Robot Framework ou Python (padrao de trabalho em QA); use outra linguagem apenas se for claramente mais apropriada. Coloque o codigo em blocos ```linguagem ... ```. Se a pagina nao suportar o objetivo (ex.: nao existe login), diga isso com clareza em vez de inventar um teste.")

    mensagens = [{"role": "user", "content": objetivo}]

    for passo in range(MAX_ITERACOES):
        resp = client.messages.create(
            model=MODELO_CLAUDE,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=ferramentas,
            messages=mensagens,
        )
        mensagens.append({"role": "assistant", "content": resp.content})

        usos = [b for b in resp.content if b.type == "tool_use"]
        if not usos:
            texto = "".join(b.text for b in resp.content if b.type == "text")
            return texto.strip() or "(sem resposta final)"

        resultados = []
        for uso in usos:
            log(f">>> [Claude] Ferramenta: {uso.name} {json.dumps(uso.input)[:120]}")
            try:
                r = await session.call_tool(uso.name, uso.input or {})
                conteudo = texto_do_resultado_mcp(r)
            except Exception as e:
                conteudo = f"ERRO ao executar {uso.name}: {e}"
            resultados.append({
                "type": "tool_result",
                "tool_use_id": uso.id,
                "content": conteudo,
            })
        mensagens.append({"role": "user", "content": resultados})

    return "Limite de iteracoes atingido antes de concluir o objetivo."


# ================================================================== #
# LOOP OPENAI (GPT)                                                  #
# ================================================================== #
async def loop_openai(session, api_key, objetivo, mcp_tools):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    ferramentas = [{
        "type": "function",
        "function": {
            "name": t.name,
            "description": (t.description or "")[:1024],
            "parameters": t.inputSchema,
        }
    } for t in mcp_tools]

    mensagens = [
        {"role": "system", "content": (
            "Voce e um Arquiteto de Automacao e Seguranca (QA). Use as ferramentas de "
            "navegador para cumprir o objetivo, observando o estado real da pagina. Ao "
            "Ao final, escreva um relatorio claro do que testou e do que encontrou. Se fizer sentido gerar um script que reproduza o teste, escolha a linguagem mais adequada ao caso, PREFERINDO Robot Framework ou Python (padrao de trabalho em QA); use outra linguagem apenas se for claramente mais apropriada. Coloque o codigo em blocos ```linguagem ... ```. Se a pagina nao suportar o objetivo (ex.: nao existe login), diga isso com clareza em vez de inventar um teste.")},
        {"role": "user", "content": objetivo},
    ]

    for passo in range(MAX_ITERACOES):
        resp = client.chat.completions.create(
            model=MODELO_OPENAI,
            tools=ferramentas,
            messages=mensagens,
            max_tokens=MAX_TOKENS,
        )
        msg = resp.choices[0].message
        mensagens.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return (msg.content or "(sem resposta final)").strip()

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            log(f">>> [GPT] Ferramenta: {tc.function.name} {json.dumps(args)[:120]}")
            try:
                r = await session.call_tool(tc.function.name, args)
                conteudo = texto_do_resultado_mcp(r)
            except Exception as e:
                conteudo = f"ERRO ao executar {tc.function.name}: {e}"
            mensagens.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": conteudo,
            })

    return "Limite de iteracoes atingido antes de concluir o objetivo."


# ================================================================== #
# LOOP GEMINI (SDK google.generativeai - autentica chaves AQ./AIza)  #
# O SDK novo (google.genai) rejeita chaves AQ. com 401, entao usamos #
# o SDK classico aqui, com tratamento reforcado do                   #
# MALFORMED_FUNCTION_CALL (retry) e deteccao de navegador fechado.   #
# ================================================================== #
async def loop_gemini(session, api_key, objetivo, mcp_tools):
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    # Converte as ferramentas MCP para o formato do Gemini (whitelist de schema).
    declaracoes = []
    for t in mcp_tools:
        params = limpar_schema_gemini(t.inputSchema or {"type": "object", "properties": {}})
        if not isinstance(params, dict):
            params = {"type": "object", "properties": {}}
        if "type" not in params:
            params["type"] = "object"
        if params.get("type") == "object" and "properties" not in params:
            params["properties"] = {}
        declaracoes.append({
            "name": t.name,
            "description": (t.description or "")[:1024],
            "parameters": params,
        })
    tools_gemini = [{"function_declarations": declaracoes}]

    system = ("Voce e um assistente de automacao de testes, QA e seguranca. Use as "
              "ferramentas de navegador para cumprir o objetivo, observando o estado real "
              "da pagina antes de cada acao. Chame UMA ferramenta por vez, com argumentos "
              "simples e validos. " + INSTRUCAO_LINGUAGEM)

    # No tier gratuito o limite por minuto e baixo (ex.: 5-10 req/min). Uma automacao
    # MCP faz varias chamadas seguidas, entao: (1) preferimos modelos com mais folga,
    # (2) pausamos entre passos, (3) tratamos ResourceExhausted com mensagem clara.
    modelos_tentar = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    model = None
    erro_modelo = ""
    for nome_m in modelos_tentar:
        try:
            model = genai.GenerativeModel(
                nome_m,
                tools=tools_gemini,
                system_instruction=system,
            )
            log(f">>> [Gemini] Usando modelo {nome_m}")
            break
        except Exception as e:
            erro_modelo = f"{nome_m}: {type(e).__name__}: {e}"
            continue
    if model is None:
        return f"Falha ao registrar ferramentas no Gemini: {erro_modelo}"

    chat = model.start_chat()
    proxima_mensagem = objetivo
    ultimo_texto = ""          # guarda o ultimo texto util, para devolver algo se travar
    navegador_morto = False

    for passo in range(MAX_ITERACOES):
        # Pausa entre passos para respeitar o limite por minuto do tier gratuito
        # (evita ResourceExhausted no meio da automacao). Nao pausa no 1o passo.
        if passo > 0:
            time.sleep(4)

        # --- Envia a mensagem, com RETRY em caso de MALFORMED / cota ---
        resp = None
        for tentativa in range(3):  # tentativas extras para cota (espera e refaz)
            try:
                resp = chat.send_message(proxima_mensagem)
                break
            except Exception as e:
                nome_erro = type(e).__name__
                msg = str(e)
                # Cota por minuto estourada: espera e tenta de novo
                if ("ResourceExhausted" in nome_erro or "429" in msg
                        or "quota" in msg.lower() or "exhausted" in msg.lower()):
                    if tentativa < 2:
                        log(f">>> Limite por minuto atingido. Aguardando 30s para retomar (tentativa {tentativa+1})...")
                        time.sleep(30)
                        continue
                    # Esgotou as tentativas de cota
                    if ultimo_texto:
                        return (ultimo_texto + "\n\n[Automacao interrompida: limite de uso "
                                "da IA (cota gratuita por minuto) atingido. Aguarde 1 minuto "
                                "e tente de novo, ou ative billing para limites maiores.]")
                    return ("Limite de uso da IA atingido (cota gratuita: poucas requisicoes "
                            "por minuto). Aguarde 1-2 minutos e tente de novo, ou ative billing "
                            "no Google AI Studio para limites maiores.")
                if "MALFORMED_FUNCTION_CALL" in msg or "finish_reason" in msg:
                    log(f">>> MALFORMED na tentativa {tentativa+1}, tentando de novo...")
                    if tentativa < 2:
                        proxima_mensagem = ("A ultima acao falhou por chamada malformada. "
                                            "Refaca chamando UMA ferramenta simples por vez.")
                        continue
                # Erro que nao da para recuperar
                if ultimo_texto:
                    return (ultimo_texto + "\n\n[Nota: a automacao foi interrompida por "
                            f"instabilidade do modelo: {nome_erro}]")
                return f"O modelo Gemini falhou ({nome_erro}). Tente de novo ou use outra chave/IA."
        if resp is None:
            break

        # --- Coleta as chamadas de ferramenta pedidas ---
        chamadas = []
        try:
            for cand in resp.candidates:
                for parte in cand.content.parts:
                    fc = getattr(parte, "function_call", None)
                    if fc and fc.name:
                        chamadas.append(fc)
        except Exception:
            pass

        # Sem chamadas = resposta final em texto
        if not chamadas:
            try:
                return (resp.text or ultimo_texto or "(sem resposta final)").strip()
            except Exception:
                return ultimo_texto or "(sem resposta final)"

        # --- Executa cada ferramenta no navegador via MCP ---
        respostas_fc = []
        for fc in chamadas:
            args = dict(fc.args) if fc.args else {}
            log(f">>> [Gemini] Ferramenta: {fc.name} {json.dumps(args)[:120]}")
            try:
                r = await session.call_tool(fc.name, args)
                conteudo = texto_do_resultado_mcp(r)
                if conteudo and len(conteudo) > 40:
                    ultimo_texto = conteudo  # guarda progresso util
            except Exception as e:
                # Navegador fechado / MCP caiu: nao adianta continuar
                emsg = str(e)
                conteudo = f"ERRO ao executar {fc.name}: {emsg}"
                if ("closed" in emsg.lower() or "target" in emsg.lower()
                        or "connection" in emsg.lower() or "browser" in emsg.lower()):
                    navegador_morto = True
                    log(f">>> Navegador parece ter sido fechado: {emsg[:100]}")
            respostas_fc.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=fc.name, response={"resultado": conteudo})))

        if navegador_morto:
            return (ultimo_texto + "\n\n[Automacao interrompida: o navegador foi fechado "
                    "antes do fim do teste.]") if ultimo_texto else \
                   "Automacao interrompida: o navegador foi fechado antes do fim do teste."

        proxima_mensagem = respostas_fc

    return (ultimo_texto + "\n\n[Limite de passos atingido.]") if ultimo_texto else \
           "Limite de iteracoes atingido antes de concluir o objetivo."


# ================================================================== #
# (bloco antigo do SDK novo removido - chave AQ. dava 401)           #
# ================================================================== #


# ================================================================== #
# ORQUESTRACAO: sobe o Playwright MCP e roteia pelo provedor         #
# ================================================================== #
async def executar(api_key, url_alvo, objetivo):
    if not tem_lib("mcp"):
        responder("Biblioteca ausente: mcp. Rode: pip install mcp")
        return

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    # Windows precisa de npx.cmd; outros SOs usam npx
    comando_npx = "npx.cmd" if platform.system() == "Windows" else "npx"
    args = ["@playwright/mcp@latest"]
    if HEADLESS:
        args.append("--headless")

    server_params = StdioServerParameters(command=comando_npx, args=args)

    log(">>> Subindo servidor Playwright MCP (Microsoft)...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_resp = await session.list_tools()
                mcp_tools = tools_resp.tools
                log(f">>> MCP conectado. {len(mcp_tools)} ferramentas disponiveis.")

                objetivo_completo = (
                    f"URL alvo: {url_alvo}\n"
                    f"Comece navegando ate essa URL com a ferramenta de navegacao.\n"
                    f"Objetivo do teste: {objetivo}\n\n"
                    f"Depois de executar e relatar o que encontrou, PERGUNTE ao usuario qual "
                    f"tipo de automacao ele quer construir a partir disto: (1) navegacao web, "
                    f"(2) API, ou (3) banco de dados/SQL (peca credenciais se necessario). "
                    f"So gere o script final quando tiver as informacoes necessarias.")

                # Roteador por provedor. Ordem importa: prefixos mais especificos
                # primeiro. Gemini fica como padrao porque o Google mudou o formato
                # da chave (AIza -> AQ.) e pode mudar de novo; validar so "AIza"
                # quebraria com chaves novas. Ver: prefixos AIza, AQ., AQ_ e afins.
                if api_key.startswith("sk-ant-"):
                    if not tem_lib("anthropic"):
                        responder("Biblioteca ausente: anthropic.")
                        return
                    resultado = await loop_anthropic(session, api_key, objetivo_completo, mcp_tools)
                elif api_key.startswith("sk-"):
                    if not tem_lib("openai"):
                        responder("Biblioteca ausente: openai.")
                        return
                    resultado = await loop_openai(session, api_key, objetivo_completo, mcp_tools)
                else:
                    # Gemini: aceita AIza (classico), AQ./AQ_ (novo formato 2026)
                    # e qualquer outro que nao seja Claude/OpenAI.
                    if not tem_lib("google.generativeai"):
                        responder("Biblioteca ausente: google-generativeai. Rode: pip install google-generativeai")
                        return
                    resultado = await loop_gemini(session, api_key, objetivo_completo, mcp_tools)

                # --- INTEGRACAO COM O CHAT: grava o resultado na memoria compartilhada ---
                # Assim o proximo turno do chat (gerador_ia.py) "lembra" do que o MCP fez.
                # O relatorio entra como uma fala do assistente, precedida de uma nota
                # de contexto (como se o operador tivesse pedido a automacao ao vivo).
                try:
                    memoria = []
                    if os.path.exists(ARQUIVO_MEMORIA):
                        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
                            memoria = json.load(f)
                    memoria.append({
                        "role": "user",
                        "content": f"[AUTOMACAO MCP AO VIVO] Executei uma automacao real no "
                                   f"navegador sobre {url_alvo} com o objetivo: {objetivo}"
                    })
                    memoria.append({"role": "assistant", "content": resultado})
                    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
                        json.dump(memoria, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    log(f">>> Aviso: nao foi possivel gravar na memoria do chat: {e}")

                responder(resultado)
        responder("Erro: 'npx' (Node.js) nao encontrado. Instale o Node 18+ de nodejs.org.")
    except BaseException as e:
        # ExceptionGroup (TaskGroup) esconde a causa real; desempacota para mostrar.
        import traceback
        reais = []

        def _coletar(exc):
            sub = getattr(exc, "exceptions", None)
            if sub:
                for x in sub:
                    _coletar(x)
            else:
                reais.append(f"{type(exc).__name__}: {exc}")

        _coletar(e)
        detalhe = " | ".join(reais) if reais else f"{type(e).__name__}: {e}"
        log("=== TRACEBACK COMPLETO ===")
        log(traceback.format_exc())
        responder(f"ERRO no agente MCP: {detalhe}")


async def executar_banco(api_key, dsn, somente_leitura, objetivo):
    """Sobe o servidor MCP de banco (DBHub) e deixa a IA executar o objetivo via SQL.
    dsn: string de conexao, ex.: postgres://user:senha@host:5432/db
    somente_leitura: se True, o DBHub roda em modo --readonly (so SELECT)."""
    if not tem_lib("mcp"):
        responder("Biblioteca ausente: mcp. Rode: pip install mcp")
        return

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    comando_npx = "npx.cmd" if platform.system() == "Windows" else "npx"
    # DBHub via npx, transporte stdio. --dsn passa a conexao. --readonly = so leitura.
    args = ["-y", "@bytebase/dbhub", "--transport", "stdio", "--dsn", dsn]
    if somente_leitura:
        args.append("--readonly")

    server_params = StdioServerParameters(command=comando_npx, args=args)

    log(">>> Subindo servidor DBHub (banco de dados) via MCP...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_resp = await session.list_tools()
                mcp_tools = tools_resp.tools
                log(f">>> DBHub conectado. {len(mcp_tools)} ferramentas disponiveis.")

                modo_ro = ("O banco esta em modo SOMENTE LEITURA (apenas consultas SELECT). "
                           if somente_leitura else
                           "O banco permite leitura e escrita; seja cuidadoso com operacoes "
                           "destrutivas (INSERT/UPDATE/DELETE/DROP) e confirme antes. ")
                objetivo_completo = (
                    f"Voce esta conectado a um banco de dados via ferramentas MCP. {modo_ro}"
                    f"Primeiro explore o schema (liste tabelas e colunas) antes de consultar. "
                    f"Objetivo do usuario: {objetivo}\n\n"
                    f"Ao final, relate o que encontrou de forma clara. Se fizer sentido, gere "
                    f"um script de teste (SQL, ou Robot Framework com DatabaseLibrary, ou "
                    f"Python) dentro de blocos ```linguagem ... ```.")

                # Reusa os mesmos loops de IA do modo tela
                if api_key.startswith("sk-ant-"):
                    if not tem_lib("anthropic"):
                        responder("Biblioteca ausente: anthropic."); return
                    resultado = await loop_anthropic(session, api_key, objetivo_completo, mcp_tools)
                elif api_key.startswith("sk-"):
                    if not tem_lib("openai"):
                        responder("Biblioteca ausente: openai."); return
                    resultado = await loop_openai(session, api_key, objetivo_completo, mcp_tools)
                else:
                    if not tem_lib("google.generativeai"):
                        responder("Biblioteca ausente: google-generativeai."); return
                    resultado = await loop_gemini(session, api_key, objetivo_completo, mcp_tools)

                # Grava na memoria compartilhada com o chat
                try:
                    memoria = []
                    if os.path.exists(ARQUIVO_MEMORIA):
                        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
                            memoria = json.load(f)
                    memoria.append({
                        "role": "user",
                        "content": f"[AUTOMACAO BANCO DE DADOS] Executei uma consulta/teste no "
                                   f"banco com o objetivo: {objetivo}"
                    })
                    memoria.append({"role": "assistant", "content": resultado})
                    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
                        json.dump(memoria, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    log(f">>> Aviso: nao foi possivel gravar na memoria do chat: {e}")

                responder(resultado)
        responder("Erro: 'npx' (Node.js) nao encontrado. Instale o Node 18+ de nodejs.org.")
    except BaseException as e:
        import traceback
        reais = []

        def _coletar(exc):
            sub = getattr(exc, "exceptions", None)
            if sub:
                for x in sub:
                    _coletar(x)
            else:
                reais.append(f"{type(exc).__name__}: {exc}")

        _coletar(e)
        detalhe = " | ".join(reais) if reais else f"{type(e).__name__}: {e}"
        log("=== TRACEBACK COMPLETO (banco) ===")
        log(traceback.format_exc())
        # Mensagem amigavel para erros comuns de conexao
        dica = ""
        d = detalhe.lower()
        if "econnrefused" in d or "connection refused" in d:
            dica = " (o banco nao respondeu - verifique host/porta e se o servidor esta rodando)"
        elif "password" in d or "authentication" in d:
            dica = " (falha de autenticacao - verifique usuario/senha)"
        elif "not found" in d and "npx" in d:
            dica = " (Node.js/npx nao encontrado - instale o Node 18+)"
        responder(f"ERRO no agente de banco: {detalhe}{dica}")


def _fazer_requisicao_http(metodo, url, headers, body, timeout=None):
    """Executa uma requisicao HTTP real e devolve um dict com o resultado.
    Nao depende de servidor MCP: usa a lib requests localmente."""
    import requests
    if timeout is None:
        timeout = TIMEOUT_OPERACAO
    try:
        m = (metodo or "GET").upper()
        h = headers or {}
        # body pode ser string (json cru) ou dict
        data = None
        json_data = None
        if body:
            if isinstance(body, (dict, list)):
                json_data = body
            else:
                # tenta interpretar como JSON; se falhar, envia como texto
                try:
                    json_data = json.loads(body)
                except Exception:
                    data = body
        resp = requests.request(m, url, headers=h, json=json_data, data=data, timeout=timeout)
        # limita o corpo para nao estourar o contexto do modelo
        texto = resp.text[:6000] if resp.text else ""
        return {
            "status_code": resp.status_code,
            "ok": resp.ok,
            "headers": dict(resp.headers),
            "body": texto,
            "url_final": resp.url,
            "tempo_ms": int(resp.elapsed.total_seconds() * 1000),
        }
    except Exception as e:
        return {"erro": f"{type(e).__name__}: {e}"}


async def executar_api(api_key, req, objetivo):
    """Testa uma API HTTP. A IA recebe uma ferramenta 'fazer_requisicao_http'
    (mesmo padrao de tool-use das outras funcoes) e a usa para chamar a API e
    analisar a resposta. req = dict com metodo/url/headers/body iniciais."""
    if not tem_lib("requests"):
        responder("Biblioteca ausente: requests. Rode: pip install requests")
        return

    metodo0 = req.get("metodo", "GET")
    url0 = req.get("url", "")
    headers0 = req.get("headers", {})
    body0 = req.get("body", "")

    contexto_req = (
        f"Requisicao base montada pelo usuario:\n"
        f"  Metodo: {metodo0}\n  URL: {url0}\n"
        f"  Headers: {json.dumps(headers0, ensure_ascii=False)}\n"
        f"  Body: {body0 if body0 else '(vazio)'}\n\n")

    instrucao = (
        contexto_req +
        f"Objetivo do teste: {objetivo}\n\n"
        f"Use a ferramenta fazer_requisicao_http para executar a chamada (pode ajustar "
        f"metodo/url/headers/body conforme o objetivo). Analise status, headers e corpo, "
        f"e relate se a API se comportou como esperado. Se fizer sentido, gere um script "
        f"de teste (Python requests, Robot Framework RequestsLibrary, ou similar) em blocos "
        f"```linguagem ... ```.")

    # A ferramenta HTTP exposta a IA (mesmo schema para os 3 provedores)
    schema_http = {
        "type": "object",
        "properties": {
            "metodo": {"type": "string", "description": "GET, POST, PUT, DELETE, PATCH..."},
            "url": {"type": "string", "description": "URL completa do endpoint"},
            "headers": {"type": "object", "description": "Cabecalhos HTTP (opcional)"},
            "body": {"type": "string", "description": "Corpo da requisicao, JSON como texto (opcional)"},
        },
        "required": ["metodo", "url"],
    }

    log(">>> Modo API: ferramenta HTTP local pronta.")
    try:
        if api_key.startswith("sk-ant-"):
            if not tem_lib("anthropic"):
                responder("Biblioteca ausente: anthropic."); return
            resultado = await _loop_api_anthropic(api_key, instrucao, schema_http)
        elif api_key.startswith("sk-"):
            if not tem_lib("openai"):
                responder("Biblioteca ausente: openai."); return
            resultado = await _loop_api_openai(api_key, instrucao, schema_http)
        else:
            if not tem_lib("google.generativeai"):
                responder("Biblioteca ausente: google-generativeai."); return
            resultado = await _loop_api_gemini(api_key, instrucao, schema_http)

        # Grava na memoria compartilhada
        try:
            memoria = []
            if os.path.exists(ARQUIVO_MEMORIA):
                with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
                    memoria = json.load(f)
            memoria.append({"role": "user",
                            "content": f"[TESTE DE API] {metodo0} {url0} - objetivo: {objetivo}"})
            memoria.append({"role": "assistant", "content": resultado})
            with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
                json.dump(memoria, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log(f">>> Aviso: nao foi possivel gravar na memoria: {e}")

        responder(resultado)
    except Exception as e:
        import traceback
        log(traceback.format_exc())
        responder(f"ERRO no teste de API: {type(e).__name__}: {e}")


# --- Loops de API por provedor (ferramenta unica: fazer_requisicao_http) ---
async def _loop_api_anthropic(api_key, instrucao, schema_http):
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    ferramentas = [{"name": "fazer_requisicao_http",
                    "description": "Executa uma requisicao HTTP e retorna status, headers e corpo.",
                    "input_schema": schema_http}]
    mensagens = [{"role": "user", "content": instrucao}]
    for _ in range(MAX_ITERACOES):
        resp = client.messages.create(model=MODELO_CLAUDE,
                                      max_tokens=MAX_TOKENS, tools=ferramentas, messages=mensagens)
        mensagens.append({"role": "assistant", "content": resp.content})
        usos = [b for b in resp.content if b.type == "tool_use"]
        if not usos:
            return "".join(b.text for b in resp.content if b.type == "text").strip() or "(sem resposta)"
        resultados = []
        for uso in usos:
            r = _fazer_requisicao_http(uso.input.get("metodo"), uso.input.get("url"),
                                       uso.input.get("headers"), uso.input.get("body"))
            log(f">>> [Claude] HTTP {uso.input.get('metodo')} {uso.input.get('url')}")
            resultados.append({"type": "tool_result", "tool_use_id": uso.id,
                               "content": json.dumps(r, ensure_ascii=False)[:6000]})
        mensagens.append({"role": "user", "content": resultados})
    return "Limite de passos atingido no teste de API."


async def _loop_api_openai(api_key, instrucao, schema_http):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    ferramentas = [{"type": "function", "function": {
        "name": "fazer_requisicao_http",
        "description": "Executa uma requisicao HTTP e retorna status, headers e corpo.",
        "parameters": schema_http}}]
    mensagens = [{"role": "user", "content": instrucao}]
    for _ in range(MAX_ITERACOES):
        resp = client.chat.completions.create(model=MODELO_OPENAI, tools=ferramentas,
                                              messages=mensagens, max_tokens=MAX_TOKENS)
        msg = resp.choices[0].message
        mensagens.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            return (msg.content or "(sem resposta)").strip()
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            r = _fazer_requisicao_http(args.get("metodo"), args.get("url"),
                                       args.get("headers"), args.get("body"))
            log(f">>> [GPT] HTTP {args.get('metodo')} {args.get('url')}")
            mensagens.append({"role": "tool", "tool_call_id": tc.id,
                              "content": json.dumps(r, ensure_ascii=False)[:6000]})
    return "Limite de passos atingido no teste de API."


async def _loop_api_gemini(api_key, instrucao, schema_http):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    tools_gemini = [{"function_declarations": [{
        "name": "fazer_requisicao_http",
        "description": "Executa uma requisicao HTTP e retorna status, headers e corpo.",
        "parameters": limpar_schema_gemini(schema_http)}]}]
    modelos = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    model = None
    for nm in modelos:
        try:
            model = genai.GenerativeModel(nm, tools=tools_gemini); break
        except Exception:
            continue
    if model is None:
        return "Falha ao iniciar o modelo Gemini para o teste de API."
    chat = model.start_chat()
    proxima = instrucao
    ultimo = ""
    for passo in range(MAX_ITERACOES):
        if passo > 0:
            time.sleep(4)
        try:
            resp = chat.send_message(proxima)
        except Exception as e:
            if "ResourceExhausted" in type(e).__name__ or "429" in str(e):
                return (ultimo or "") + "\n[Limite de uso da IA atingido. Aguarde 1-2 min.]"
            return f"O modelo Gemini falhou: {type(e).__name__}"
        chamadas = []
        try:
            for cand in resp.candidates:
                for parte in cand.content.parts:
                    fc = getattr(parte, "function_call", None)
                    if fc and fc.name:
                        chamadas.append(fc)
        except Exception:
            pass
        if not chamadas:
            try:
                return (resp.text or ultimo or "(sem resposta)").strip()
            except Exception:
                return ultimo or "(sem resposta)"
        respostas = []
        for fc in chamadas:
            args = dict(fc.args) if fc.args else {}
            r = _fazer_requisicao_http(args.get("metodo"), args.get("url"),
                                       args.get("headers"), args.get("body"))
            ultimo = json.dumps(r, ensure_ascii=False)[:2000]
            log(f">>> [Gemini] HTTP {args.get('metodo')} {args.get('url')}")
            respostas.append(genai.protos.Part(function_response=genai.protos.FunctionResponse(
                name=fc.name, response={"resultado": r})))
        proxima = respostas
    return (ultimo or "") + "\n[Limite de passos atingido no teste de API.]"


def _oracle_abrir_conexao(info):
    """Abre conexao Oracle em thin mode (driver oficial, sem Instant Client)."""
    import oracledb
    host = info.get("host", "localhost")
    porta = int(info.get("porta") or 1521)
    servico = info.get("servico") or info.get("nome") or "XEPDB1"
    usuario = info.get("usuario", "")
    senha = info.get("senha", "")
    dsn = f"{host}:{porta}/{servico}"
    return oracledb.connect(user=usuario, password=senha, dsn=dsn)


def _oracle_ferramentas(somente_leitura):
    """Schemas das ferramentas Oracle expostas a IA."""
    return [
        {
            "name": "listar_tabelas",
            "description": "Lista as tabelas e views disponiveis no schema do usuario conectado.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "descrever_tabela",
            "description": "Mostra as colunas, tipos e nulidade de uma tabela.",
            "input_schema": {
                "type": "object",
                "properties": {"tabela": {"type": "string", "description": "Nome da tabela"}},
                "required": ["tabela"],
            },
        },
        {
            "name": "executar_sql",
            "description": ("Executa um comando SQL no Oracle e retorna as linhas."
                            + (" Somente SELECT e permitido (conexao somente-leitura)."
                               if somente_leitura else "")),
            "input_schema": {
                "type": "object",
                "properties": {"sql": {"type": "string", "description": "Comando SQL a executar"}},
                "required": ["sql"],
            },
        },
    ]


def _oracle_executar_ferramenta(conn, somente_leitura, nome, args, limite=None):
    """Executa uma ferramenta Oracle e devolve um dict com o resultado."""
    if limite is None:
        limite = MAX_LINHAS
    try:
        cur = conn.cursor()
        if nome == "listar_tabelas":
            cur.execute("SELECT table_name FROM user_tables ORDER BY table_name")
            tabelas = [linha[0] for linha in cur.fetchmany(200)]
            cur.close()
            return {"tabelas": tabelas, "total": len(tabelas)}

        if nome == "descrever_tabela":
            tabela = (args.get("tabela") or "").upper()
            cur.execute(
                "SELECT column_name, data_type, data_length, nullable "
                "FROM user_tab_columns WHERE table_name = :t ORDER BY column_id",
                t=tabela)
            colunas = [{"coluna": c[0], "tipo": c[1], "tamanho": c[2], "aceita_nulo": c[3] == "Y"}
                       for c in cur.fetchall()]
            cur.close()
            if not colunas:
                return {"erro": f"Tabela '{tabela}' nao encontrada no schema do usuario."}
            return {"tabela": tabela, "colunas": colunas}

        if nome == "executar_sql":
            sql = (args.get("sql") or "").strip().rstrip(";")
            if not sql:
                cur.close()
                return {"erro": "SQL vazio."}
            # Trava de seguranca: em modo somente-leitura, so SELECT/WITH passam
            primeira = sql.split()[0].upper() if sql.split() else ""
            if somente_leitura and primeira not in ("SELECT", "WITH"):
                cur.close()
                return {"erro": "Conexao em modo somente-leitura: apenas SELECT e permitido. "
                                f"Comando recusado: {primeira}"}
            cur.execute(sql)
            if cur.description is None:
                conn.commit()
                cur.close()
                return {"ok": True, "mensagem": "Comando executado (sem linhas de retorno)."}
            nomes = [d[0] for d in cur.description]
            linhas = [list(map(_oracle_valor_seguro, r)) for r in cur.fetchmany(limite)]
            cur.close()
            return {"colunas": nomes, "linhas": linhas, "exibidas": len(linhas)}

        cur.close()
        return {"erro": f"Ferramenta desconhecida: {nome}"}
    except Exception as e:
        return {"erro": f"{type(e).__name__}: {e}"}


def _oracle_valor_seguro(v):
    """Converte valores do banco para algo serializavel em JSON."""
    if v is None:
        return None
    if isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


async def executar_oracle(api_key, info, somente_leitura, objetivo):
    """Testa/consulta um banco Oracle usando o driver oficial (thin mode).
    A IA recebe ferramentas (listar/descrever/executar) no mesmo padrao de tool-use."""
    if not tem_lib("oracledb"):
        responder("Biblioteca ausente: oracledb (driver oficial da Oracle).\n"
                  "Instale com: pip install oracledb")
        return

    log(">>> Conectando ao Oracle (thin mode, driver oficial)...")
    try:
        conn = _oracle_abrir_conexao(info)
    except Exception as e:
        responder(f"Nao foi possivel conectar ao Oracle: {type(e).__name__}: {e}")
        return

    log(">>> Oracle conectado.")
    ferramentas = _oracle_ferramentas(somente_leitura)

    instrucao = (
        f"Voce esta conectado a um banco Oracle "
        f"({info.get('host')}:{info.get('porta')}/{info.get('servico') or info.get('nome')}) "
        f"em modo {'SOMENTE LEITURA' if somente_leitura else 'leitura e escrita'}.\n\n"
        f"Objetivo: {objetivo}\n\n"
        f"Use as ferramentas para explorar o schema e executar as consultas necessarias. "
        f"Explique os achados de forma clara e, se fizer sentido, gere um script SQL de teste "
        f"em blocos ```sql ... ```.")

    def despachar(nome, args):
        log(f">>> [Oracle] {nome} {args if args else ''}")
        return _oracle_executar_ferramenta(conn, somente_leitura, nome, args)

    try:
        if api_key.startswith("sk-ant-"):
            if not tem_lib("anthropic"):
                responder("Biblioteca ausente: anthropic."); return
            resultado = await _loop_ferramentas_anthropic(api_key, instrucao, ferramentas, despachar)
        elif api_key.startswith("sk-"):
            if not tem_lib("openai"):
                responder("Biblioteca ausente: openai."); return
            resultado = await _loop_ferramentas_openai(api_key, instrucao, ferramentas, despachar)
        else:
            if not tem_lib("google.generativeai"):
                responder("Biblioteca ausente: google-generativeai."); return
            resultado = await _loop_ferramentas_gemini(api_key, instrucao, ferramentas, despachar)

        try:
            memoria = []
            if os.path.exists(ARQUIVO_MEMORIA):
                with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
                    memoria = json.load(f)
            memoria.append({"role": "user", "content": f"[ORACLE] {objetivo}"})
            memoria.append({"role": "assistant", "content": resultado})
            with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
                json.dump(memoria, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log(f">>> Aviso: nao foi possivel gravar na memoria: {e}")

        responder(resultado)
    except Exception as e:
        import traceback
        log(traceback.format_exc())
        responder(f"ERRO no teste Oracle: {type(e).__name__}: {e}")
    finally:
        try:
            conn.close()
            log(">>> Conexao Oracle encerrada.")
        except Exception:
            pass


# --- Loops genericos de tool-use (varias ferramentas, dispatcher externo) ---
async def _loop_ferramentas_anthropic(api_key, instrucao, ferramentas, despachar):
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    mensagens = [{"role": "user", "content": instrucao}]
    for _ in range(MAX_ITERACOES):
        resp = client.messages.create(model=MODELO_CLAUDE,
                                      max_tokens=MAX_TOKENS, tools=ferramentas, messages=mensagens)
        mensagens.append({"role": "assistant", "content": resp.content})
        usos = [b for b in resp.content if b.type == "tool_use"]
        if not usos:
            return "".join(b.text for b in resp.content if b.type == "text").strip() or "(sem resposta)"
        resultados = []
        for uso in usos:
            r = despachar(uso.name, dict(uso.input) if uso.input else {})
            resultados.append({"type": "tool_result", "tool_use_id": uso.id,
                               "content": json.dumps(r, ensure_ascii=False, default=str)[:6000]})
        mensagens.append({"role": "user", "content": resultados})
    return "Limite de passos atingido."


async def _loop_ferramentas_openai(api_key, instrucao, ferramentas, despachar):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    tools = [{"type": "function", "function": {
        "name": f["name"], "description": f["description"], "parameters": f["input_schema"]}}
        for f in ferramentas]
    mensagens = [{"role": "user", "content": instrucao}]
    for _ in range(MAX_ITERACOES):
        resp = client.chat.completions.create(model=MODELO_OPENAI, tools=tools,
                                              messages=mensagens, max_tokens=MAX_TOKENS)
        msg = resp.choices[0].message
        mensagens.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            return (msg.content or "(sem resposta)").strip()
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            r = despachar(tc.function.name, args)
            mensagens.append({"role": "tool", "tool_call_id": tc.id,
                              "content": json.dumps(r, ensure_ascii=False, default=str)[:6000]})
    return "Limite de passos atingido."


async def _loop_ferramentas_gemini(api_key, instrucao, ferramentas, despachar):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    decls = [{"name": f["name"], "description": f["description"],
              "parameters": limpar_schema_gemini(f["input_schema"])} for f in ferramentas]
    tools_gemini = [{"function_declarations": decls}]
    modelos = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    model = None
    for nm in modelos:
        try:
            model = genai.GenerativeModel(nm, tools=tools_gemini); break
        except Exception:
            continue
    if model is None:
        return "Falha ao iniciar o modelo Gemini."
    chat = model.start_chat()
    proxima = instrucao
    ultimo = ""
    for passo in range(MAX_ITERACOES):
        if passo > 0:
            time.sleep(4)
        try:
            resp = chat.send_message(proxima)
        except Exception as e:
            if "ResourceExhausted" in type(e).__name__ or "429" in str(e):
                return (ultimo or "") + "\n[Limite de uso da IA atingido. Aguarde 1-2 min.]"
            return f"O modelo Gemini falhou: {type(e).__name__}"
        chamadas = []
        try:
            for cand in resp.candidates:
                for parte in cand.content.parts:
                    fc = getattr(parte, "function_call", None)
                    if fc and fc.name:
                        chamadas.append(fc)
        except Exception:
            pass
        if not chamadas:
            try:
                return (resp.text or ultimo or "(sem resposta)").strip()
            except Exception:
                return ultimo or "(sem resposta)"
        respostas = []
        for fc in chamadas:
            args = dict(fc.args) if fc.args else {}
            r = despachar(fc.name, args)
            ultimo = json.dumps(r, ensure_ascii=False, default=str)[:2000]
            respostas.append(genai.protos.Part(function_response=genai.protos.FunctionResponse(
                name=fc.name, response={"resultado": r})))
        proxima = respostas
    return (ultimo or "") + "\n[Limite de passos atingido.]"


async def executar_mongo(api_key, conn_string, somente_leitura, objetivo):
    """Sobe o servidor MCP OFICIAL da MongoDB (mongodb-mcp-server) via npx.
    conn_string: mongodb://usuario:senha@host:porta/banco
    somente_leitura: se True, passa --readOnly (o servidor e read-write por padrao).

    Nota de seguranca: o servidor oficial tambem expoe ferramentas do Atlas
    (criar usuarios, alterar lista de IPs, gerenciar clusters). Como nao passamos
    credenciais da API do Atlas, essas ferramentas nao tem como agir - o acesso
    fica restrito ao banco informado."""
    if not tem_lib("mcp"):
        responder("Biblioteca ausente: mcp. Rode: pip install mcp")
        return

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    comando_npx = "npx.cmd" if platform.system() == "Windows" else "npx"
    args = ["-y", "mongodb-mcp-server@latest", "--connectionString", conn_string]
    if somente_leitura:
        args.append("--readOnly")   # atencao: o padrao do servidor e read-write

    server_params = StdioServerParameters(command=comando_npx, args=args)

    log(">>> Subindo servidor MCP oficial da MongoDB...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_resp = await session.list_tools()
                mcp_tools = tools_resp.tools
                log(f">>> MongoDB MCP conectado. {len(mcp_tools)} ferramentas disponiveis.")

                modo_ro = ("O banco esta em modo SOMENTE LEITURA (apenas consultas). "
                           if somente_leitura else
                           "O banco permite leitura e escrita; seja cuidadoso com operacoes "
                           "destrutivas (insert/update/delete/drop) e confirme antes. ")
                objetivo_completo = (
                    f"Voce esta conectado a um banco MongoDB via ferramentas MCP. {modo_ro}"
                    f"Nao use ferramentas administrativas do Atlas (criar usuarios, alterar "
                    f"lista de IPs, gerenciar clusters) - limite-se a explorar e consultar os "
                    f"dados. Primeiro liste as collections e observe a forma dos documentos, "
                    f"depois consulte.\n\n"
                    f"Objetivo do usuario: {objetivo}\n\n"
                    f"Ao final, relate o que encontrou de forma clara. Se fizer sentido, gere "
                    f"um script de teste dentro de blocos ```linguagem ... ```.")

                if api_key.startswith("sk-ant-"):
                    if not tem_lib("anthropic"):
                        responder("Biblioteca ausente: anthropic."); return
                    resultado = await loop_anthropic(session, api_key, objetivo_completo, mcp_tools)
                elif api_key.startswith("sk-"):
                    if not tem_lib("openai"):
                        responder("Biblioteca ausente: openai."); return
                    resultado = await loop_openai(session, api_key, objetivo_completo, mcp_tools)
                else:
                    if not tem_lib("google.generativeai"):
                        responder("Biblioteca ausente: google-generativeai."); return
                    resultado = await loop_gemini(session, api_key, objetivo_completo, mcp_tools)

                try:
                    memoria = []
                    if os.path.exists(ARQUIVO_MEMORIA):
                        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
                            memoria = json.load(f)
                    memoria.append({"role": "user",
                                    "content": f"[MONGODB] {objetivo}"})
                    memoria.append({"role": "assistant", "content": resultado})
                    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
                        json.dump(memoria, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    log(f">>> Aviso: nao foi possivel gravar na memoria: {e}")

                responder(resultado)
    except FileNotFoundError:
        responder("Erro: 'npx' (Node.js) nao encontrado. Instale o Node 18+ de nodejs.org.")
    except Exception as e:
        import traceback
        log(traceback.format_exc())
        responder(f"ERRO no MongoDB: {type(e).__name__}: {e}")


def main():
    dados = sys.stdin.read()
    partes = dados.split("\n", 2)
    api_key = partes[0].strip() if len(partes) > 0 else ""
    linha2 = partes[1].strip() if len(partes) > 1 else ""
    objetivo = partes[2].strip() if len(partes) > 2 else ""

    if not api_key:
        responder("Erro: nenhuma chave de API foi informada.")
        return
    if not objetivo:
        responder("Erro: nenhum objetivo de teste foi informado.")
        return

    # MODO BANCO: a linha 2 vem como "--DB--<dsn>|<readonly>" (montada pelo C++).
    if linha2.startswith("--DB--"):
        resto = linha2[len("--DB--"):]
        if "|" in resto:
            dsn, ro = resto.rsplit("|", 1)
            somente_leitura = ro.strip() == "1"
        else:
            dsn, somente_leitura = resto, True
        asyncio.run(executar_banco(api_key, dsn.strip(), somente_leitura, objetivo))
        return

    # MODO MONGODB: linha 2 = "--MONGO--<connstring>|<readonly>"
    if linha2.startswith("--MONGO--"):
        resto = linha2[len("--MONGO--"):]
        if "|" in resto:
            conn, ro = resto.rsplit("|", 1)
            somente_leitura = ro.strip() == "1"
        else:
            conn, somente_leitura = resto, True
        asyncio.run(executar_mongo(api_key, conn.strip(), somente_leitura, objetivo))
        return

    # MODO ORACLE: linha 2 = "--ORACLE--<json>" (driver oficial, sem DBHub).
    if linha2.startswith("--ORACLE--"):
        bruto = linha2[len("--ORACLE--"):]
        try:
            info = json.loads(bruto) if bruto.strip() else {}
        except Exception:
            info = {}
        ro = str(info.get("somente_leitura", "1")) == "1"
        asyncio.run(executar_oracle(api_key, info, ro, objetivo))
        return

    # MODO API: a linha 2 vem como "--API--<json>" com os dados da requisicao.
    # Ex.: --API--{"metodo":"GET","url":"https://...","headers":{...},"body":"..."}
    if linha2.startswith("--API--"):
        bruto = linha2[len("--API--"):]
        try:
            req = json.loads(bruto) if bruto.strip() else {}
        except Exception:
            req = {}
        asyncio.run(executar_api(api_key, req, objetivo))
        return

    # MODO TELA (padrao): linha 2 e a URL alvo
    asyncio.run(executar(api_key, linha2, objetivo))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
