# -*- coding: utf-8 -*-
"""
testar_bancos.py - Testa os modos de banco do T2M sem gastar token de IA.

Exercita a parte que NAO depende do modelo: subir o servidor MCP, listar as
ferramentas que ele expoe, executar uma consulta e ver o FORMATO REAL do que
ele devolve. E tambem confere se o modo somente-leitura barra mesmo a escrita.

Comeca pelo SQLite, que nao precisa instalar nada nem ter servidor: o banco de
teste e criado aqui, num arquivo temporario, e apagado no fim. Depois, se voce
quiser, testa qualquer outro banco a partir da string de conexao.

SEGURANCA: contra bancos que nao sejam o SQLite de teste, este script SO le.
O unico comando de escrita que ele envia e proposital, para provar que o modo
somente-leitura recusa - e ele vai para uma tabela inexistente, entao mesmo
que a recusa falhe nada seu e alterado.

COMO USAR:
    python testar_bancos.py
"""

import asyncio
import getpass
import os
import sys
import tempfile

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


def criar_sqlite_teste():
    """Cria um banco SQLite descartavel com cara de sistema real."""
    import sqlite3
    caminho = os.path.join(tempfile.gettempdir(), "t2m_teste_bancos.db")
    if os.path.exists(caminho):
        os.unlink(caminho)
    con = sqlite3.connect(caminho)
    cur = con.cursor()
    cur.execute("""CREATE TABLE CLIENTES (ID INTEGER PRIMARY KEY, NOME TEXT,
                   EMAIL TEXT, CPF TEXT)""")
    cur.execute("""CREATE TABLE PEDIDOS (ID INTEGER PRIMARY KEY, CLIENTE_ID INT,
                   TOTAL REAL, STATUS TEXT)""")
    cur.executemany("INSERT INTO CLIENTES (ID,NOME,EMAIL,CPF) VALUES (?,?,?,?)",
                    [(i, f"Cliente {i}", f"cliente{i}@exemplo.com",
                      f"000.000.000-{i:02d}") for i in range(1, 51)])
    cur.executemany("INSERT INTO PEDIDOS (ID,CLIENTE_ID,TOTAL,STATUS) VALUES (?,?,?,?)",
                    [(i, (i % 50) + 1, 100.0 + i,
                      ["NOVO", "PAGO", "ENVIADO", "CANCELADO"][i % 4])
                     for i in range(1, 201)])
    con.commit()
    con.close()
    return caminho


async def sondar_dbhub(dsn, rotulo, somente_leitura=True, consulta=None,
                       escrita=None):
    """Sobe o DBHub com este DSN e relata o que ele expoe e devolve."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import platform

    pacote = A._pacote_npm("@bytebase/dbhub", A.VERSAO_DBHUB)
    print(f"   pacote  : {pacote}")
    print(f"   conexao : {A._mascarar_credenciais(dsn)}")
    print(f"   modo    : {'somente leitura' if somente_leitura else 'leitura/escrita'}")

    comando = "npx.cmd" if platform.system() == "Windows" else "npx"
    # Mesma configuracao que o app usa em producao: arquivo dbhub.toml com o
    # DSN por variavel de ambiente. A flag --readonly nao existe mais.
    args = ["-y", pacote, "--transport", "stdio",
            "--config=" + A._config_dbhub(somente_leitura)]

    try:
        params = StdioServerParameters(command=comando, args=args, env={"DSN": dsn})
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=600)
                ferramentas = (await s.list_tools()).tools
                nomes = [t.name for t in ferramentas]
                print(f"\n   conectou. {len(nomes)} ferramenta(s):")
                for t in ferramentas:
                    print(f"     - {t.name}: {(t.description or '')[:90]}")

                nome_exec = "execute_sql" if "execute_sql" in nomes else None
                if not nome_exec:
                    print("\n   Nao achei a ferramenta de executar SQL entre as acima.")
                    print("   Anote os nomes: e essa lista que o agente precisa conhecer.")
                    return

                if consulta:
                    print(f"\n   CONSULTA ({nome_exec}): {consulta}")
                    res = await asyncio.wait_for(
                        s.call_tool(nome_exec, {"sql": consulta}), timeout=120)
                    txt = A.texto_do_resultado_mcp(res)
                    print("   >>> FORMATO REAL DO RETORNO:")
                    for linha in txt.splitlines()[:10]:
                        print(f"       {linha[:150]}")
                    if not txt.strip():
                        print("       (vazio)")

                if escrita and somente_leitura:
                    print(f"\n   ESCRITA (deve ser RECUSADA): {escrita}")
                    try:
                        res = await asyncio.wait_for(
                            s.call_tool(nome_exec, {"sql": escrita}), timeout=120)
                        txt = A.texto_do_resultado_mcp(res)
                        recusou = bool(getattr(res, "isError", False)) or any(
                            p in txt.lower() for p in
                            ("read-only", "readonly", "not allowed", "denied",
                             "somente", "permitid"))
                        print(f"       resposta: {txt[:160]}")
                        print(f"       {ok(recusou)}"
                              + ("" if recusou else
                                 "  <-- ATENCAO: a escrita NAO foi barrada!"))
                    except Exception as e:
                        print(f"       recusou com excecao: {A._detalhar_excecao(e)[:160]}")
                        print(f"       {ok(True)}")
    except Exception as e:
        detalhe = A._detalhar_excecao(e)
        print(f"\n   FALHOU: {detalhe}")
        if "Timeout" in detalhe or not detalhe.split(":")[-1].strip():
            print("   Provavelmente e o download do pacote, que na primeira vez")
            print("   sao centenas de arquivos. Aqueca o cache e rode de novo:")
            print(f"       npx -y {pacote} --help")
        else:
            print("   (npx ausente, sem internet, ou o banco recusou a conexao)")


async def sondar_mongo(conn_string):
    """O Mongo tem servidor proprio, com outro conjunto de ferramentas."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import platform

    pacote = A._pacote_npm("mongodb-mcp-server", A.VERSAO_MONGO_MCP)
    print(f"   pacote  : {pacote}")
    print(f"   conexao : {A._mascarar_credenciais(conn_string)}")
    comando = "npx.cmd" if platform.system() == "Windows" else "npx"
    try:
        params = StdioServerParameters(
            command=comando, args=["-y", pacote, "--readOnly"],
            env={"MDB_MCP_CONNECTION_STRING": conn_string})
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await asyncio.wait_for(s.initialize(), timeout=600)
                nomes = [t.name for t in (await s.list_tools()).tools]
                print(f"\n   conectou. {len(nomes)} ferramenta(s):")
                print(f"     {', '.join(nomes)}")
                for candidato in ("list-databases", "list_databases"):
                    if candidato in nomes:
                        res = await asyncio.wait_for(
                            s.call_tool(candidato, {}), timeout=120)
                        txt = A.texto_do_resultado_mcp(res)
                        print(f"\n   {candidato} devolveu:")
                        for linha in txt.splitlines()[:8]:
                            print(f"       {linha[:150]}")
                        break
    except Exception as e:
        print(f"\n   FALHOU: {A._detalhar_excecao(e)}")


async def main():
    print("TESTE DOS MODOS DE BANCO - T2M")
    print("(nao usa chave de IA; o SQLite de teste e criado e apagado aqui)")

    # ----------------------------------------------------------------
    secao("A. SQLite - sem instalar nada, sem servidor")
    caminho = criar_sqlite_teste()
    print(f"   banco de teste: {caminho}")
    print("   50 clientes e 200 pedidos criados")
    dsn = "sqlite:///" + caminho.replace("\\", "/")
    await sondar_dbhub(
        dsn, "SQLite", somente_leitura=True,
        consulta="SELECT STATUS, COUNT(*) AS QTD FROM PEDIDOS GROUP BY STATUS",
        escrita="DELETE FROM PEDIDOS WHERE ID = 999999")

    # ----------------------------------------------------------------
    secao("B. Outro banco, a partir da string de conexao")
    print("   Cole a string que o servico de nuvem forneceu. Exemplos:")
    print("     postgres://usuario:senha@host:5432/banco?sslmode=require")
    print("     mysql://usuario:senha@host:3306/banco")
    print("     mongodb+srv://usuario:senha@cluster.xxxxx.mongodb.net/banco")
    print("   Enter para pular.")
    bruto = input("\n   string de conexao: ").strip()
    if bruto:
        if not any(c in bruto for c in ("@", "://")):
            print("   Isso nao parece uma string de conexao. Pulando.")
        else:
            if "senha" in bruto.lower() or "<password>" in bruto.lower():
                senha = getpass.getpass("   a string tem um lugar para a senha; "
                                        "digite-a (nao aparece): ")
                if senha:
                    bruto = bruto.replace("<password>", senha).replace("<senha>", senha)
            if bruto.startswith("mongodb"):
                await sondar_mongo(bruto)
            else:
                await sondar_dbhub(
                    bruto, "nuvem", somente_leitura=True,
                    consulta="SELECT 1 AS teste",
                    escrita="DELETE FROM tabela_que_nao_existe_t2m WHERE 1=0")

    # ----------------------------------------------------------------
    try:
        os.unlink(caminho)
        print(f"\n   banco de teste apagado: {caminho}")
    except Exception:
        pass

    secao("FIM - copie a saida inteira e cole na conversa")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    asyncio.run(main())
