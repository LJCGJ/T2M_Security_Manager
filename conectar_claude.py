#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""conectar_claude.py - liga o T2M ao Claude Desktop.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
A extensao (.mcpb) instala com dois cliques, mas quem instala e o Claude
Desktop. Se ele nao estiver na maquina, nao existe quem execute a instalacao -
e escrever direto nas pastas internas dele seria adivinhar um formato nao
documentado, que muda sem aviso e quebra silenciosamente.

Entao este script faz a unica coisa honesta possivel: descobre se o Claude
Desktop existe, conecta se existir, e deixa tudo apontado se nao existir. O
atalho fica no menu Iniciar; no dia em que o usuario instalar o Claude, e um
clique.

DUAS FORMAS DE CONECTAR, E POR QUE A PRIMEIRA E MELHOR
------------------------------------------------------
  1. A extensao (.mcpb): o Claude Desktop mostra a tela de permissoes, gera
     sozinho os campos de configuracao (pasta permitida, banco, tempo limite) e
     registra. E o caminho recomendado.

  2. O claude_desktop_config.json: este script escreve a entrada do servidor
     direto no arquivo. Serve para quem prefere linha de comando ou para
     instalacao em varias maquinas. Sempre com copia de seguranca antes, e
     sempre PRESERVANDO os outros servidores ja configurados - apagar a
     configuracao de outro produto seria um estrago que ninguem pediu.

USO
    python conectar_claude.py                     diz o que encontrou
    python conectar_claude.py --pasta "C:\\dados"  conecta usando essa pasta
    python conectar_claude.py --remover           tira a entrada do T2M
"""

import argparse
import json
import os
import platform
import shutil
import sys

NOME_SERVIDOR = "t2m"
AQUI = os.path.dirname(os.path.abspath(__file__))


def pastas_candidatas():
    """Onde o Claude Desktop pode guardar seus dados, em ordem de preferencia.

    Sao VARIAS de proposito, e isso foi MEDIDO, nao suposto. A primeira versao
    procurava so %APPDATA%\\Claude, que e o caminho documentado - e respondeu
    "nao instalado" numa maquina com o Claude Desktop ABERTO na hora. A pasta
    real ali era %LOCALAPPDATA%\\Claude.

    Procurar em varios lugares e a resposta certa para um caminho que nao
    controlamos e que muda entre versoes. O que continua valendo e a regra: se
    nao achar em nenhum, a resposta e "nao encontrei" - nunca um palpite.
    """
    s = platform.system()
    if s == "Windows":
        import glob
        roaming = os.environ.get("APPDATA", "")
        local = os.environ.get("LOCALAPPDATA", "")
        candidatas = []
        # VERSAO DA MICROSOFT STORE (MSIX). Ela roda em conteiner, e o
        # %APPDATA% dela e VIRTUALIZADO para dentro de Packages - o arquivo
        # real fica em
        #   %LOCALAPPDATA%\Packages\Claude_<sufixo>\LocalCache\Roaming\Claude
        # O sufixo do pacote muda por instalacao, por isso a busca e por padrao
        # e nao por nome fixo. Este caso so apareceu porque fomos olhar a
        # maquina de verdade: %LOCALAPPDATA%\Claude EXISTIA ali e nao era onde
        # a configuracao estava. Uma pasta existir nao prova que ela e a certa.
        if local:
            candidatas += sorted(glob.glob(os.path.join(
                local, "Packages", "Claude*", "LocalCache", "Roaming", "Claude")))
            candidatas.append(os.path.join(local, "Claude"))
        if roaming:
            candidatas.append(os.path.join(roaming, "Claude"))
        return [c for c in candidatas if c]
    if s == "Darwin":
        return [os.path.expanduser("~/Library/Application Support/Claude")]
    return [os.path.expanduser("~/.config/Claude")]


def pasta_do_claude():
    """A pasta que existe. Se nenhuma existir, devolve a primeira candidata -
    assim a mensagem consegue dizer ONDE procurou, e nao so que nao achou.

    Preferencia para a que JA TEM o arquivo de configuracao: numa maquina onde
    as duas existem, escrever na errada seria pior do que nao escrever - o T2M
    apareceria como conectado e o Claude nunca leria."""
    candidatas = pastas_candidatas()
    for c in candidatas:
        if os.path.exists(os.path.join(c, "claude_desktop_config.json")):
            return c
    for c in candidatas:
        if os.path.isdir(c):
            return c
    return candidatas[0] if candidatas else ""


def caminho_do_servidor():
    """O servidor MCP fica ao lado do agente, na pasta do programa."""
    for tentativa in (os.path.join(AQUI, "servidor_mcp_t2m.py"),
                      os.path.join(AQUI, "T2M_Security_Manager",
                                   "servidor_mcp_t2m.py")):
        if os.path.exists(tentativa):
            return tentativa
    return ""


def caminho_do_pacote():
    """O .mcpb, se tiver sido instalado junto."""
    for tentativa in (os.path.join(AQUI, "t2m-security-manager-5.0.0.mcpb"),
                      os.path.join(AQUI, "plugin_claude",
                                   "t2m-security-manager-5.0.0.mcpb")):
        if os.path.exists(tentativa):
            return tentativa
    return ""


def ler_config(caminho):
    if not os.path.exists(caminho):
        return {}
    try:
        with open(caminho, encoding="utf-8") as f:
            texto = f.read().strip()
        return json.loads(texto) if texto else {}
    except Exception as e:
        print(f"  [X] O arquivo de configuracao existe mas nao pode ser lido:")
        print(f"      {type(e).__name__}: {e}")
        print(f"      Corrija ou renomeie o arquivo antes de continuar - "
              f"sobrescrever apagaria os outros servidores configurados nele.")
        return None


def conectar(pasta_permitida, dsn=""):
    """pasta_permitida vazia e uma escolha legitima, nao um erro.

    So a camada de ARQUIVOS depende dela. Quem vai testar tela, banco ou API
    nao precisa dar acesso a pasta nenhuma - e exigir isso seria pedir uma
    permissao que nao vai ser usada, que e a forma mais rapida de ensinar
    alguem a clicar em 'permitir' sem ler."""
    destino = pasta_do_claude()
    if not destino:
        print("  [X] Nao foi possivel determinar a pasta do Claude Desktop.")
        return 2

    servidor = caminho_do_servidor()
    if not servidor:
        print("  [X] servidor_mcp_t2m.py nao encontrado ao lado deste script.")
        return 2

    if not os.path.isdir(destino):
        print(f"  [!] O Claude Desktop nao parece estar instalado.")
        print(f"      Procurei em: {destino}")
        print()
        print("      Nada foi alterado - de proposito. Criar configuracao para "
              "um programa que nao existe deixaria arquivo solto na maquina, e "
              "nao ha garantia de que ele seria lido depois.")
        print()
        pacote = caminho_do_pacote()
        if pacote:
            print(f"      Quando instalar o Claude Desktop, abra este arquivo "
                  f"com dois cliques:")
            print(f"        {pacote}")
        print(f"      Ou rode este script de novo - o atalho esta no menu "
              f"Iniciar, em T2M Security Manager.")
        return 1

    config = os.path.join(destino, "claude_desktop_config.json")
    atual = ler_config(config)
    if atual is None:
        return 2

    servidores = atual.get("mcpServers")
    if not isinstance(servidores, dict):
        servidores = {}

    outros = [n for n in servidores if n != NOME_SERVIDOR]
    env = {}
    if pasta_permitida:
        env["T2M_PASTA_PERMITIDA"] = pasta_permitida
    if dsn:
        env["T2M_DSN"] = dsn
    servidores[NOME_SERVIDOR] = {
        "command": sys.executable or "python",
        "args": [servidor],
        "env": env,
    }
    atual["mcpServers"] = servidores

    if os.path.exists(config):
        # Copia de seguranca antes de qualquer escrita. O arquivo pode ter a
        # configuracao de outros produtos, e quem perde isso nao tem como
        # recuperar sem refazer tudo na mao.
        try:
            shutil.copy2(config, config + ".bak")
            print(f"  [OK] Copia de seguranca: {config}.bak")
        except Exception as e:
            print(f"  [X] Nao foi possivel fazer copia de seguranca: {e}")
            return 2

    try:
        os.makedirs(destino, exist_ok=True)
        with open(config, "w", encoding="utf-8") as f:
            json.dump(atual, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  [X] Nao foi possivel gravar a configuracao: {e}")
        return 2

    print(f"  [OK] T2M conectado ao Claude Desktop.")
    print(f"       Arquivo: {config}")
    print(f"       Pasta permitida: {pasta_permitida or 'nenhuma - camada de arquivos desligada'}")
    print(f"       Banco: {'configurado' if dsn else 'nao configurado'}")
    if outros:
        print(f"       Servidores que ja estavam la e foram preservados: "
              f"{', '.join(outros)}")
    print()
    print("       Feche e abra o Claude Desktop para ele carregar o servidor.")
    print("       Para conferir, peca a ele: 'use a ferramenta t2m_situacao'.")
    return 0


def remover():
    destino = pasta_do_claude()
    config = os.path.join(destino, "claude_desktop_config.json") if destino else ""
    if not config or not os.path.exists(config):
        print("  [!] Nao ha configuracao do Claude Desktop para alterar.")
        return 1
    atual = ler_config(config)
    if atual is None:
        return 2
    servidores = atual.get("mcpServers") or {}
    if NOME_SERVIDOR not in servidores:
        print("  [!] O T2M nao estava configurado ali. Nada a remover.")
        return 1
    shutil.copy2(config, config + ".bak")
    servidores.pop(NOME_SERVIDOR, None)
    atual["mcpServers"] = servidores
    with open(config, "w", encoding="utf-8") as f:
        json.dump(atual, f, ensure_ascii=False, indent=2)
    print(f"  [OK] T2M removido. Os outros servidores continuam: "
          f"{', '.join(servidores) or '(nenhum)'}")
    return 0


def situacao():
    destino = pasta_do_claude()
    servidor = caminho_do_servidor()
    pacote = caminho_do_pacote()
    config = os.path.join(destino, "claude_desktop_config.json") if destino else ""
    instalado = bool(destino and os.path.isdir(destino))
    conectado = False
    if config and os.path.exists(config):
        atual = ler_config(config) or {}
        conectado = NOME_SERVIDOR in (atual.get("mcpServers") or {})

    print()
    print("=" * 62)
    print("  T2M no Claude Desktop")
    print("=" * 62)
    print(f"  Claude Desktop instalado : {'sim' if instalado else 'NAO'}")
    print(f"  Pasta encontrada         : {destino or '(desconhecida)'}")
    for c in pastas_candidatas():
        marca = "existe" if os.path.isdir(c) else "nao existe"
        tem_cfg = os.path.exists(os.path.join(c, "claude_desktop_config.json"))
        print(f"    - {c}  [{marca}{', com configuracao' if tem_cfg else ''}]")
    print(f"  Servidor MCP do T2M      : {servidor or 'NAO ENCONTRADO'}")
    print(f"  Extensao (.mcpb)         : {pacote or 'nao instalada ao lado'}")
    print(f"  Ja conectado             : {'sim' if conectado else 'nao'}")
    print("-" * 62)
    if not instalado:
        print("  O Claude Desktop nao esta instalado nesta maquina.")
        print("  Instale-o e rode este script de novo - ou abra o .mcpb com")
        print("  dois cliques, que e o caminho recomendado.")
    elif conectado:
        print("  Tudo pronto. Se acabou de conectar, feche e abra o Claude")
        print("  Desktop, e peca: 'use a ferramenta t2m_situacao'.")
    else:
        print("  Falta conectar. Duas formas:")
        if pacote:
            print(f"    1. Dois cliques em: {pacote}")
        print('    2. python conectar_claude.py --pasta "C:\\sua\\pasta"')
    print("=" * 62)
    print()
    return 0 if conectado else 1


def main():
    p = argparse.ArgumentParser(description="Liga o T2M ao Claude Desktop.")
    p.add_argument("--pasta", default="",
                   help="pasta unica que a automacao podera ler (opcional)")
    p.add_argument("--sem-arquivos", dest="sem_arquivos", action="store_true",
                   help="conecta sem dar acesso a pasta nenhuma")
    p.add_argument("--dsn", default="",
                   help="conexao do banco (opcional)")
    p.add_argument("--remover", action="store_true",
                   help="tira a entrada do T2M da configuracao")
    args = p.parse_args()

    if args.remover:
        return remover()
    if args.sem_arquivos:
        return conectar("", args.dsn.strip())
    if not args.pasta:
        return situacao()

    pasta = args.pasta.strip().strip('"')
    if not os.path.isdir(pasta):
        print(f"  [X] A pasta nao existe: {pasta}")
        return 2
    return conectar(pasta, args.dsn.strip())


if __name__ == "__main__":
    sys.exit(main())
