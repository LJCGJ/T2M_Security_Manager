# -*- coding: utf-8 -*-
"""
T2M Copilot - Motor de IA (roteador multi-provedor)

SEGURANCA:
    A entrada chega por STDIN, e nao por sys.argv. Isso resolve tres problemas:
      - A API key nao aparece na lista de processos (Gerenciador de Tarefas).
      - Prompts longos nao esbarram no limite da linha de comando (~32KB).
      - Aspas e caracteres especiais no prompt nao quebram o parsing.

    Contrato de entrada (stdin, UTF-8) - 3 linhas, igual ao agente_mcp.py:
        linha 1: chave de API
        linha 2: URL alvo
        linha 3+: prompt do usuario

    Contrato de saida (stdout):
        CHAT_MSG_INICIO
        <resposta>
        CHAT_MSG_FIM
"""

import sys
import os
import json
import subprocess

# Memoria COMPARTILHADA com o agente MCP (agente_mcp.py). Mesmo caminho nos dois
# (diretorio do script) para que chat e automacao ao vivo vejam a mesma conversa.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _caminho_dados(arquivo):
    """Caminho de um arquivo GRAVAVEL do usuario, espelhando o CaminhoDados()
    do MyForm.h: %APPDATA%/T2M Security Manager/<arquivo>.

    Por que isso importa: instalado em Program Files, gravar ao lado do script
    falha com PermissionError. Como esse erro era engolido em silencio, o
    sintoma para o usuario era "a IA nunca lembra do turno anterior", sem
    nenhuma mensagem de erro. Mantem a mesma migracao do arquivo antigo que o
    C++ ja faz, para nao perder conversas de instalacoes anteriores.
    """
    try:
        appdata = os.environ.get("APPDATA", "")
        if not appdata:
            return os.path.join(SCRIPT_DIR, arquivo)
        pasta = os.path.join(appdata, "T2M Security Manager")
        os.makedirs(pasta, exist_ok=True)
        destino = os.path.join(pasta, arquivo)
        antigo = os.path.join(SCRIPT_DIR, arquivo)
        if not os.path.exists(destino) and os.path.exists(antigo):
            import shutil
            shutil.copy2(antigo, destino)
        return destino
    except Exception:
        return os.path.join(SCRIPT_DIR, arquivo)


ARQUIVO_MEMORIA = _caminho_dados("memoria_chat.json")


def responder(texto):
    """Formato que a interface C++ espera no stdout - o MESMO contrato do
    agente_mcp.py. Mensagens de erro que saiam sem os marcadores caem no
    fallback generico do C++, que despeja o stdout bruto na tela (podendo
    misturar saida do pip com a mensagem real)."""
    print("CHAT_MSG_INICIO")
    print(texto)
    print("CHAT_MSG_FIM")


def log(msg):
    """Mensagens de progresso vao para stderr; o app as exibe ao vivo no chat.
    O stdout fica reservado para a resposta final (marcadores CHAT_MSG_*)."""
    print(msg, file=sys.stderr, flush=True)


def _carregar_configuracoes():
    """Le configuracoes.txt gravado pelo app (tela de Configuracoes).
    Procura primeiro na pasta de dados do usuario, depois ao lado do script."""
    cfg = {}
    try:
        appdata = os.environ.get("APPDATA", "")
        candidatos = []
        if appdata:
            candidatos.append(os.path.join(appdata, "T2M Security Manager", "configuracoes.txt"))
        candidatos.append(os.path.join(SCRIPT_DIR, "configuracoes.txt"))
        caminho = next((c for c in candidatos if os.path.exists(c)), None)
        if caminho:
            with open(caminho, "r", encoding="utf-8") as f:
                for linha in f:
                    if "=" in linha:
                        chave, valor = linha.split("=", 1)
                        cfg[chave.strip()] = valor.strip()
    except Exception:
        pass
    return cfg


_CFG = _carregar_configuracoes()

# ATENCAO: modelos antigos foram APOSENTADOS e retornam erro.
# claude-3-haiku-20240307 saiu do ar em abril/2026 - nao usar.
MODELO_CLAUDE = _CFG.get("modelo_claude", "claude-haiku-4-5-20251001").strip() \
    or "claude-haiku-4-5-20251001"
MODELO_OPENAI = _CFG.get("modelo_openai", "gpt-4o-mini").strip() or "gpt-4o-mini"
# A rota Gemini ignorava a configuracao e usava sempre uma lista fixa: o que o
# usuario escolhesse na tela nao tinha efeito nenhum para chaves do Google.
MODELO_GEMINI = _CFG.get("modelo_gemini", "").strip()

# Quantas mensagens do historico sao reenviadas a cada chamada.
# Sem limite, a conversa cresce para sempre: cada pergunta nova reenviaria toda
# a conversa anterior, ficando progressivamente mais lenta e mais cara.
try:
    MAX_HISTORICO = max(2, min(200, int(_CFG.get("max_historico", 20))))
except Exception:
    MAX_HISTORICO = 20


def limitar_historico(memoria):
    """Mantem apenas as ultimas mensagens, preservando o inicio da conversa
    (onde costuma estar o contexto mais importante).

    Duas armadilhas tratadas aqui:

    1) MAX_HISTORICO == 2 (valor permitido pela tela de Configuracoes) fazia
       memoria[-0:], e -0 e 0 em Python: o slice devolvia a lista INTEIRA e o
       resultado ficava MAIOR que a entrada. A configuracao que existe para
       economizar tokens fazia exatamente o oposto.

    2) O corte podia cair no meio de um par user/assistant, deixando a cauda
       comecando com 'assistant'. Como o prefixo preservado termina em
       'assistant', a sequencia ficava com dois 'assistant' seguidos - a
       Anthropic responde HTTP 400 (roles must alternate) e o Gemini tambem
       rejeita. Por isso avancamos ate o proximo turno 'user'; avancar so
       encurta a cauda, entao o teto continua respeitado.
    """
    if len(memoria) <= MAX_HISTORICO:
        return memoria

    cauda = MAX_HISTORICO - 2
    if cauda <= 0:
        return memoria[:2]

    inicio = len(memoria) - cauda
    while inicio < len(memoria) and (
            not isinstance(memoria[inicio], dict)
            or memoria[inicio].get("role") != "user"):
        inicio += 1
    return memoria[:2] + memoria[inicio:]


# ==============================================================================
# --- 1. AUTO-INSTALACAO SILENCIOSA DE DEPENDENCIAS ---
# ==============================================================================
def garantir_bibliotecas(api_key=""):
    """Instala apenas as bibliotecas que ESTA execucao vai usar.

    Antes a funcao importava os cinco SDKs em toda mensagem, o que trazia dois
    problemas. Primeiro, custava alguns segundos por mensagem sem necessidade.
    Segundo, e mais grave: o import de google.generativeai levanta TypeError ou
    AttributeError (nao ImportError) quando ha conflito de protobuf/grpc - um
    caso comum - e como so ImportError era capturado, a excecao escapava e
    derrubava o chat inteiro, inclusive para quem usa Claude ou OpenAI e nem
    encosta no Gemini.
    """
    # Sempre necessarias: leitura da pagina no scanner de DOM.
    necessarias = {"requests": "requests", "beautifulsoup4": "bs4"}
    # Apenas o SDK do provedor para o qual esta chave sera roteada.
    if api_key.startswith("sk-ant-"):
        necessarias["anthropic"] = "anthropic"
    elif api_key.startswith("sk-"):
        necessarias["openai"] = "openai"
    elif api_key:
        necessarias["google-generativeai"] = "google.generativeai"

    faltando = []
    for pacote, modulo in necessarias.items():
        try:
            __import__(modulo)
        except ImportError:
            faltando.append(pacote)
        except Exception as e:
            # O modulo existe mas quebrou ao importar (conflito de dependencia).
            # Reinstalar nao resolve; avisa e segue. A rota correspondente
            # falhara de forma controlada se realmente precisar dele.
            log(f"--- AVISO: {modulo} esta instalado mas falhou ao importar: "
                f"{type(e).__name__}: {e}")

    for lib in faltando:
        try:
            # timeout: sem ele, um pip travado na rede fazia o C++ matar o
            # processo por tempo esgotado e culpar a chave de API.
            # DEVNULL: sem isso a saida do pip se mistura ao stdout do contrato.
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", lib, "--quiet"],
                timeout=180,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            log(f"--- AVISO: falha ao instalar {lib}: {type(e).__name__}: {e}")


# ==============================================================================
# --- 2. LIMPEZA DE JSON SCHEMA (base para futuras 'tools' MCP-like) ---
# ==============================================================================
def clean_schema(schema):
    """Remove chaves de JSON Schema que a API do Gemini nao aceita."""
    if not isinstance(schema, dict):
        return schema
    cleaned = {}
    for key, value in schema.items():
        if key in ("$schema", "additionalProperties", "additional_properties"):
            continue
        if isinstance(value, dict):
            cleaned[key] = clean_schema(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_schema(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


# ==============================================================================
# --- 3. SCANNER DE INTERFACE (DOM) ---
#     Observacao honesta: isto NAO e o protocolo MCP. E scraping do HTML da
#     URL alvo para mapear inputs/botoes/forms e dar contexto real ao modelo.
#     Para QA/automacao de tela isso e uma abordagem legitima e util.
# ==============================================================================
def extrair_contexto_dom(url):
    try:
        import requests
        from bs4 import BeautifulSoup
        log(f">>> Lendo a estrutura de {url}...")

        headers = {'User-Agent': 'Mozilla/5.0 (T2M-QA-Scanner)'}
        req = requests.get(url, headers=headers, timeout=8)
        req.raise_for_status()
        soup = BeautifulSoup(req.text, 'html.parser')

        inputs = soup.find_all('input')
        botoes = soup.find_all('button')
        forms = soup.find_all('form')
        links = soup.find_all('a')

        scripts = soup.find_all('script')
        total_elementos = len(inputs) + len(botoes) + len(forms)

        # DETECCAO DE PAGINA DINAMICA (SPA):
        # Aplicacoes React/Vue/Angular entregam um HTML quase vazio e montam a
        # interface no navegador, via JavaScript. Como esta leitura e estatica,
        # ela veria "nenhum campo" e o modelo concluiria que a pagina e vazia -
        # uma conclusao errada dita com confianca. Melhor admitir a limitacao.
        marcadores_spa = ('id="root"', "id='root'", 'id="app"', "id='app'",
                          '__NEXT_DATA__', 'ng-version', 'data-reactroot')
        html_bruto = req.text
        parece_spa = (total_elementos <= 1 and len(scripts) >= 1) or \
                     any(m in html_bruto for m in marcadores_spa)

        linhas = [f"=== LEITURA ESTATICA DA PAGINA ({url}) ==="]

        if parece_spa and total_elementos <= 2:
            linhas.append("")
            linhas.append("ATENCAO - LIMITACAO DESTA LEITURA:")
            linhas.append("Esta pagina monta a interface por JavaScript no navegador "
                          "(aplicacao de pagina unica). A leitura estatica do HTML nao "
                          "enxerga os elementos criados em tempo de execucao.")
            linhas.append("NAO conclua que a pagina nao tem campos ou botoes: eles "
                          "provavelmente existem, mas so aparecem apos o carregamento.")
            linhas.append("Para mapear esta pagina de verdade, use o modo Automacao > "
                          "Teste de Tela, que abre um navegador real.")
            linhas.append("")

        linhas.append(f"Formularios no HTML estatico: {len(forms)}")
        linhas.append(f"Links no HTML estatico: {len(links)}")
        linhas.append(f"Scripts carregados: {len(scripts)}")

        if inputs:
            linhas.append("Campos de entrada encontrados:")
            for i in inputs:
                linhas.append(
                    f" - Tipo: {i.get('type', 'N/A')} | "
                    f"ID: {i.get('id', 'N/A')} | "
                    f"Name: {i.get('name', 'N/A')} | "
                    f"Placeholder: {i.get('placeholder', 'N/A')}"
                )
        else:
            linhas.append("Campos de entrada: nenhum no HTML estatico"
                          + (" (provavelmente criados por JavaScript)" if parece_spa else ""))

        if botoes:
            linhas.append("Botoes encontrados:")
            for b in botoes:
                texto = (b.get_text() or "").strip()[:60]
                linhas.append(f" - Texto: {texto} | ID: {b.get('id', 'N/A')}")
        else:
            linhas.append("Botoes: nenhum no HTML estatico"
                          + (" (provavelmente criados por JavaScript)" if parece_spa else ""))

        linhas.append("=======================================")
        return "\n".join(linhas) + "\n"
    except Exception as e:
        return (
            "--- AVISO: nao foi possivel ler a URL profundamente. "
            f"Use nomes genericos de elementos. (Erro: {e})\n"
        )


# ==============================================================================
# --- 4. LEITURA DA ENTRADA (STDIN JSON) ---
# ==============================================================================
def ler_entrada():
    """Le 3 linhas de texto via stdin: linha1=chave, linha2=url, linha3+=prompt.
    Mesmo contrato usado pelo C++ (MyForm.h) e pelo agente_mcp.py."""
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        raise ValueError("Nenhum dado recebido via stdin.")
    partes = raw.split("\n", 2)
    api_key = partes[0].strip() if len(partes) > 0 else ""
    url = partes[1].strip() if len(partes) > 1 else ""
    prompt = partes[2] if len(partes) > 2 else ""
    # Retorna na ordem que o main() espera: (api_key, prompt, url)
    return (api_key, prompt, url)


# ==============================================================================
# --- 5. FUNCAO PRINCIPAL E ROTEAMENTO MULTI-IA ---
# ==============================================================================
def main():
    try:
        try:
            api_key, prompt_usuario, url_alvo = ler_entrada()
        except Exception as e:
            responder(f"Erro ao ler a entrada: {e}")
            return

        if not api_key:
            responder("Nenhuma chave de API foi informada.")
            return

        # Depois de ler a chave: so instala o SDK do provedor que sera usado.
        garantir_bibliotecas(api_key)

        arquivo_memoria = ARQUIVO_MEMORIA
        memoria = []

        # --- COMANDOS DE CONTROLE (vindos do C++) ---
        # --INICIAR_NOVO_CHAT-- : primeira mensagem (apresentacao). MCP_OFF = sem scanner.
        # --SCAN_DOM--          : o usuario esta no modo Scan DOM; escaneia a pagina e
        #                         responde a pergunta que vem depois do prefixo.
        if prompt_usuario.startswith("--SCAN_DOM--"):
            pergunta = prompt_usuario.replace("--SCAN_DOM--", "", 1).strip()
            if os.path.exists(arquivo_memoria):
                try:
                    with open(arquivo_memoria, 'r', encoding='utf-8') as f:
                        memoria = json.load(f)
                except Exception:
                    memoria = []
            contexto = ""
            if url_alvo:
                contexto = ("CONTEXTO INTERNO (estrutura da pagina; nao mencione que veio de "
                            "um scanner, apenas use se for util):\n" + extrair_contexto_dom(url_alvo))
            entrada = (contexto + "\n\n" if contexto else "") + \
                      ("Com base na estrutura acima, ajude o usuario. " if contexto else "") + \
                      "Pergunta do usuario: " + (pergunta or "Analise a pagina e me diga o que da para automatizar.")
            memoria.append({"role": "user", "content": entrada})

        elif prompt_usuario.startswith("--INICIAR_NOVO_CHAT--"):
            usar_scanner = "MCP_OFF" not in prompt_usuario

            if usar_scanner and url_alvo:
                mapa = ("CONTEXTO INTERNO (nao mencione que isso veio de um scanner; apenas "
                        "use estas informacoes se forem uteis para responder):\n"
                        + extrair_contexto_dom(url_alvo))
            else:
                mapa = ""

            prompt_mestre = f"""
Voce e um assistente especialista em automacao de testes, qualidade de software (QA)
e engenharia de seguranca, integrado a uma ferramenta de automacao chamada T2M Copilot.

{mapa}

Escreva uma PRIMEIRA mensagem de apresentacao seguindo estas regras:
- Tom profissional, direto e confiante, como um bom engenheiro senior falaria. Sem
  exageros, sem linguagem de marketing, sem emojis, sem se alongar.
- No maximo 3 ou 4 frases curtas.
- Apresente-se em uma frase e deixe claro, de forma objetiva, no que voce pode ajudar:
  planejar e escrever testes automatizados, analisar interfaces, validar comportamento
  de aplicacoes web e apoiar tarefas de seguranca e QA.
- NAO liste tecnologias ou ferramentas especificas por nome (nada de citar frameworks,
  bibliotecas ou linguagens) a menos que o usuario pergunte. Fale de capacidades, nao de
  stack.
- NAO mencione "scanner", "URL mapeada", "operador" nem o estado interno do sistema.
- Termine com UMA pergunta objetiva convidando o usuario a descrever o que precisa.
- NAO gere codigo nesta primeira resposta.
Sempre que for gerar codigo (nas proximas mensagens), coloque-o em blocos
```linguagem ... ``` para o sistema reconhecer.
"""
            memoria = [{"role": "user", "content": prompt_mestre}]
        else:
            if os.path.exists(arquivo_memoria):
                try:
                    with open(arquivo_memoria, 'r', encoding='utf-8') as f:
                        memoria = json.load(f)
                except Exception:
                    memoria = []
            memoria.append({"role": "user", "content": prompt_usuario})

        # Corta o historico antes de enviar (controla custo e tempo)
        total_antes = len(memoria)
        memoria = limitar_historico(memoria)
        if total_antes > len(memoria):
            log(f">>> Historico longo: enviando as {len(memoria)} mensagens mais "
                f"relevantes de {total_antes}.")

        resposta_ia = ""
        sistema = (
            "Voce e o T2M Copilot, um assistente especialista em automacao de testes, "
            "qualidade de software (QA) e engenharia de seguranca, integrado a uma "
            "ferramenta desktop. Seja profissional, direto e pratico, como um bom "
            "engenheiro senior. Evite marketing e respostas longas demais. Nao mencione "
            "detalhes internos do sistema (scanner, operador, memoria).\n\n"
            "SEU OBJETIVO e ajudar o usuario a TESTAR e CONSTRUIR automacoes. Depois de "
            "analisar uma pagina ou entender o contexto, PERGUNTE objetivamente qual tipo "
            "de automacao o usuario quer construir, oferecendo as opcoes:\n"
            "  1) Automacao de NAVEGACAO web (interagir com paginas, formularios, fluxos);\n"
            "  2) Automacao de API (testar endpoints; peca metodo, URL, headers, payload);\n"
            "  3) Automacao de BANCO DE DADOS/SQL (peca o tipo de banco e as credenciais/"
            "string de conexao ao usuario quando necessario, e alerte para nao expor senhas "
            "reais se nao quiser).\n"
            "Conduza a construcao passo a passo, fazendo as perguntas necessarias antes de "
            "gerar o script. Escolha a linguagem mais adequada, preferindo Robot Framework "
            "ou Python. Sempre que gerar codigo, coloque-o em blocos ```linguagem ... ``` "
            "para o sistema conseguir extrair e salvar.")

        # Roteador por provedor. Ordem importa: prefixos mais especificos primeiro.
        # Gemini fica como padrao porque o Google mudou o formato da chave em 2026
        # (AIza -> AQ.) e pode mudar de novo; validar so "AIza" quebraria com as
        # chaves novas. Chaves Gemini validas hoje: AIza..., AQ...., AQ_...

        # --- ROTA ANTHROPIC (CLAUDE) ---
        if api_key.startswith("sk-ant-"):
            log(f">>> Consultando o Claude ({MODELO_CLAUDE})...")
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=MODELO_CLAUDE,
                max_tokens=2048,
                system=sistema,
                messages=memoria,
            )
            # content pode trazer blocos que nao sao texto (ThinkingBlock, quando
            # o modelo escolhido tem raciocinio estendido) e pode vir vazio.
            # Pegar content[0].text as cegas dava AttributeError ou IndexError.
            resposta_ia = "".join(
                b.text for b in response.content
                if getattr(b, "type", "") == "text" and getattr(b, "text", None)
            ).strip()

        # --- ROTA OPENAI (CHATGPT) ---
        elif api_key.startswith("sk-"):
            log(f">>> Consultando a OpenAI ({MODELO_OPENAI})...")
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=MODELO_OPENAI,
                messages=[{"role": "system", "content": sistema}] + memoria,
            )
            # content vem None em recusas e quando o modelo devolve tool_calls;
            # o .strip() direto dava AttributeError em NoneType.
            resposta_ia = (response.choices[0].message.content or "").strip()

        # --- ROTA GOOGLE GEMINI (padrao; aceita AIza, AQ. e formatos futuros) ---
        else:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            mensagens = [
                {"role": "user" if m["role"] == "user" else "model",
                 "parts": [m["content"]]}
                for m in memoria
            ]
            # Modelos estaveis primeiro. gemini-flash-latest é um alias que o
            # Google mantem sempre apontando para a versao flash atual (bom fallback).
            modelos = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
            # O modelo escolhido em Configuracoes entra na frente; o resto vira fallback.
            if MODELO_GEMINI:
                modelos = [MODELO_GEMINI] + [m for m in modelos if m != MODELO_GEMINI]
            sucesso = False
            erros = []
            for nome_modelo in modelos:
                try:
                    log(f">>> Consultando o Gemini ({nome_modelo})...")
                    model = genai.GenerativeModel(nome_modelo, system_instruction=sistema)
                    response = model.generate_content(mensagens)
                    resposta_ia = response.text.strip()
                    sucesso = True
                    break
                except Exception as e:
                    # Guarda o erro de CADA modelo, para diagnostico (nao so o ultimo)
                    erros.append(f"{nome_modelo}: {str(e)[:150]}")
                    log(f">>> {nome_modelo} indisponivel, tentando o proximo...")
                    continue
            if not sucesso:
                detalhe = " || ".join(erros)
                responder(f"Nenhum modelo Gemini respondeu.\n\nDetalhes: {detalhe}")
                return

        # Resposta vazia nao deve virar um bloco CHAT_MSG em branco na tela.
        if not resposta_ia:
            responder("A IA devolveu uma resposta vazia. Tente reformular a pergunta "
                      "ou confira o modelo selecionado em Configuracoes.")
            return

        # --- PERSISTE MEMORIA E RETORNA PARA A INTERFACE ---
        memoria.append({"role": "assistant", "content": resposta_ia})
        try:
            with open(arquivo_memoria, 'w', encoding='utf-8') as f:
                json.dump(memoria, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

        log(">>> Resposta recebida.")
        responder(resposta_ia)

    except Exception as e:
        responder(f"Erro interno no motor de IA: {type(e).__name__}: {e}")


if __name__ == "__main__":
    try:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()