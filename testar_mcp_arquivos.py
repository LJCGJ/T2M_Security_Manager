#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testar_mcp_arquivos.py - prova a trava do modo Arquivos, sem gastar IA.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
A protecao do modo Arquivos e uma afirmacao: "o servidor recusa qualquer caminho
fora da pasta permitida". Afirmacao nao verificada e exatamente o que este
produto existe para caçar nos outros - seria incoerente aceitar a nossa.

Aqui a trava e MEDIDA: sobe o servidor de verdade, pede a lista de ferramentas,
le um arquivo DENTRO da pasta (tem de funcionar) e tenta ler um arquivo FORA
dela (tem de ser recusado). Nenhuma requisicao de IA e feita, entao custa zero
de cota e pode rodar quantas vezes quiser.

Ja houve dois casos, neste projeto, de correcao construida sobre suposicao sobre
um servidor MCP: o navegador padrao do Playwright e a existencia do browser_find.
Os dois so foram resolvidos rodando o servidor e lendo a resposta. Este script e
esse habito virado ferramenta.

USO
    python testar_mcp_arquivos.py                 usa uma pasta temporaria de teste
    python testar_mcp_arquivos.py "C:\\caminho"    usa a sua pasta
"""

import asyncio
import os
import platform
import sys
import tempfile

ESCRITA = ("write_file", "edit_file", "create_directory", "move_file")
VERSAO = "2026.7.10"

_falhas = []


def diz(ok, texto, detalhe=""):
    print(f"   {'[OK]' if ok else '[X] '} {texto}")
    if detalhe:
        print(f"        {detalhe}")
    if not ok:
        _falhas.append(texto)


def _fora_da_pasta():
    """Um arquivo que existe, e que a automacao NAO pode ler."""
    if platform.system() == "Windows":
        for c in (r"C:\Windows\win.ini", r"C:\Windows\System32\drivers\etc\hosts"):
            if os.path.exists(c):
                return c
        return r"C:\Windows\win.ini"
    return "/etc/hostname"


async def provar(pasta):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    npx = "npx.cmd" if platform.system() == "Windows" else "npx"
    pacote = f"@modelcontextprotocol/server-filesystem@{VERSAO}"
    print(f"\n--- servidor: {pacote}")
    print(f"--- pasta permitida: {pasta}\n")

    params = StdioServerParameters(command=npx, args=["-y", pacote, pasta])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            nomes = sorted(t.name for t in (await s.list_tools()).tools)
            diz(len(nomes) >= 10, f"servidor respondeu com {len(nomes)} ferramentas",
                ", ".join(nomes))

            # O aplicativo esconde estas quatro por padrao. Se o servidor deixar
            # de oferece-las, o filtro vira letra morta - e ninguem perceberia.
            tem_escrita = [n for n in nomes if n in ESCRITA]
            diz(len(tem_escrita) == len(ESCRITA),
                "as ferramentas de escrita existem no servidor (o app e quem as esconde)",
                ", ".join(tem_escrita))

            r = await s.call_tool("list_allowed_directories", {})
            texto = " ".join(getattr(c, "text", "") for c in r.content)
            diz(os.path.basename(pasta.rstrip("\\/")) in texto or pasta in texto,
                "o servidor confirma qual pasta esta permitida", texto.strip()[:200])

            dentro = os.path.join(pasta, "prova_t2m.txt")
            with open(dentro, "w", encoding="utf-8") as f:
                f.write("conteudo de prova")
            r = await s.call_tool("read_text_file", {"path": dentro})
            lido = " ".join(getattr(c, "text", "") for c in r.content)
            diz("conteudo de prova" in lido,
                "arquivo DENTRO da pasta permitida e lido normalmente")

            # O teste que importa: um caminho legitimo, existente, e fora do
            # combinado. Recusar aqui e a unica razao de existir a pasta permitida.
            alvo = _fora_da_pasta()
            recusou, resposta = False, ""
            try:
                r = await s.call_tool("read_text_file", {"path": alvo})
                resposta = " ".join(getattr(c, "text", "") for c in r.content)
                recusou = bool(getattr(r, "isError", False)) or "not allowed" in resposta.lower() \
                    or "outside" in resposta.lower() or "access denied" in resposta.lower()
            except Exception as e:
                recusou, resposta = True, f"{type(e).__name__}: {e}"
            diz(recusou, f"arquivo FORA da pasta e RECUSADO ({alvo})",
                resposta.strip()[:200])

            # Subir um nivel com ".." e a tentativa mais obvia de escapar.
            fuga = os.path.join(pasta, "..", os.path.basename(_fora_da_pasta()))
            recusou2, resposta2 = False, ""
            try:
                r = await s.call_tool("read_text_file", {"path": fuga})
                resposta2 = " ".join(getattr(c, "text", "") for c in r.content)
                recusou2 = bool(getattr(r, "isError", False)) \
                    or "not allowed" in resposta2.lower() or "outside" in resposta2.lower() \
                    or "no such file" in resposta2.lower() or "enoent" in resposta2.lower()
            except Exception as e:
                recusou2, resposta2 = True, f"{type(e).__name__}: {e}"
            diz(recusou2, "caminho com '..' tentando sair da pasta tambem falha",
                resposta2.strip()[:200])

            try:
                os.remove(dentro)
            except OSError:
                pass


def main():
    pasta = sys.argv[1].strip('"') if len(sys.argv) > 1 else ""
    temporaria = False
    if not pasta:
        pasta = tempfile.mkdtemp(prefix="t2m_arquivos_")
        temporaria = True
    pasta = os.path.abspath(pasta)
    if not os.path.isdir(pasta):
        print(f"A pasta nao existe: {pasta}")
        return 2

    print("=" * 66)
    print("  PROVA DA TRAVA DO MODO ARQUIVOS - nenhuma requisicao de IA")
    print("=" * 66)
    try:
        asyncio.run(provar(pasta))
    except FileNotFoundError:
        print("\n  'npx' nao encontrado. Instale o Node 18+ de nodejs.org.")
        return 2
    except Exception as e:
        print(f"\n  Nao foi possivel falar com o servidor: {type(e).__name__}: {e}")
        return 2
    finally:
        if temporaria:
            try:
                os.rmdir(pasta)
            except OSError:
                pass

    print()
    print("=" * 66)
    if _falhas:
        print(f"  {len(_falhas)} FALHA(S). A trava NAO esta se comportando como o")
        print("  aplicativo afirma - nao ligue a escrita ate entender por que.")
    else:
        print("  Trava confirmada: dentro le, fora recusa.")
    print("=" * 66)
    return 1 if _falhas else 0


if __name__ == "__main__":
    sys.exit(main())
