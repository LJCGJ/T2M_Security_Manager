# -*- coding: utf-8 -*-
"""
diagnostico_sqlcl.py (v3) - Descobre COMO fazer o SQLcl rodar nesta maquina.

CONTEXTO:
    O sql.EXE instalado pelo winget esta travando com codigo 3221225477
    (0xC0000005 = violacao de acesso), sem imprimir nada. Isso nao e problema
    de JAVA_HOME (ja verificamos que esta correto): e o lancador nativo
    quebrando. Este script tenta os caminhos alternativos, do mais simples ao
    mais direto, ate um funcionar.

NAO altera nada e NAO executa SQL.

COMO USAR:
    python diagnostico_sqlcl.py
"""

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile


def secao(t):
    print()
    print("=" * 64)
    print(f"  {t}")
    print("=" * 64)


def detalhar(e):
    reais = []

    def coletar(exc):
        subs = getattr(exc, "exceptions", None)
        if subs:
            for x in subs:
                coletar(x)
        else:
            reais.append(f"{type(exc).__name__}: {exc}")

    coletar(e)
    return " | ".join(reais) if reais else f"{type(e).__name__}: {e}"


def explicar_codigo(c):
    conhecidos = {
        0: "sucesso",
        1: "erro generico",
        3221225477: "0xC0000005 VIOLACAO DE ACESSO (o processo travou)",
        3221225781: "0xC0000135 DLL ausente",
        3221225595: "0xC000007B formato invalido (mistura 32/64 bits)",
    }
    return conhecidos.get(c, f"codigo {c}")


def rodar(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout, errors="replace")
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as e:
        return -1, "", f"({type(e).__name__}: {e})"


def testar(rot, cmd):
    """Roda um candidato e diz se ele funcionou."""
    print(f"\n$ {rot}")
    cod, out, err = rodar(cmd)
    print(f"  resultado: {explicar_codigo(cod)}")
    if out:
        print("  stdout: " + out[:300].replace("\n", "\n          "))
    if err:
        print("  stderr: " + err[:300].replace("\n", "\n          "))
    if not out and not err:
        print("  (nenhuma saida)")
    funcionou = cod == 0 and bool(out)
    print(f"  --> {'FUNCIONOU' if funcionou else 'nao serve'}")
    return funcionou


def achar_raiz_sqlcl():
    """Devolve a pasta raiz do SQLcl (a que contem bin/ e lib/)."""
    exe = shutil.which("sql") or shutil.which("sql.exe")
    if exe and os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(exe)), "lib")):
        return os.path.dirname(os.path.dirname(exe))
    base = os.environ.get("LOCALAPPDATA", "")
    if base:
        padrao = os.path.join(base, "Microsoft", "WinGet", "Packages", "*SQLcl*", "**", "lib")
        for lib in glob.glob(padrao, recursive=True):
            raiz = os.path.dirname(lib)
            if os.path.isdir(os.path.join(raiz, "bin")):
                return raiz
    return None


def main():
    print("DIAGNOSTICO SQLcl v3 - achando um caminho que funcione")
    print(f"Python {sys.version.split()[0]} | {sys.platform}")
    print(f"JAVA_HOME = {os.environ.get('JAVA_HOME', '(nao definido)')}")

    raiz = achar_raiz_sqlcl()
    secao("1. Instalacao do SQLcl")
    print(f"Raiz: {raiz or 'NAO ENCONTRADA'}")
    if not raiz:
        print("Instale com: winget install --id Oracle.SQLcl")
        return

    pasta_bin = os.path.join(raiz, "bin")
    pasta_lib = os.path.join(raiz, "lib")
    for nome, pasta in (("bin", pasta_bin), ("lib", pasta_lib)):
        try:
            itens = sorted(os.listdir(pasta))
            print(f"\n{nome}/ ({len(itens)} itens): " + ", ".join(itens[:14]))
        except Exception as e:
            print(f"\n{nome}/ (nao foi possivel listar: {e})")

    java = os.path.join(os.environ.get("JAVA_HOME", ""), "bin", "java.exe")
    if not os.path.exists(java):
        java = shutil.which("java") or "java"
    print(f"\njava usado: {java}")

    secao("2. Candidatos para executar o SQLcl")
    candidatos = []

    sql_bat = os.path.join(pasta_bin, "sql.bat")
    sql_exe = os.path.join(pasta_bin, "sql.exe")
    if os.path.exists(sql_bat):
        candidatos.append(("sql.bat -version", [sql_bat, "-version"],
                           ("bat", [sql_bat])))
    if os.path.exists(sql_exe):
        candidatos.append(("sql.exe -version", [sql_exe, "-version"],
                           ("exe", [sql_exe])))
    # Chamada direta pela JVM: contorna qualquer problema do lancador nativo.
    cp = os.path.join(pasta_lib, "*")
    classe = "oracle.dbtools.raptor.scriptrunner.cmdline.SqlCli"
    candidatos.append((f"java -cp lib/* {classe} -version",
                       [java, "-cp", cp, classe, "-version"],
                       ("java", [java, "-cp", cp, classe])))

    vencedor = None
    for rot, cmd, base in candidatos:
        if testar(rot, cmd):
            vencedor = base
            break

    if not vencedor:
        secao("RESULTADO")
        print("Nenhuma forma de executar o SQLcl funcionou nesta maquina.")
        print("\nO mais provavel e incompatibilidade do SQLcl 26.2 com o Java 25.")
        print("A Oracle documenta 'JRE 17 ou superior', mas o 25 e bem recente.")
        print("\nSugestao: instalar o Java 17 lado a lado (as versoes convivem):")
        print("  winget install --id EclipseAdoptium.Temurin.17.JDK")
        print("e rodar este script de novo apontando o JAVA_HOME para ele:")
        print('  set "JAVA_HOME=C:\\Program Files\\Eclipse Adoptium\\jdk-17..."')
        print("\nEnquanto isso o modo Oracle segue funcionando pelo driver nativo.")
        return

    tipo, base_cmd = vencedor
    secao(f"3. Servidor MCP usando o caminho que funcionou ({tipo})")
    import importlib.util
    if importlib.util.find_spec("mcp") is None:
        print("pacote mcp ausente. Rode: pip install mcp")
        return

    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def consultar():
        # errlog PRECISA de arquivo real (tem fileno). Um buffer de memoria
        # falha com UnsupportedOperation: fileno.
        arq = tempfile.NamedTemporaryFile("w+", delete=False, suffix="_sqlcl.log",
                                          encoding="utf-8", errors="replace")
        try:
            params = StdioServerParameters(command=base_cmd[0],
                                           args=base_cmd[1:] + ["-mcp"])
            print(f"comando: {base_cmd[0]} {' '.join(base_cmd[1:])} -mcp\n")
            async with stdio_client(params, errlog=arq) as (read, write):
                async with ClientSession(read, write) as sessao:
                    await asyncio.wait_for(sessao.initialize(), timeout=120)
                    resp = await sessao.list_tools()
                    print(f"CONECTOU. {len(resp.tools)} ferramenta(s):\n")
                    for t in resp.tools:
                        print(f"--- {t.name} ---")
                        print(f"  descricao: {(t.description or '')[:250]}")
                        print("  schema: " + json.dumps(t.inputSchema, ensure_ascii=False)[:700])
                        print()
                    if any(t.name == "list-connections" for t in resp.tools):
                        print("--- conexoes salvas (somente nomes) ---")
                        try:
                            r = await asyncio.wait_for(
                                sessao.call_tool("list-connections", {}), timeout=60)
                            txt = "".join(getattr(b, "text", "") or "" for b in r.content)
                            print(txt[:900] or "(nenhuma)")
                        except Exception as e:
                            print(f"(falhou: {detalhar(e)})")
        except Exception as e:
            print(f"FALHOU: {detalhar(e)}")
        finally:
            try:
                arq.flush()
                arq.seek(0)
                s = arq.read().strip()
                if s:
                    print("\n  >>> stderr do SQLcl:")
                    for linha in s.splitlines()[:30]:
                        print("      " + linha)
                else:
                    print("\n  (o SQLcl nao escreveu nada em stderr)")
                arq.close()
                os.unlink(arq.name)
            except Exception:
                pass

    try:
        asyncio.run(consultar())
    except Exception as e:
        print(f"Erro geral: {detalhar(e)}")

    secao("FIM - copie tudo acima e cole na conversa")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
