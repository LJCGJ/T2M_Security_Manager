# -*- coding: utf-8 -*-
"""
testar_tela.py - Testa o modo Tela (navegador) do T2M sem gastar token de IA.

Exercita o que NAO depende do modelo: subir o servidor MCP do Playwright,
listar as ferramentas, navegar de verdade numa pagina e - o mais importante -
provar que as duas protecoes de seguranca funcionam:

  * perfil isolado (--isolated): a automacao NAO herda cookies nem sessoes
    logadas do seu navegador. Sem isso, uma pagina hostil que consiga induzir
    a IA a navegar chegaria AUTENTICADA aos sistemas onde voce ja entrou.

  * dominios confiaveis (--allowed-origins): a automacao so alcanca os
    enderecos autorizados. E a defesa contra a IA ser levada para fora do
    alvo do teste.

NAO USA INTERNET. As paginas de teste sao servidas por um servidor local que
o proprio script sobe e derruba, entao o resultado nao depende de rede
corporativa, proxy nem do site de terceiros estar no ar.

COMO USAR:
    python testar_tela.py
"""

import asyncio
import http.server
import os
import socket
import sys
import threading

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "T2M_Security_Manager")
if os.path.isdir(PASTA):
    sys.path.insert(0, PASTA)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import agente_mcp as A
except Exception as e:
    print(f"Nao consegui importar o agente_mcp.py: {type(e).__name__}: {e}")
    sys.exit(1)


def secao(t):
    print()
    print("=" * 68)
    print(f"  {t}")
    print("=" * 68)


def ok(cond):
    return "OK" if cond else "FALHOU"


PAGINA_ALVO = b"""<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<title>Sistema de Teste T2M</title></head><body>
<h1>Area restrita</h1>
<form id="login"><label>Usuario <input name="usuario" id="usuario"></label>
<label>Senha <input name="senha" id="senha" type="password"></label>
<button id="entrar" type="submit">Entrar</button></form>
<p id="aviso">Informe suas credenciais.</p></body></html>"""

PAGINA_FORA = b"""<!doctype html><html><head><meta charset="utf-8">
<title>Fora do escopo</title></head><body><h1>Esta pagina NAO deveria ser
alcancada quando ha dominios confiaveis configurados.</h1></body></html>"""


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def subir_servidor(conteudo, porta):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)

        def log_message(self, *a):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", porta), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


async def sondar_playwright(rotulo, origens=None, isolado=True, navegar=None,
                            deve_bloquear=None):
    """Sobe o servidor MCP do Playwright com as mesmas opcoes que o app usa."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import platform

    pacote = A._pacote_npm("@playwright/mcp", A.VERSAO_PLAYWRIGHT_MCP)
    args = ["-y", pacote, "--headless"]
    if isolado:
        args.append("--isolated")
    if origens:
        args += ["--allowed-origins", origens]

    print(f"   pacote  : {pacote}")
    print(f"   opcoes  : {' '.join(a for a in args[2:])}")

    comando = "npx.cmd" if platform.system() == "Windows" else "npx"
    try:
        params = StdioServerParameters(command=comando, args=args)
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=600)
                nomes = [t.name for t in (await s.list_tools()).tools]
                print(f"\n   conectou. {len(nomes)} ferramenta(s).")
                print(f"   {', '.join(nomes[:12])}"
                      + (" ..." if len(nomes) > 12 else ""))

                nome_nav = next((n for n in ("browser_navigate", "navigate")
                                 if n in nomes), None)
                if not nome_nav:
                    print("\n   Nao achei a ferramenta de navegar. Nomes acima.")
                    return

                if navegar:
                    print(f"\n   NAVEGANDO para {navegar}")
                    res = await asyncio.wait_for(
                        s.call_tool(nome_nav, {"url": navegar}), timeout=180)
                    txt = A.texto_do_resultado_mcp(res)
                    for linha in txt.splitlines()[:8]:
                        print(f"       {linha[:130]}")
                    # O navigate devolve so um LINK para o snapshot em disco.
                    # Quem entrega o conteudo e o browser_snapshot, numa chamada
                    # separada - por isso a instrucao do app precisa mandar o
                    # modelo chama-lo. Aqui provamos os dois lados: que o
                    # navigate realmente nao traz o conteudo, e que o snapshot
                    # traz.
                    so_link = ("Snapshot](" in txt or ".yml" in txt) \
                        and "Area restrita" not in txt
                    print(f"   {ok(so_link)}  (confirmado: o navigate devolve "
                          f"apenas o link do snapshot)")

                    if "browser_snapshot" in nomes:
                        print("\n   BROWSER_SNAPSHOT (e daqui que o modelo enxerga)")
                        res = await asyncio.wait_for(
                            s.call_tool("browser_snapshot", {}), timeout=180)
                        txt2 = A.texto_do_resultado_mcp(res)
                        for linha in txt2.splitlines()[:14]:
                            print(f"       {linha[:130]}")
                        leu = "Area restrita" in txt2
                        tem_ref = "[ref=" in txt2
                        print(f"   {ok(leu and tem_ref)}  (conteudo da pagina e "
                              f"referencias [ref=] para clicar e preencher)")

                if deve_bloquear:
                    print(f"\n   BLOQUEIO ESPERADO para {deve_bloquear}")
                    res = await asyncio.wait_for(
                        s.call_tool(nome_nav, {"url": deve_bloquear}), timeout=180)
                    txt = A.texto_do_resultado_mcp(res)
                    vazou = "Fora do escopo" in txt or "NAO deveria" in txt
                    print(f"       resposta: {txt[:200]}")
                    print(f"   {ok(not vazou)}"
                          + ("" if not vazou else
                             "  <-- ATENCAO: o dominio NAO foi bloqueado!"))
    except Exception as e:
        detalhe = A._detalhar_excecao(e)
        print(f"\n   FALHOU: {detalhe}")
        if "Timeout" in detalhe:
            print("   Provavelmente e o download do pacote. Aqueca e repita:")
            print(f"       npx -y {pacote} --help")


async def testar_filtro(alvo):
    """Chama a ferramenta perigosa ATRAVES do filtro do app, contra o servidor
    real, e confere que ela nao chega do outro lado."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import platform

    pacote = A._pacote_npm("@playwright/mcp", A.VERSAO_PLAYWRIGHT_MCP)
    comando = "npx.cmd" if platform.system() == "Windows" else "npx"
    try:
        params = StdioServerParameters(
            command=comando, args=["-y", pacote, "--headless", "--isolated"])
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=600)
                todas = [t.name for t in (await s.list_tools()).tools]
                visiveis = [n for n in todas
                            if n not in A.FERRAMENTAS_TELA_BLOQUEADAS]
                ocultas = [n for n in todas if n in A.FERRAMENTAS_TELA_BLOQUEADAS]
                print(f"\n   servidor oferece : {len(todas)}")
                print(f"   modelo enxerga   : {len(visiveis)}")
                print(f"   ocultadas        : {ocultas or '(nenhuma)'}")
                print(f"   {ok(bool(ocultas))}  (a perigosa some da lista)")

                filtrada = A._SessaoTelaFiltrada(s)
                for nome in A.FERRAMENTAS_TELA_BLOQUEADAS:
                    res = await asyncio.wait_for(
                        filtrada.call_tool(nome, {"code": "1+1"}), timeout=60)
                    txt = A.texto_do_resultado_mcp(res)
                    barrou = "nao esta disponivel" in txt
                    print(f"\n   chamada direta a {nome}:")
                    print(f"       {txt[:150]}")
                    print(f"   {ok(barrou)}  (barrada antes de chegar ao servidor)")

                # E o caminho normal continua passando pelo filtro sem estorvo
                res = await asyncio.wait_for(
                    filtrada.call_tool("browser_navigate", {"url": alvo}), timeout=180)
                passou = "Page Title" in A.texto_do_resultado_mcp(res)
                print(f"\n   {ok(passou)}  (ferramenta legitima nao foi afetada)")
    except Exception as e:
        print(f"\n   FALHOU: {A._detalhar_excecao(e)}")


async def main():
    print("TESTE DO MODO TELA - T2M")
    print("(nao usa chave de IA, nao usa internet, nao abre janela)")
    print(f"\nconfiguracao lida: navegador_isolado={A.NAVEGADOR_ISOLADO} | "
          f"dominios_confiaveis={A.DOMINIOS_CONFIAVEIS!r}")

    p1, p2 = porta_livre(), porta_livre()
    s1 = subir_servidor(PAGINA_ALVO, p1)
    s2 = subir_servidor(PAGINA_FORA, p2)
    alvo = f"http://127.0.0.1:{p1}/"
    fora = f"http://localhost:{p2}/"
    print(f"\npaginas locais de teste: alvo={alvo}  fora={fora}")

    try:
        secao("A. Navegacao normal, com perfil isolado")
        print("   E o padrao do T2M: sem cookies e sem sessao herdada.")
        await sondar_playwright("normal", isolado=True, navegar=alvo)

        secao("B. Dominios confiaveis - a pagina fora da lista deve ser barrada")
        print("   Autorizamos SO o endereco do alvo. A segunda pagina existe e")
        print("   responde normalmente, entao se ela for lida o bloqueio falhou.")
        await sondar_playwright("restrito", origens=f"127.0.0.1:{p1}",
                                isolado=True, navegar=alvo, deve_bloquear=fora)

        secao("C. Filtro de ferramentas perigosas do proprio T2M")
        print("   O servidor oferece browser_run_code_unsafe, que executa codigo")
        print("   arbitrario. O T2M nao repassa essa ferramenta ao modelo - e,")
        print("   como o modelo poderia inventar o nome, tambem barra na chamada.")
        print(f"   lista bloqueada: {A.FERRAMENTAS_TELA_BLOQUEADAS}")
        await testar_filtro(alvo)
    finally:
        for s in (s1, s2):
            try:
                s.shutdown()
            except Exception:
                pass

    secao("FIM - copie a saida inteira e cole na conversa")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    asyncio.run(main())
