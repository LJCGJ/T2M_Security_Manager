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
MAX_ITERACOES = 15          # teto de passos no loop (evita custo descontrolado)
MAX_TOKENS = 2048           # teto por resposta do modelo
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
            model="claude-3-5-sonnet-20241022",
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
            model="gpt-4o-mini",
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
    # Ex.: --DB--postgres://user:senha@host:5432/db|1
    # Assim reaproveitamos o mesmo contrato de 3 linhas sem quebrar o modo tela.
    if linha2.startswith("--DB--"):
        resto = linha2[len("--DB--"):]
        # separa dsn e flag de somente-leitura
        if "|" in resto:
            dsn, ro = resto.rsplit("|", 1)
            somente_leitura = ro.strip() == "1"
        else:
            dsn, somente_leitura = resto, True
        asyncio.run(executar_banco(api_key, dsn.strip(), somente_leitura, objetivo))
        return

    # MODO TELA (padrao): linha 2 e a URL alvo
    asyncio.run(executar(api_key, linha2, objetivo))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
