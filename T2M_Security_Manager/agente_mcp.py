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
    if not isinstance(schema, dict):
        return schema
    # O SDK antigo google.generativeai rejeita varios campos de JSON Schema.
    # Removemos tudo que nao seja o subconjunto que ele aceita.
    proibidas = {"$schema", "additionalProperties", "additional_properties",
                 "title", "default", "examples", "$ref", "definitions", "$defs",
                 "anyOf", "oneOf", "allOf", "not", "format", "pattern",
                 "minimum", "maximum", "minItems", "maxItems", "minLength",
                 "maxLength", "const", "multipleOf", "uniqueItems"}
    limpo = {}
    for k, v in schema.items():
        if k in proibidas:
            continue
        if isinstance(v, dict):
            limpo[k] = limpar_schema_gemini(v)
        elif isinstance(v, list):
            limpo[k] = [limpar_schema_gemini(i) if isinstance(i, dict) else i for i in v]
        else:
            limpo[k] = v
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

    system = ("Voce e um Arquiteto de Automacao e Seguranca (QA). Use as ferramentas "
              "de navegador para cumprir o objetivo passo a passo, observando o estado "
              "real da pagina antes de cada acao. Ao final, escreva um relatorio claro "
              "do que testou, o que encontrou e um esboco de script (Robot Framework ou "
              "Python) dentro de blocos ```linguagem ``` que reproduza o teste.")

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
            "final, escreva um relatorio e um esboco de script em blocos ```linguagem ```.")},
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
# LOOP GEMINI (google-generativeai, chaves AIza)                     #
# ================================================================== #
async def loop_gemini(session, api_key, objetivo, mcp_tools):
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    declaracoes = []
    for t in mcp_tools:
        params = limpar_schema_gemini(t.inputSchema or {"type": "object", "properties": {}})
        if "type" not in params:
            params["type"] = "object"
        declaracoes.append({
            "name": t.name,
            "description": (t.description or "")[:1024],
            "parameters": params,
        })

    tools_gemini = [{"function_declarations": declaracoes}]
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        tools=tools_gemini,
        system_instruction=(
            "Voce e um Arquiteto de Automacao e Seguranca (QA). Use as ferramentas de "
            "navegador para cumprir o objetivo, observando o estado real da pagina. Ao "
            "final, escreva um relatorio e um esboco de script em blocos ```linguagem ```."),
    )
    chat = model.start_chat()
    proxima_mensagem = objetivo

    for passo in range(MAX_ITERACOES):
        resp = chat.send_message(proxima_mensagem)
        chamadas = []
        for cand in resp.candidates:
            for parte in cand.content.parts:
                fc = getattr(parte, "function_call", None)
                if fc and fc.name:
                    chamadas.append(fc)

        if not chamadas:
            return (resp.text or "(sem resposta final)").strip()

        respostas_fc = []
        for fc in chamadas:
            args = dict(fc.args) if fc.args else {}
            log(f">>> [Gemini] Ferramenta: {fc.name} {json.dumps(args)[:120]}")
            try:
                r = await session.call_tool(fc.name, args)
                conteudo = texto_do_resultado_mcp(r)
            except Exception as e:
                conteudo = f"ERRO ao executar {fc.name}: {e}"
            respostas_fc.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=fc.name, response={"resultado": conteudo})))
        proxima_mensagem = respostas_fc

    return "Limite de iteracoes atingido antes de concluir o objetivo."


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
                    f"Objetivo do teste: {objetivo}")

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
                        responder("Biblioteca ausente: google-generativeai.")
                        return
                    resultado = await loop_gemini(session, api_key, objetivo_completo, mcp_tools)

                responder(resultado)

    except FileNotFoundError:
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


def main():
    dados = sys.stdin.read()
    partes = dados.split("\n", 2)
    api_key = partes[0].strip() if len(partes) > 0 else ""
    url_alvo = partes[1].strip() if len(partes) > 1 else ""
    objetivo = partes[2].strip() if len(partes) > 2 else ""

    if not api_key:
        responder("Erro: nenhuma chave de API foi informada.")
        return
    if not objetivo:
        responder("Erro: nenhum objetivo de teste foi informado.")
        return

    asyncio.run(executar(api_key, url_alvo, objetivo))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()