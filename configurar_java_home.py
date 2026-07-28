# -*- coding: utf-8 -*-
"""
configurar_java_home.py - Define o JAVA_HOME e testa o SQLcl em seguida.

POR QUE ISTO EXISTE:
    O lancador do SQLcl (sql.exe) procura o Java pelo JAVA_HOME ANTES de olhar
    o PATH. Com o Java instalado mas sem essa variavel, ele sai sem dizer nada -
    foi o que aconteceu no diagnostico: "sql -version" nao imprimiu uma linha
    sequer e o servidor MCP nao subiu.

O QUE ELE MUDA:
    Apenas a variavel JAVA_HOME, no nivel do USUARIO (nao precisa de
    administrador, nao mexe no PATH e nao afeta outras contas da maquina).

COMO DESFAZER, se quiser:
    setx JAVA_HOME ""
    ou remova em: Configuracoes > Sistema > Sobre > Configuracoes avancadas do
    sistema > Variaveis de Ambiente > Variaveis de usuario

COMO USAR:
    python configurar_java_home.py
"""

import io
import os
import shutil
import subprocess
import sys


def secao(t):
    print()
    print("=" * 62)
    print(f"  {t}")
    print("=" * 62)


def detalhar(e):
    """Desempacota ExceptionGroup para mostrar a causa real."""
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


def rodar(cmd, timeout=90):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           text=True, timeout=timeout, errors="replace")
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as e:
        return -1, "", f"({type(e).__name__}: {e})"


def parece_jdk(pasta):
    """Uma pasta so serve como JAVA_HOME se tiver bin/java e as bibliotecas."""
    if not pasta or not os.path.isdir(pasta):
        return False
    tem_java = any(os.path.exists(os.path.join(pasta, "bin", n))
                   for n in ("java.exe", "java"))
    return tem_java and os.path.isdir(os.path.join(pasta, "lib"))


def candidatos_java():
    """Lista possiveis JAVA_HOME, do mais provavel ao menos."""
    vistos, saida = set(), []

    def add(p):
        if p and p not in vistos and parece_jdk(p):
            vistos.add(p)
            saida.append(p)

    # 1) a partir do java que esta no PATH (ignorando o atalho da Store)
    exe = shutil.which("java")
    if exe and "WindowsApps" not in exe:
        add(os.path.dirname(os.path.dirname(os.path.realpath(exe))))

    # 2) locais padrao de instalacao
    for base in (os.environ.get("ProgramFiles", ""),
                 os.environ.get("ProgramFiles(x86)", ""),
                 os.environ.get("LOCALAPPDATA", "")):
        for fabricante in ("Eclipse Adoptium", "Java", "Microsoft", "Zulu",
                           "Amazon Corretto", "BellSoft", "Semeru"):
            raiz = os.path.join(base, fabricante) if base else ""
            if raiz and os.path.isdir(raiz):
                try:
                    for nome in sorted(os.listdir(raiz), reverse=True):
                        add(os.path.join(raiz, nome))
                except Exception:
                    pass
    return saida


def achar_sql():
    achado = shutil.which("sql") or shutil.which("sql.exe")
    if achado:
        return achado
    base = os.environ.get("LOCALAPPDATA", "")
    if base:
        raiz = os.path.join(base, "Microsoft", "WinGet", "Packages")
        if os.path.isdir(raiz):
            for dirpath, _, arquivos in os.walk(raiz):
                if "sqlcl" in dirpath.lower() and dirpath.lower().endswith("bin"):
                    for n in ("sql.exe", "sql.EXE", "sql.bat"):
                        if n in arquivos:
                            return os.path.join(dirpath, n)
    return None


def main():
    print("CONFIGURAR JAVA_HOME PARA O SQLcl - T2M")

    secao("1. Situacao atual")
    atual = os.environ.get("JAVA_HOME")
    print(f"JAVA_HOME agora: {atual or '(nao definido)'}")
    print(f"java no PATH   : {shutil.which('java') or '(nao encontrado)'}")

    if atual and parece_jdk(atual):
        print("\nJAVA_HOME ja aponta para uma instalacao valida.")
        escolhido = atual
    else:
        secao("2. Procurando uma instalacao de Java valida")
        opcoes = candidatos_java()
        if not opcoes:
            print("Nenhuma instalacao valida encontrada.")
            print("Instale um JDK/JRE 17+ e rode de novo. Por exemplo:")
            print("  winget install --id EclipseAdoptium.Temurin.17.JRE")
            return
        for i, p in enumerate(opcoes):
            print(f"  [{i}] {p}")
        escolhido = opcoes[0]
        print(f"\nEscolhido: {escolhido}")

        secao("3. Gravando a variavel (nivel usuario, sem administrador)")
        cod, out, err = rodar(["setx", "JAVA_HOME", escolhido], 30)
        print(f"setx codigo={cod}")
        if out:
            print("  " + out)
        if err:
            print("  " + err)
        if cod != 0:
            print("\nNao foi possivel gravar. Defina manualmente em:")
            print("  Variaveis de Ambiente > Variaveis de usuario > Novo")
            print(f"  Nome: JAVA_HOME   Valor: {escolhido}")

    # Vale para ESTE processo, para ja testarmos sem abrir outro terminal.
    os.environ["JAVA_HOME"] = escolhido
    caminho_bin = os.path.join(escolhido, "bin")
    os.environ["PATH"] = caminho_bin + os.pathsep + os.environ.get("PATH", "")

    secao("4. Testando o SQLcl com o JAVA_HOME definido")
    sql = achar_sql()
    print(f"SQLcl: {sql or 'NAO ENCONTRADO'}")
    if not sql:
        print("Instale com: winget install --id Oracle.SQLcl")
        return

    cod, out, err = rodar([sql, "-version"], 120)
    print(f"\n$ sql -version   (codigo={cod})")
    print("  stdout: " + (out[:400] if out else "(vazio)"))
    if err:
        print("  stderr: " + err[:400])

    secao("5. Servidor MCP do SQLcl: ferramentas e schemas")
    import importlib.util
    if importlib.util.find_spec("mcp") is None:
        print("pacote mcp ausente. Rode: pip install mcp")
        return

    import asyncio
    import json
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def consultar():
        capturado = io.StringIO()
        try:
            params = StdioServerParameters(
                command=sql, args=["-mcp"],
                env={"JAVA_HOME": escolhido,
                     "PATH": caminho_bin + os.pathsep + os.environ.get("PATH", "")})
            async with stdio_client(params, errlog=capturado) as (read, write):
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
            s = capturado.getvalue().strip()
            if s:
                print("\n  >>> stderr do SQLcl (causa provavel):")
                for linha in s.splitlines()[:25]:
                    print("      " + linha)

    try:
        asyncio.run(consultar())
    except Exception as e:
        print(f"Erro geral: {detalhar(e)}")

    secao("FIM")
    print("Se conectou acima, copie a saida e cole na conversa.")
    print("Abra um terminal NOVO para o JAVA_HOME valer nos proximos usos.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
