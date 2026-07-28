# -*- coding: utf-8 -*-
"""
testar_mcp_local.py - Testa a integracao MCP sem gastar token de IA.

Exercita as partes que NAO dependem do modelo: deteccao do SQLcl, criacao da
conexao nomeada, subida do servidor, filtro de ferramentas, validador de
somente-leitura e o formato de retorno do sql_run.

SEGURANCA: este script NUNCA envia comando destrutivo ao banco. Ele testa a
recusa do DELETE sem deixar o comando sair daqui, e so executa consultas.

COMO USAR:
    python testar_mcp_local.py
"""

import asyncio
import getpass
import os
import sys

# Importa as funcoes REAIS do agente, para testar o que roda em producao.
PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "T2M_Security_Manager")
if os.path.isdir(PASTA):
    sys.path.insert(0, PASTA)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import agente_mcp as A
except Exception as e:
    print(f"Nao consegui importar o agente_mcp.py: {type(e).__name__}: {e}")
    print(f"Procurei em: {PASTA}")
    sys.exit(1)


def secao(t):
    print()
    print("=" * 64)
    print(f"  {t}")
    print("=" * 64)


def ok(cond):
    return "OK" if cond else "FALHOU"


async def testar_api():
    secao("A. Servidor MCP proprio (modo API)")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    caminho = os.path.join(PASTA, "servidor_http_mcp.py")
    if not os.path.exists(caminho):
        print(f"servidor_http_mcp.py nao encontrado em {PASTA}")
        return
    # Sobe um servidor HTTP local so para o teste: assim ele funciona em
    # qualquer maquina, sem depender de internet nem de proxy corporativo.
    import http.server, json as _json, threading
    porta = 8799

    class _H(http.server.BaseHTTPRequestHandler):
        def _r(self):
            n = int(self.headers.get("Content-Length", 0) or 0)
            corpo = _json.dumps({"metodo": self.command,
                                 "auth": self.headers.get("Authorization", "(nenhum)"),
                                 "recebido": self.rfile.read(n).decode() if n else ""}).encode()
            self.send_response(201 if self.command == "POST" else 200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(corpo)
        do_GET = do_POST = do_PUT = do_DELETE = _r

        def log_message(self, *a):
            pass

    try:
        httpd = http.server.HTTPServer(("127.0.0.1", porta), _H)
    except OSError as e:
        print(f"nao consegui abrir a porta {porta} para o teste: {e}")
        return
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    params = StdioServerParameters(command=sys.executable, args=["-u", caminho],
                                   env={"T2M_TIMEOUT": "30"})
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=60)
                t = (await s.list_tools()).tools
                print(f"conectou: {len(t)} ferramenta(s) -> {[x.name for x in t]}")
                for metodo, hdr in (("GET", None), ("POST", {"Authorization": "Bearer teste"})):
                    res = await s.call_tool("fazer_requisicao_http",
                                            {"metodo": metodo,
                                             "url": f"http://127.0.0.1:{porta}/r",
                                             "headers": hdr})
                    txt = "".join(getattr(b, "text", "") or "" for b in res.content)
                    bom = '"status_code"' in txt and "erro" not in txt[:20]
                    print(f"   {metodo:<5} -> {txt[:120]}")
                    print(f"         {ok(bom)}")
    except Exception as e:
        print(f"FALHOU: {A._detalhar_excecao(e)}")
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass


async def testar_oracle():
    secao("B. Oracle via servidor MCP oficial (SQLcl)")

    print("1) Deteccao do ambiente")
    raiz = A._achar_sqlcl()
    java = A._achar_java()
    cmd = A._comando_sqlcl(raiz) if raiz else None
    print(f"   SQLcl : {raiz or 'NAO ENCONTRADO'}")
    print(f"   Java  : {java or 'NAO ENCONTRADO'}")
    print(f"   {ok(bool(cmd))}")
    if not cmd:
        print("\n   Sem SQLcl/Java o app usa o driver nativo. Nada mais a testar aqui.")
        return

    print("\n2) Dados da conexao Oracle (usados so nesta maquina)")
    print("   No campo host da para colar so o nome do servidor, ou entao uma")
    print("   string de conexao inteira - tcps://... ou (DESCRIPTION=...) - que")
    print("   e o formato do Autonomous Database. Colando a string inteira, os")
    print("   campos porta e servico sao ignorados.")
    host = input("   host, apelido do tnsnames ou string completa [localhost]: "
                 ).strip() or "localhost"
    info = {"host": host}

    wallet = input("   wallet .zip ou pasta (Enter se nao usa): ").strip()
    if wallet:
        info["wallet"] = wallet
        senha_wallet = getpass.getpass("   senha da wallet (Enter se nao tem): ")
        if senha_wallet:
            info["wallet_senha"] = senha_wallet

    if A._oracle_conexao_ja_pronta(host):
        print("   -> reconhecido como string de conexao completa")
    elif wallet:
        print("   -> com wallet: o host acima sera tratado como apelido do tnsnames.ora")
    else:
        info["porta"] = input("   porta [1521]: ").strip() or "1521"
        info["servico"] = input("   servico [FREEPDB1]: ").strip() or "FREEPDB1"
        if not str(info["porta"]).isdigit():
            print(f"\n   Porta invalida: {info['porta']!r}. Deve ser um numero "
                  f"(normalmente 1521, ou 1522 no Autonomous Database).")
            return

    info["usuario"] = input("   usuario: ").strip()
    info["senha"] = getpass.getpass("   senha (nao aparece): ")

    if not info["usuario"] or not info["senha"]:
        print("\n   Usuario ou senha em branco. Use credenciais REAIS de um usuario")
        print("   do seu Oracle (de preferencia um usuario de teste, nao o SYSTEM).")
        print("   Se voce ainda nao tem o usuario de teste, rode antes:")
        print("     python preparar_oracle_teste.py")
        return

    print(f"\n   conexao montada: {A._oracle_rotulo(info)}")

    print("\n3) Criando a conexao nomeada no SQLcl")
    print("   (o SQLcl sai com codigo 0 mesmo falhando, entao conferimos o texto)")
    bom, detalhe = A._salvar_conexao_sqlcl(cmd, info)
    print(f"   {ok(bom)}" + (f" - {detalhe}" if detalhe else ""))
    if not bom:
        print("\n   A conexao NAO foi salva, entao o passo 5 falharia com")
        print("   'Connection not found'. Corrija o acima e rode de novo.")
        return

    print("\n4) Subindo o servidor e listando ferramentas")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=cmd[0], args=cmd[1:] + ["-mcp"])
    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=120)
                todas = (await s.list_tools()).tools
                nomes = [t.name for t in todas]
                permitidas = [n for n in nomes if n in A.FERRAMENTAS_ORACLE_PERMITIDAS]
                ocultas = [n for n in nomes if n not in A.FERRAMENTAS_ORACLE_PERMITIDAS]
                print(f"   servidor expoe : {nomes}")
                print(f"   modelo veria   : {permitidas}")
                print(f"   ocultas        : {ocultas}")
                print(f"   {ok(len(permitidas) == 2)}")

                print("\n5) Conectando (pelo nosso codigo, nao pelo modelo)")
                res = await s.call_tool("connect",
                                        {"connection_name": A.NOME_CONEXAO_T2M,
                                         "model": "teste-linha-de-comando"})
                txt = A.texto_do_resultado_mcp(res)
                print(f"   resposta: {txt[:200]}")

                filtrada = A._SessaoOracleFiltrada(s, True, "teste-linha-de-comando")

                print("\n6) SELECT em modo somente-leitura (deve PASSAR)")
                res = await filtrada.call_tool("sql_run", {"sql": "SELECT 1 AS teste FROM dual"})
                txt = A.texto_do_resultado_mcp(res)
                print("   >>> FORMATO REAL DO RETORNO (o que eu precisava ver):")
                for linha in txt.splitlines()[:8]:
                    print(f"       {linha}")
                print(f"   {ok('1' in txt)}")

                print("\n7) DELETE em modo somente-leitura (deve ser RECUSADO aqui, sem chegar ao banco)")
                res = await filtrada.call_tool("sql_run", {"sql": "DELETE FROM DUAL"})
                txt = A.texto_do_resultado_mcp(res)
                print(f"   resposta: {txt[:160]}")
                print(f"   {ok('somente-leitura' in txt)}")

                print("\n8) Ferramenta perigosa (deve ser RECUSADA pelo filtro)")
                for perigosa, arg in (("sqlcl_run", {"sqlcl": "help"}),
                                      ("skills_sync", {}),
                                      ("connections_list", {})):
                    res = await filtrada.call_tool(perigosa, arg)
                    txt = A.texto_do_resultado_mcp(res)
                    print(f"   {perigosa:<18} {ok('nao esta disponivel' in txt)}")

                print("\n9) schema_information (leitura, deve PASSAR)")
                res = await filtrada.call_tool("schema_information", {"level": "BRIEF"})
                txt = A.texto_do_resultado_mcp(res)
                print(f"   primeiras linhas: {txt[:200]}")
                print(f"   {ok(len(txt) > 10)}")

                print("\n10) Auditoria: as consultas foram registradas?")
                res = await filtrada.call_tool("sql_run", {
                    "sql": "SELECT COUNT(*) AS registros FROM DBTOOLS$MCP_LOG"})
                txt = A.texto_do_resultado_mcp(res)
                print(f"   {txt[:200]}")
    except Exception as e:
        print(f"   FALHOU: {A._detalhar_excecao(e)}")


async def main():
    print("TESTE LOCAL DA INTEGRACAO MCP - T2M")
    print("(nao usa chave de IA e nao altera dados)")
    print(f"\nconfiguracao lida: oracle_via_mcp={A.ORACLE_VIA_MCP!r}")

    await testar_api()

    resp = input("\nTestar tambem o Oracle? Precisa das credenciais. (s/N): ").strip().lower()
    if resp == "s":
        await testar_oracle()

    secao("FIM - copie a saida e cole na conversa")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    asyncio.run(main())
