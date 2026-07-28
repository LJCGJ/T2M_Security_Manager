# -*- coding: utf-8 -*-
"""
diagnostico_docker.py - Verifica os pre-requisitos do Docker Desktop no Windows.

O Docker Desktop nao roda sozinho: ele precisa do WSL2 (um Linux enxuto dentro
do Windows) e de virtualizacao habilitada. Quando falta um dos dois, o
instalador falha com "codigo de saida 1" sem dizer o motivo.

Este script SO CONSULTA. Nao instala e nao altera nada - ele diz o que falta e
qual comando resolve.

COMO USAR:
    python diagnostico_docker.py
"""

import re
import subprocess
import sys


def secao(t):
    print()
    print("=" * 64)
    print(f"  {t}")
    print("=" * 64)


def rodar(cmd, timeout=90):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           timeout=timeout)
        # O wsl.exe responde em UTF-16 no Windows; tentamos as duas leituras.
        bruto = (p.stdout or b"") + (p.stderr or b"")
        for enc in ("utf-16-le", "utf-8", "cp1252"):
            try:
                texto = bruto.decode(enc)
                if texto.count("\x00") < len(texto) // 4:
                    return p.returncode, texto.replace("\x00", "").strip()
            except Exception:
                continue
        return p.returncode, bruto.decode("utf-8", "replace").strip()
    except FileNotFoundError:
        return -1, "(comando nao encontrado)"
    except subprocess.TimeoutExpired:
        return -2, "(sem resposta)"
    except Exception as e:
        return -3, f"({type(e).__name__}: {e})"


def main():
    print("DIAGNOSTICO DO DOCKER DESKTOP - pre-requisitos")
    print("(so consulta; nao instala nem altera nada)")

    pendencias = []

    # ---------------------------------------------------------------
    secao("1. Versao do Windows")
    cod, saida = rodar(["cmd", "/c", "ver"])
    print(saida or "(sem saida)")
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", saida or "")
    if m:
        build = int(m.group(3))
        if build >= 22000:
            print("  Windows 11 - OK")
        elif build >= 19044:
            print("  Windows 10 recente - OK")
        else:
            print("  Build antiga demais para o Docker Desktop atual")
            pendencias.append("atualizar o Windows")

    # ---------------------------------------------------------------
    secao("2. Virtualizacao (precisa estar habilitada na BIOS)")
    cod, saida = rodar(
        ["powershell", "-NoProfile", "-Command",
         "(Get-CimInstance Win32_ComputerSystem).HypervisorPresent"])
    hv = "true" in (saida or "").lower()
    print(f"  Hipervisor ativo: {saida.strip() or '(sem resposta)'}")
    if hv:
        print("  OK - a virtualizacao esta funcionando")
    else:
        cod2, s2 = rodar(["powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled"])
        print(f"  Virtualizacao habilitada na BIOS: {s2.strip() or '(sem resposta)'}")
        if "false" in (s2 or "").lower():
            print("\n  >>> A virtualizacao esta DESLIGADA na BIOS.")
            print("      Reinicie, entre na BIOS/UEFI e habilite:")
            print("        Intel -> 'Intel VT-x' ou 'Intel Virtualization Technology'")
            print("        AMD   -> 'SVM Mode' ou 'AMD-V'")
            pendencias.append("habilitar a virtualizacao na BIOS")
        else:
            print("\n  >>> A CPU suporta, mas o hipervisor nao esta ativo.")
            print("      Costuma ser resolvido junto com o WSL, no passo 3.")
            pendencias.append("ativar o hipervisor (normalmente resolve com o WSL)")

    # ---------------------------------------------------------------
    secao("3. WSL2 (o Docker Desktop depende dele)")
    cod, saida = rodar(["wsl", "--status"])
    if cod != 0 or not saida or "nao" in (saida or "").lower()[:40]:
        print("  WSL nao parece instalado.")
        print(f"  resposta: {(saida or '')[:200]}")
        pendencias.append("instalar o WSL")
    else:
        print(saida[:500])
        print("  OK - o WSL respondeu")

    cod, saida = rodar(["wsl", "-l", "-v"])
    print("\n  Distribuicoes instaladas:")
    print("  " + (saida[:400].replace("\n", "\n  ") if saida else "(nenhuma)"))
    if saida and re.search(r"\s1\s*$", saida, re.M):
        print("\n  >>> Ha distribuicao rodando em WSL versao 1. O Docker exige a 2.")
        pendencias.append("converter a distribuicao para WSL 2")

    # ---------------------------------------------------------------
    secao("4. Docker instalado?")
    cod, saida = rodar(["docker", "--version"])
    print(f"  docker --version: {saida[:120] if saida else '(nao encontrado)'}")
    cod2, saida2 = rodar(["docker", "info", "--format", "{{.ServerVersion}}"], 40)
    if cod2 == 0 and saida2.strip():
        print(f"  motor rodando: versao {saida2.strip()}")
        print("\n  TUDO PRONTO. Pode rodar: python subir_oracle_teste.py")
        return
    print("  motor nao esta respondendo (normal se o Docker Desktop nao estiver aberto)")

    # ---------------------------------------------------------------
    secao("O QUE FAZER")
    if not pendencias:
        print("Os pre-requisitos parecem OK.")
        print("\n1. Abra o Docker Desktop pelo menu Iniciar e espere a baleia")
        print("   no canto da barra de tarefas ficar estavel.")
        print("2. Rode este diagnostico de novo para confirmar.")
        print("\nSe o Docker Desktop nao estiver instalado:")
        print("   winget install --id Docker.DockerDesktop")
        return

    print("Pendencias encontradas:")
    for i, p in enumerate(pendencias, 1):
        print(f"  {i}. {p}")

    print("\nCaminho recomendado, na ordem:")
    print()
    print("  1) Abra o PowerShell COMO ADMINISTRADOR e rode:")
    print()
    print("       wsl --install")
    print()
    print("     Isso instala o WSL2, liga os recursos do Windows que faltam")
    print("     (Plataforma de Maquina Virtual) e baixa uma distribuicao Linux.")
    print()
    print("  2) REINICIE o computador. E obrigatorio.")
    print()
    print("  3) Depois do reinicio, rode este diagnostico de novo.")
    print()
    print("  4) So entao instale o Docker Desktop:")
    print()
    print("       winget install --id Docker.DockerDesktop")
    print()
    if "habilitar a virtualizacao na BIOS" in pendencias:
        print("  ATENCAO: o passo da BIOS vem ANTES de tudo. Sem virtualizacao,")
        print("  nem o WSL2 nem o Docker funcionam.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
