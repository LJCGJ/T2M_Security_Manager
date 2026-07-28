# -*- coding: utf-8 -*-
"""
limpar_disco.py - Remove o Docker por completo e libera espaco no Windows.

COMO FUNCIONA:
    1. Mostra o espaco livre e o tamanho de cada coisa que pode ser removida
    2. Pergunta ANTES de cada categoria; nada e apagado sem voce confirmar
    3. Mostra quanto foi liberado no final

NAO TOCA em documentos, downloads, projetos ou nada seu. So mexe em cache,
temporarios e sobras de instalacao.

COMO USAR:
    python limpar_disco.py            # mostra e pergunta
    python limpar_disco.py --relatorio  # SO mostra, nao pergunta nada

Varias limpezas exigem PowerShell/Prompt como ADMINISTRADOR. O script avisa.
"""

import ctypes
import os
import shutil
import subprocess
import sys

SO_RELATORIO = "--relatorio" in sys.argv


def secao(t):
    print()
    print("=" * 66)
    print(f"  {t}")
    print("=" * 66)


def gb(n):
    return f"{n / (1024 ** 3):.2f} GB"


def eh_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def espaco_livre(caminho="C:\\"):
    try:
        return shutil.disk_usage(caminho)
    except Exception:
        return None


def tamanho(caminho):
    """Tamanho de uma pasta, tolerante a arquivos sem permissao."""
    if not caminho or not os.path.exists(caminho):
        return 0
    if os.path.isfile(caminho):
        try:
            return os.path.getsize(caminho)
        except Exception:
            return 0
    total = 0
    for raiz, _, arquivos in os.walk(caminho, onerror=lambda e: None):
        for a in arquivos:
            try:
                total += os.path.getsize(os.path.join(raiz, a))
            except Exception:
                pass
    return total


def rodar(cmd, timeout=1800, mostrar=True):
    try:
        p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                           timeout=timeout, errors="replace", text=True)
        saida = ((p.stdout or "") + (p.stderr or "")).strip()
        if mostrar and saida:
            print("    " + saida[:400].replace("\n", "\n    "))
        return p.returncode
    except Exception as e:
        print(f"    ({type(e).__name__}: {e})")
        return -1


def apagar(caminho):
    """Apaga arquivo ou pasta, ignorando o que estiver em uso."""
    try:
        if os.path.isfile(caminho):
            os.unlink(caminho)
        else:
            shutil.rmtree(caminho, ignore_errors=True)
        return True
    except Exception:
        return False


def confirmar(pergunta):
    if SO_RELATORIO:
        return False
    return input(f"    {pergunta} (s/N): ").strip().lower() == "s"


def pastas_docker():
    la = os.environ.get("LOCALAPPDATA", "")
    ad = os.environ.get("APPDATA", "")
    pd = os.environ.get("ProgramData", "")
    up = os.environ.get("USERPROFILE", "")
    pf = os.environ.get("ProgramFiles", "")
    return [c for c in [
        os.path.join(pd, "Docker"),
        os.path.join(pd, "DockerDesktop"),
        os.path.join(ad, "Docker"),
        os.path.join(ad, "Docker Desktop"),
        os.path.join(la, "Docker"),
        os.path.join(pf, "Docker"),
        os.path.join(up, ".docker"),
    ] if c and os.path.exists(c)]


def main():
    print("LIMPEZA DE DISCO - remocao do Docker e liberacao de espaco")
    admin = eh_admin()
    print(f"Executando como administrador: {'SIM' if admin else 'NAO'}")
    if not admin:
        print("  (algumas limpezas serao puladas; para todas, abra como admin)")

    u = espaco_livre()
    if u:
        print(f"\nDisco C:  total {gb(u.total)}  |  usado {gb(u.used)}  |  "
              f"LIVRE {gb(u.free)}")
        livre_antes = u.free
    else:
        livre_antes = 0

    # ---------------------------------------------------------------
    secao("1. Docker Desktop")
    cod = rodar(["winget", "list", "--id", "Docker.DockerDesktop"], 120, mostrar=False)
    instalado = cod == 0
    print(f"  Instalado pelo winget: {'sim' if instalado else 'nao (ou instalacao parcial)'}")

    pastas = pastas_docker()
    total_docker = sum(tamanho(p) for p in pastas)
    for p in pastas:
        print(f"    {gb(tamanho(p)):>10}  {p}")
    print(f"  Total em pastas do Docker: {gb(total_docker)}")

    if instalado and confirmar("Desinstalar o Docker Desktop?"):
        print("    desinstalando (pode demorar)...")
        rodar(["winget", "uninstall", "--id", "Docker.DockerDesktop",
               "--silent", "--force"], 1800)

    if pastas and confirmar(f"Apagar as pastas do Docker ({gb(total_docker)})?"):
        for p in pastas:
            print(f"    {'ok' if apagar(p) else 'em uso/negado'}: {p}")

    # ---------------------------------------------------------------
    secao("2. Distribuicoes do WSL")
    cod = rodar(["wsl", "--list", "--quiet"], 60, mostrar=True)
    if cod == 0 and not SO_RELATORIO:
        print("\n  Distribuicoes do Docker (docker-desktop*) podem ser removidas.")
        print("  ATENCAO: nao remova uma distribuicao sua com arquivos dentro.")
        alvo = input("    Nome da distribuicao a remover (Enter para pular): ").strip()
        if alvo:
            rodar(["wsl", "--unregister", alvo], 300)

    # ---------------------------------------------------------------
    secao("3. Instaladores baixados pelo winget")
    la = os.environ.get("LOCALAPPDATA", "")
    cache = os.path.join(la, "Packages")
    alvos = []
    if os.path.isdir(cache):
        for nome in os.listdir(cache):
            if "DesktopAppInstaller" in nome:
                for sub in ("LocalState", "TempState"):
                    c = os.path.join(cache, nome, sub)
                    if os.path.isdir(c):
                        alvos.append(c)
    t = sum(tamanho(a) for a in alvos)
    for a in alvos:
        print(f"    {gb(tamanho(a)):>10}  {a}")
    print(f"  Total: {gb(t)}   (sao os .exe ja instalados; seguro apagar)")
    if alvos and t > 0 and confirmar("Limpar?"):
        for a in alvos:
            for nome in os.listdir(a):
                apagar(os.path.join(a, nome))
        print("    limpo")

    # ---------------------------------------------------------------
    secao("4. Temporarios")
    temps = [os.environ.get("TEMP", ""), "C:\\Windows\\Temp"]
    t = sum(tamanho(x) for x in temps if x)
    for x in temps:
        if x:
            print(f"    {gb(tamanho(x)):>10}  {x}")
    print(f"  Total: {gb(t)}")
    if t > 0 and confirmar("Limpar temporarios?"):
        n = 0
        for x in temps:
            if not x or not os.path.isdir(x):
                continue
            for nome in os.listdir(x):
                if apagar(os.path.join(x, nome)):
                    n += 1
        print(f"    {n} itens removidos (os em uso foram mantidos)")

    # ---------------------------------------------------------------
    secao("5. Cache do Windows Update")
    wu = "C:\\Windows\\SoftwareDistribution\\Download"
    print(f"    {gb(tamanho(wu)):>10}  {wu}")
    if not admin:
        print("  (precisa de administrador)")
    elif tamanho(wu) > 0 and confirmar("Limpar? O Windows rebaixa o que precisar."):
        rodar(["net", "stop", "wuauserv"], 120, mostrar=False)
        for nome in os.listdir(wu):
            apagar(os.path.join(wu, nome))
        rodar(["net", "start", "wuauserv"], 120, mostrar=False)
        print("    limpo")

    # ---------------------------------------------------------------
    secao("6. Componentes antigos do Windows (WinSxS)")
    print("  Remove versoes antigas de atualizacoes. Costuma liberar varios GB")
    print("  e ajuda no erro 14098, que precisa de espaco para se reparar.")
    if not admin:
        print("  (precisa de administrador)")
    elif confirmar("Rodar a limpeza? Demora 10-20 min."):
        rodar(["dism", "/online", "/cleanup-image", "/startcomponentcleanup",
               "/resetbase"], 3600)

    # ---------------------------------------------------------------
    secao("7. Arquivo de hibernacao")
    hib = "C:\\hiberfil.sys"
    th = tamanho(hib)
    print(f"    {gb(th):>10}  {hib}")
    print("  Costuma ter o tamanho da memoria RAM. Desligar remove a hibernacao")
    print("  (o suspender continua funcionando).")
    if not admin:
        print("  (precisa de administrador)")
    elif th > 0 and confirmar("Desligar a hibernacao?"):
        rodar(["powercfg", "/h", "off"], 120)

    # ---------------------------------------------------------------
    secao("RESULTADO")
    u2 = espaco_livre()
    if u2:
        print(f"  Livre agora : {gb(u2.free)}")
        if livre_antes:
            d = u2.free - livre_antes
            print(f"  Liberado    : {gb(d)}" if d > 0 else "  (sem mudanca ainda)")
    print("\n  Outros lugares que costumam ocupar muito, veja no Explorador:")
    print("    C:\\Windows.old            (instalacao anterior do Windows)")
    print("    Downloads                 (instaladores antigos)")
    print("    Configuracoes > Sistema > Armazenamento > Sensor de Armazenamento")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if sys.platform != "win32":
        print("Este script e para Windows.")
        sys.exit(0)
    main()
