#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verificar_instalador.py - confere o instalador do T2M por linha de comando.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O roteiro_instalador.html tem quinze itens. A maioria e mecanica: conferir se um
arquivo esta na lista, se o tamanho bate, se sobrou dado pessoal na pasta. Isso
nao precisa de olho humano - precisa de alguem que nao se canse e nao pule o
item 8 porque o 7 passou.

O que este script NAO faz: julgar tela. Aviso do SmartScreen, texto da licenca,
a janela do preparador de ambiente aparecendo na hora certa, a primeira execucao
numa maquina limpa e o dialogo da desinstalacao continuam sendo dos olhos de
alguem. Ele diz, no fim, quais itens ficaram para voce.

A diferenca para o verificar_antes_do_instalador.bat: aquele tem a lista de
arquivos escrita a mao, entao ele so sabe o que alguem lembrou de escrever - e
foi por isso que o servidor_http_mcp.py faltou por versoes sem ninguem notar.
Aqui a lista e LIDA do proprio instalador_t2m.iss e cruzada com o que o codigo
procura em tempo de execucao. A pergunta deixa de ser "os arquivos que eu listei
estao la?" e passa a ser "o instalador leva tudo o que o programa vai pedir?".

USO
    python verificar_instalador.py                 confere o projeto (antes de compilar)
    python verificar_instalador.py --instalado     confere tambem a maquina onde foi instalado
    python verificar_instalador.py --autoteste     testa este script, sem tocar no projeto
"""

import os
import re
import sys
import subprocess
import tempfile

# Arquivos que nunca podem viajar dentro do instalador. Nao e higiene: o
# api_keys_ia.txt da pasta Release tem chaves de API de verdade.
NUNCA_EMPACOTAR = (
    "api_keys_ia.txt", "config.txt", "memoria_chat.json", "last_ai_key.txt",
    "ultima_chave.txt", "tema.txt", "vereditos_modelos.txt",
    "teste_t2m.db", "nota_llama.json", "nota_gemini.json",
)

# Sobra de teste que o curinga levava junto quando a lista usava *.png / *.ico.
PADRAO_SOBRA = re.compile(r"(login[\w\-]*\.png|icon2_antigo\.ico|.*\.pdb|.*\.db)$", re.I)

ERROS = []
AVISOS = []


def dizer(estado, texto, detalhe=""):
    marca = {"ok": "[OK]", "erro": "[X] ", "aviso": "[!] "}[estado]
    print(f"   {marca} {texto}")
    if detalhe:
        print(f"        {detalhe}")
    if estado == "erro":
        ERROS.append(texto)
    elif estado == "aviso":
        AVISOS.append(texto)


def titulo(t):
    print()
    print(f"--- {t} ---")


# ================================================================== #
# LEITURA DO INSTALADOR                                              #
# ================================================================== #

def ler_defines(iss):
    """#define Nome "valor" -> {"Nome": "valor"}"""
    return dict(re.findall(r'#define\s+(\w+)\s+"([^"]*)"', iss))


def resolver(caminho, defines):
    """Troca {#PastaRelease} e amigos pelos valores do proprio .iss.

    Normaliza a barra tambem. O .iss e escrito com barra invertida do Windows,
    e fora dele o os.path nao a reconhece como separador: basename devolvia o
    caminho inteiro e a conferencia de dado pessoal passava batido. Rodar so no
    Windows nao serve - o autoteste precisa valer em qualquer lugar."""
    def troca(m):
        return defines.get(m.group(1), m.group(0))
    resolvido = re.sub(r"\{#(\w+)\}", troca, caminho)
    if os.sep != "\\":
        resolvido = resolvido.replace("\\", os.sep)
    return resolvido


def nome_do_arquivo(caminho):
    """Ultimo pedaco do caminho, com qualquer uma das duas barras."""
    return re.split(r"[\\/]", caminho)[-1]


def ler_fontes(iss):
    """Devolve [(caminho_bruto, flags)] de cada linha Source: da secao [Files].

    Le so o que esta dentro de [Files]: um Source citado num comentario de outra
    secao nao vale como arquivo empacotado.
    """
    fontes = []
    dentro = False
    for linha in iss.splitlines():
        nu = linha.strip()
        if nu.startswith("["):
            dentro = nu.lower().startswith("[files]")
            continue
        if not dentro or nu.startswith(";") or not nu:
            continue
        m = re.search(r'Source:\s*"([^"]+)"', nu)
        if not m:
            continue
        flags = ""
        mf = re.search(r"Flags:\s*([^;]+)", nu)
        if mf:
            flags = mf.group(1).strip().lower()
        fontes.append((m.group(1), flags))
    return fontes


def scripts_exigidos(texto_agente, texto_ui):
    """Nomes de .py que o programa procura em tempo de execucao.

    Duas origens, porque sao dois jeitos de sumir: o agente carrega vizinhos por
    SCRIPT_DIR, e o C++ dispara scripts pelo nome.
    """
    nomes = set(re.findall(
        r'os\.path\.join\(SCRIPT_DIR,\s*["\']([A-Za-z0-9_\-]+\.py)["\']', texto_agente))
    nomes |= set(re.findall(r'"([A-Za-z0-9_\-]+\.py)"', texto_ui))
    return nomes


# ================================================================== #
# CONFERENCIAS - PROJETO (antes de compilar o instalador)            #
# ================================================================== #

def conferir_projeto(raiz):
    iss_path = os.path.join(raiz, "instalador_t2m.iss")
    if not os.path.exists(iss_path):
        dizer("erro", "instalador_t2m.iss nao encontrado", f"procurado em {raiz}")
        return
    iss = open(iss_path, encoding="utf-8", errors="replace").read()
    defines = ler_defines(iss)
    fontes = ler_fontes(iss)

    titulo(f"1. Instalador {defines.get('VersaoApp', '?')} - lista de arquivos")
    dizer("ok", f"{len(fontes)} arquivos listados em [Files]")

    # ---- curinga na Release: leva sobra de teste sem ninguem revisar
    curingas = [c for c, _ in fontes if "*" in c and "PastaRelease" in c]
    if curingas:
        dizer("erro", "ha curinga apontando para a pasta Release",
              " / ".join(curingas) + " - a Release acumula sobra de teste")
    else:
        dizer("ok", "nenhum curinga na pasta Release")

    # ---- todo Source tem de existir AGORA
    # skipifsourcedoesntexist e a armadilha: o Inno compila calado e o arquivo
    # simplesmente nao vai. O instalador fica pronto, menor, e quebrado.
    faltando_duro, faltando_silencioso = [], []
    for bruto, flags in fontes:
        caminho = resolver(bruto, defines)
        if "*" in caminho:
            continue
        if not os.path.exists(caminho):
            if "skipifsourcedoesntexist" in flags:
                faltando_silencioso.append(caminho)
            else:
                faltando_duro.append(caminho)
    if faltando_duro:
        dizer("erro", "arquivo listado que nao existe (o Inno vai recusar compilar)",
              " / ".join(faltando_duro))
    if faltando_silencioso:
        dizer("erro", "arquivo ausente com skipifsourcedoesntexist: some sem aviso",
              " / ".join(faltando_silencioso))
    if not faltando_duro and not faltando_silencioso:
        dizer("ok", "todo arquivo listado existe no disco")

    # ---- dado pessoal nunca pode estar na lista
    listados = {nome_do_arquivo(resolver(c, defines)).lower() for c, _ in fontes}
    vazando = sorted(n for n in NUNCA_EMPACOTAR if n.lower() in listados)
    if vazando:
        dizer("erro", "DADO PESSOAL na lista do instalador", " / ".join(vazando))
    else:
        dizer("ok", "nenhum dado pessoal na lista (chaves, config, memoria)")

    # ---- o que o programa procura tem de estar na lista
    titulo("2. O instalador leva tudo o que o programa pede?")
    agente = os.path.join(raiz, "T2M_Security_Manager", "agente_mcp.py")
    ui = os.path.join(raiz, "T2M_Security_Manager", "MyForm.h")
    if os.path.exists(agente) and os.path.exists(ui):
        exigidos = scripts_exigidos(
            open(agente, encoding="utf-8", errors="replace").read(),
            open(ui, encoding="utf-8", errors="replace").read())
        ausentes = sorted(n for n in exigidos if n.lower() not in listados)
        dizer("ok", f"scripts procurados em tempo de execucao: {len(exigidos)}",
              ", ".join(sorted(exigidos)))
        if ausentes:
            dizer("erro", "script que o programa procura e o instalador NAO leva",
                  " / ".join(ausentes) + " - falha so na maquina de quem instalou")
        else:
            dizer("ok", "todos eles estao na lista do instalador")
    else:
        dizer("aviso", "codigo-fonte nao encontrado; cruzamento nao feito")

    # ---- Release atualizada
    titulo("3. A Release esta com o codigo de agora?")
    src = os.path.join(raiz, "T2M_Security_Manager")
    rel = os.path.join(raiz, "x64", "Release")
    desatualizados = []
    for nome in sorted(os.listdir(src)) if os.path.isdir(src) else []:
        if not nome.endswith(".py"):
            continue
        a, b = os.path.join(src, nome), os.path.join(rel, nome)
        if not os.path.exists(b):
            desatualizados.append(f"{nome} (nao existe na Release)")
        elif os.path.getsize(a) != os.path.getsize(b):
            desatualizados.append(
                f"{nome} ({os.path.getsize(a)} no projeto x {os.path.getsize(b)} na Release)")
    if desatualizados:
        dizer("erro", "a Release tem Python diferente do projeto: RECOMPILE",
              " / ".join(desatualizados))
    elif os.path.isdir(rel):
        dizer("ok", "os .py da Release batem com os do projeto")
    else:
        dizer("aviso", "pasta x64\\Release nao encontrada")

    # ---- pacote gerado
    titulo("4. Pacote gerado")
    versao = defines.get("VersaoApp", "")
    esperado = os.path.join(raiz, "Saida", f"T2M_Security_Manager_Setup_{versao}.exe")
    exe = os.path.join(rel, "T2M_Security_Manager.exe")
    if os.path.exists(esperado):
        dizer("ok", f"instalador {versao} encontrado",
              f"{os.path.getsize(esperado) // 1024} KB")
        if os.path.exists(exe) and os.path.getmtime(exe) > os.path.getmtime(esperado):
            dizer("erro", "o .exe do programa e MAIS NOVO que o instalador",
                  "o pacote foi gerado antes da ultima compilacao; gere de novo")
        else:
            dizer("ok", "o instalador e mais novo que o executavel")
    else:
        dizer("aviso", f"instalador {versao} ainda nao gerado",
              "compile o instalador_t2m.iss no Inno Setup (F9)")


# ================================================================== #
# CONFERENCIAS - MAQUINA INSTALADA                                   #
# ================================================================== #

def _reg_query(chave):
    try:
        r = subprocess.run(["reg", "query", chave, "/s"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout or ""
    except Exception:
        return ""


def _blocos_do_registro(saida):
    """Quebra a saida de `reg query /s` em (chave, {valor: dado}).

    Fazia falta. A primeira versao desta funcao procurava a palavra "T2M" numa
    lista de linhas que ela mesma nao delimitava direito, e acabou apontando o
    Panda Aether Agent como sendo o T2M - depois disso, TODOS os 14 arquivos
    apareceram como "nao chegaram", porque estavam sendo procurados na pasta de
    outro programa. Um verificador que acusa o inocente e tao inutil quanto um
    que absolve o culpado: nos dois casos o operador para de acreditar nele.
    """
    chave, valores = None, {}
    padrao = re.compile(r"^\s+(\S.*?)\s{2,}(REG_\w+)\s{2,}(.*)$")
    for linha in saida.splitlines():
        if not linha.strip():
            continue
        if not linha.startswith(" "):
            if chave:
                yield chave, valores
            chave, valores = linha.strip(), {}
            continue
        m = padrao.match(linha)
        if m and chave:
            valores[m.group(1).strip()] = m.group(3).strip()
    if chave:
        yield chave, valores


def ler_appid(raiz):
    """AppId do proprio .iss. O Inno cria a chave de desinstalacao com ele mais
    o sufixo _is1, entao procurar por esse nome e exato - nao depende de o
    DisplayName estar escrito de um jeito ou de outro."""
    try:
        iss = open(os.path.join(raiz, "instalador_t2m.iss"),
                   encoding="utf-8", errors="replace").read()
        m = re.search(r"^AppId=\{\{(.+)$", iss, re.M)
        if m:
            return "{" + m.group(1).strip() + "}"
    except Exception:
        pass
    return ""


def achar_instalacoes(raiz_projeto):
    """Procura o T2M nas tres arvores de desinstalacao do Windows.

    Duas entradas para o mesmo programa significam AppId trocado entre versoes:
    cada atualizacao vira instalacao paralela e o usuario nao sabe qual abriu.
    """
    appid = ler_appid(raiz_projeto).lower()
    achados = {}
    for raiz in (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                 r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                 r"HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"):
        for chave, valores in _blocos_do_registro(_reg_query(raiz)):
            nome = valores.get("DisplayName", "")
            # Duas identificacoes, ambas exatas: o AppId na chave (como o Inno
            # a cria) ou o nome do produto inteiro. "T2M" solto nao serve -
            # casava com qualquer outro programa que tivesse essas letras.
            bate_id = bool(appid) and appid in chave.lower()
            bate_nome = nome.strip().lower() == "t2m security manager"
            if bate_id or bate_nome:
                pasta = (valores.get("InstallLocation", "")
                         or os.path.dirname(valores.get("UninstallString", "").strip('"')))
                achados[chave] = (pasta.rstrip("\\"), valores.get("DisplayVersion", ""))
    pastas = sorted({p for p, _ in achados.values() if p})
    versoes = sorted({v for _, v in achados.values() if v})
    return pastas, versoes


def conferir_instalado(raiz):
    titulo("5. Maquina onde o T2M foi instalado")
    if os.name != "nt":
        dizer("aviso", "so roda no Windows; conferencia da instalacao pulada")
        return
    pastas, versoes = achar_instalacoes(raiz)
    if not pastas:
        dizer("aviso", "nenhuma instalacao encontrada no registro",
              "instale o pacote e rode de novo com --instalado")
        return
    if len(pastas) > 1:
        dizer("erro", "MAIS DE UMA instalacao registrada", " / ".join(pastas)
              + " - AppId mudou entre versoes; atualizar cria copia paralela")
    else:
        dizer("ok", f"uma unica instalacao: {pastas[0]}"
                    + (f" (versao {versoes[0]})" if versoes else ""))

    app = pastas[0]
    iss = open(os.path.join(raiz, "instalador_t2m.iss"),
               encoding="utf-8", errors="replace").read()
    defines = ler_defines(iss)
    esperados = sorted({nome_do_arquivo(resolver(c, defines))
                        for c, _ in ler_fontes(iss) if "*" not in c})
    ausentes = [n for n in esperados if not os.path.exists(os.path.join(app, n))]
    if len(ausentes) == len(esperados):
        # Nenhum arquivo, nem o executavel: e muito mais provavel que a pasta
        # esteja errada do que uma instalacao ter copiado zero arquivos. Culpar
        # o instalador aqui foi o erro da primeira versao deste script.
        dizer("erro", "a pasta encontrada nao parece ser a do T2M",
              f"{app} - nem o executavel esta la; a deteccao no registro errou "
              f"ou o programa nao chegou a ser instalado")
    elif ausentes:
        dizer("erro", "arquivo listado que NAO chegou na instalacao", " / ".join(ausentes))
    else:
        dizer("ok", f"os {len(esperados)} arquivos do pacote chegaram")

    try:
        presentes = os.listdir(app)
    except Exception:
        presentes = []
    intrusos = [n for n in presentes
                if n.lower() in [x.lower() for x in NUNCA_EMPACOTAR]
                or PADRAO_SOBRA.match(n)]
    if intrusos:
        dizer("erro", "arquivo que nao devia ter sido instalado", " / ".join(intrusos))
    else:
        dizer("ok", "nenhum dado pessoal ou sobra de teste na pasta instalada")

    titulo("6. Atalhos, dados e ambiente")
    atalhos = [
        os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                     "Start Menu", "Programs", "T2M Security Manager"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows",
                     "Start Menu", "Programs", "T2M Security Manager"),
    ]
    if any(os.path.isdir(a) for a in atalhos):
        dizer("ok", "grupo do menu Iniciar criado")
    else:
        dizer("aviso", "grupo do menu Iniciar nao encontrado")

    dados = os.path.join(os.environ.get("APPDATA", ""), "T2M Security Manager")
    if os.path.isdir(dados):
        dizer("ok", "configuracoes gravadas em %APPDATA% (nao na pasta do programa)")
    else:
        dizer("aviso", "pasta de dados ainda nao criada",
              "abra o app uma vez e salve algo em Configuracoes")

    for exe, nome in (("python", "Python"), ("npx", "Node/npx")):
        try:
            r = subprocess.run(["where", exe], capture_output=True, text=True, timeout=20)
            caminho = (r.stdout or "").strip().splitlines()
            if r.returncode == 0 and caminho:
                perfil = caminho[0]
                # O preparador de ambiente roda com runasoriginaluser justamente
                # para nao instalar no perfil do administrador. Se cair la, o
                # usuario real abre o app e nada esta instalado.
                if "\\Users\\" in perfil and os.environ.get("USERNAME", "zzz") not in perfil:
                    dizer("erro", f"{nome} instalado em OUTRO perfil de usuario", perfil)
                else:
                    dizer("ok", f"{nome} no PATH", perfil)
            else:
                dizer("aviso", f"{nome} nao encontrado no PATH")
        except Exception:
            dizer("aviso", f"nao foi possivel consultar {nome}")


# ================================================================== #
# AUTOTESTE - confere este script sem tocar no projeto               #
# ================================================================== #

def autoteste():
    """Monta um projeto de mentira com defeitos conhecidos e exige que apareçam.

    Sem isto, um erro de regex faria o script dizer "tudo certo" para sempre - e
    um verificador que so sabe aprovar e pior do que nenhum.
    """
    global ERROS, AVISOS
    base = tempfile.mkdtemp(prefix="t2m_autoteste_")
    src = os.path.join(base, "T2M_Security_Manager")
    rel = os.path.join(base, "x64", "Release")
    os.makedirs(src)
    os.makedirs(rel)

    def escrever(caminho, texto=""):
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)

    escrever(os.path.join(src, "agente_mcp.py"),
             'x = os.path.join(SCRIPT_DIR, "servidor_http_mcp.py")\n')
    escrever(os.path.join(rel, "agente_mcp.py"),
             'x = os.path.join(SCRIPT_DIR, "servidor_http_mcp.py")\nsobra\n')  # tamanho diferente
    escrever(os.path.join(src, "MyForm.h"), 'String^ s = "gerador_ia.py";\n')
    escrever(os.path.join(rel, "gerador_ia.py"))
    escrever(os.path.join(rel, "api_keys_ia.txt"), "sk-secreta")

    iss = (
        '#define VersaoApp      "9.9"\n'
        f'#define PastaRelease   "{rel}"\n'
        "[Files]\n"
        'Source: "{#PastaRelease}\\agente_mcp.py"; DestDir: "{app}"\n'
        'Source: "{#PastaRelease}\\gerador_ia.py"; DestDir: "{app}"\n'
        'Source: "{#PastaRelease}\\api_keys_ia.txt"; DestDir: "{app}"\n'
        'Source: "{#PastaRelease}\\*.png"; DestDir: "{app}"; Flags: skipifsourcedoesntexist\n'
        'Source: "{#PastaRelease}\\sumido.ico"; DestDir: "{app}"; Flags: skipifsourcedoesntexist\n'
        "[Icons]\n"
        'Source: "{#PastaRelease}\\nao_conta.py"; DestDir: "{app}"\n'
    )
    escrever(os.path.join(base, "instalador_t2m.iss"), iss)

    # A secao [Icons] nao pode contaminar a lista de arquivos.
    fontes = ler_fontes(iss)
    assert len(fontes) == 5, f"[Files] mal delimitada: {len(fontes)} fontes"

    ERROS, AVISOS = [], []
    saida_real = sys.stdout
    try:
        with open(os.devnull, "w") as mudo:
            sys.stdout = mudo
            conferir_projeto(base)
    finally:
        sys.stdout = saida_real

    # ---- leitura do registro: o defeito que fez o script acusar o inocente
    # Saida real de `reg query /s`, com dois programas. A primeira versao desta
    # leitura apontou o Panda Aether Agent como sendo o T2M e depois declarou
    # que nenhum dos 14 arquivos tinha chegado - eles estavam sendo procurados
    # na pasta de outro programa. O caso fica aqui para nao voltar.
    amostra = (
        "\n"
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\PandaAether\n"
        "    DisplayName    REG_SZ    Panda Aether Agent\n"
        "    DisplayVersion    REG_SZ    2.20.01\n"
        "    InstallLocation    REG_SZ    C:\\Program Files (x86)\\Panda Security\\Panda Aether Agent\n"
        "\n"
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\"
        "{8F3A2C41-7B95-4E62-A1D8-T2MSECMGR2026}_is1\n"
        "    DisplayName    REG_SZ    T2M Security Manager\n"
        "    DisplayVersion    REG_SZ    4.3\n"
        "    InstallLocation    REG_SZ    C:\\Program Files (x86)\\T2M Security Manager\\\n"
    )
    blocos = list(_blocos_do_registro(amostra))
    if len(blocos) != 2:
        print(f">>> AUTOTESTE FALHOU: registro lido como {len(blocos)} blocos, esperado 2")
        return 1
    nomes = {v.get("DisplayName", "") for _, v in blocos}
    if nomes != {"Panda Aether Agent", "T2M Security Manager"}:
        print(f">>> AUTOTESTE FALHOU: nomes lidos do registro: {nomes}")
        return 1
    casados = [c for c, v in blocos
               if v.get("DisplayName", "").strip().lower() == "t2m security manager"
               or "t2msecmgr2026" in c.lower()]
    if len(casados) != 1 or "Panda" in casados[0]:
        print(">>> AUTOTESTE FALHOU: a identificacao do T2M pegou o programa errado")
        return 1

    achados = " | ".join(ERROS)
    esperados = {
        "curinga": "curinga",
        "some sem aviso": "skipifsourcedoesntexist",
        "DADO PESSOAL": "chave de API na lista",
        "instalador NAO leva": "servidor_http_mcp.py ausente da lista",
        "RECOMPILE": "Release diferente do projeto",
    }
    faltou = [d for chave, d in esperados.items() if chave not in achados]
    if faltou:
        print(">>> AUTOTESTE FALHOU: nao detectou -> " + " / ".join(faltou))
        return 1
    print(f">>> Autoteste OK: os {len(esperados)} defeitos plantados foram detectados.")
    print(">>> (curinga, arquivo que some calado, chave de API empacotada,")
    print(">>>  script exigido fora da lista e Release desatualizada)")
    return 0


# ================================================================== #

def main():
    raiz = os.path.dirname(os.path.abspath(__file__))
    if "--autoteste" in sys.argv:
        return autoteste()

    print()
    print("=" * 66)
    print("  VERIFICACAO DO INSTALADOR - T2M Security Manager")
    print("=" * 66)

    conferir_projeto(raiz)
    if "--instalado" in sys.argv:
        conferir_instalado(raiz)

    print()
    print("=" * 66)
    if ERROS:
        print(f"  {len(ERROS)} ERRO(S) e {len(AVISOS)} aviso(s). Corrija antes de publicar.")
    elif AVISOS:
        print(f"  Sem erros, com {len(AVISOS)} aviso(s).")
    else:
        print("  Tudo certo na parte mecanica.")
    print("-" * 66)
    print("  Continuam sendo do olho humano (roteiro_instalador.html):")
    print("   4  o aviso do SmartScreen, que precisa estar dito no release")
    print("   5  a tela de licenca e as duas tarefas oferecidas")
    print("   6  o preparador de ambiente abrindo DEPOIS, em janela visivel")
    print("  11  a primeira execucao numa maquina limpa, sem chave cadastrada")
    print("  13  o modo Teste de API HTTP rodando de verdade")
    print("  15  a desinstalacao perguntando antes de apagar chaves")
    print("=" * 66)
    print()
    return 1 if ERROS else 0


if __name__ == "__main__":
    sys.exit(main())
