# -*- coding: utf-8 -*-
"""
rodar_agente.py - Roda o agente do T2M pela linha de comando, com IA de verdade.

E o MESMO caminho que o aplicativo usa: sobe o agente_mcp.py como processo
separado e conversa por stdin, exatamente como o C++ faz. A diferenca e que
aqui voce ve o progresso cru, sem a janela no meio - o que torna o diagnostico
muito mais direto quando algo da errado.

Serve para os cinco modos: Tela, Banco, MongoDB, Oracle e API.

ATENCAO: este roda com IA de verdade e CONSOME CREDITO da sua chave. Os outros
scripts (testar_tela, testar_bancos, testar_regressao) nao consomem nada - use
aqueles primeiro para conferir a encanacao, e este so quando quiser ver o
comportamento do modelo.

A chave e digitada na hora e nao fica gravada em lugar nenhum. Ela vai pelo
stdin do processo filho, nunca por argumento de linha de comando, que apareceria
na lista de processos da maquina.

COMO USAR:
    python rodar_agente.py           # pergunta o modo
    python rodar_agente.py tela
    python rodar_agente.py banco
    python rodar_agente.py mongo
    python rodar_agente.py oracle
    python rodar_agente.py api
"""

import getpass
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
AGENTE = os.path.join(RAIZ, "T2M_Security_Manager", "agente_mcp.py")
if not os.path.exists(AGENTE):
    AGENTE = os.path.join(RAIZ, "agente_mcp.py")

MODOS = ("tela", "banco", "mongo", "oracle", "api")


def secao(t):
    print()
    print("=" * 68)
    print(f"  {t}")
    print("=" * 68)


def perguntar(rotulo, padrao=""):
    v = input(f"   {rotulo}{f' [{padrao}]' if padrao else ''}: ").strip()
    return v or padrao


def montar_linha2(modo):
    """Monta a segunda linha do stdin, no formato que o agente espera - o mesmo
    que o C++ monta. Erro aqui e erro no app inteiro, entao vale conferir."""
    if modo == "tela":
        return perguntar("URL alvo", "https://example.com")

    if modo == "banco":
        print("   Cole a string de conexao inteira, ou monte pelos campos.")
        print("   Ex.: sqlite:///C:/temp/teste.db")
        print("        postgres://usuario:senha@host:5432/banco?sslmode=require")
        dsn = perguntar("string de conexao")
        if not dsn:
            return None
        ro = perguntar("somente leitura? (s/n)", "s").lower().startswith("s")
        return f"--DB--{dsn}|{'1' if ro else '0'}"

    if modo == "mongo":
        cs = perguntar("connection string (mongodb+srv://... ou mongodb://...)")
        if not cs:
            return None
        ro = perguntar("somente leitura? (s/n)", "s").lower().startswith("s")
        return f"--MONGO--{cs}|{'1' if ro else '0'}"

    if modo == "oracle":
        print("   No host da para colar o nome do servidor, o apelido do")
        print("   tnsnames (se usar wallet) ou uma string tcps:// inteira.")
        host = perguntar("host / apelido / string", "localhost")
        info = {"host": host}
        wallet = perguntar("wallet .zip ou pasta (Enter se nao usa)")
        if wallet:
            info["wallet"] = wallet
            sw = getpass.getpass("   senha da wallet (Enter se nao tem): ")
            if sw:
                info["wallet_senha"] = sw
        # Com wallet e host que nao e string pronta, porta e servico ficam de
        # fora: o apelido do tnsnames ja carrega os dois. E a mesma regra do C++.
        elif "/" not in host and not host.startswith("("):
            info["porta"] = perguntar("porta", "1521")
            info["servico"] = perguntar("servico", "FREEPDB1")
        info["usuario"] = perguntar("usuario")
        info["senha"] = getpass.getpass("   senha (nao aparece): ")
        info["somente_leitura"] = "1" if perguntar(
            "somente leitura? (s/n)", "s").lower().startswith("s") else "0"
        return "--ORACLE--" + json.dumps(info, ensure_ascii=False)

    if modo == "api":
        req = {
            "metodo": perguntar("metodo", "GET"),
            "url": perguntar("url", "https://httpbin.org/get"),
            "headers": {},
            "body": "",
        }
        cab = perguntar("headers (Nome: valor, separados por ';', Enter para nenhum)")
        for parte in cab.split(";"):
            if ":" in parte:
                k, v = parte.split(":", 1)
                req["headers"][k.strip()] = v.strip()
        req["body"] = perguntar("body (Enter para vazio)")
        return "--API--" + json.dumps(req, ensure_ascii=False)

    return None


def main():
    print("RODAR O AGENTE DO T2M PELA LINHA DE COMANDO")
    print("(usa IA de verdade e CONSOME CREDITO da sua chave)")
    print(f"\nagente: {AGENTE}")
    if not os.path.exists(AGENTE):
        print("Nao encontrei o agente_mcp.py. Rode este script de dentro do repositorio.")
        return 1

    modo = (sys.argv[1].lower() if len(sys.argv) > 1 else "").strip()
    if modo not in MODOS:
        print(f"\nModos: {', '.join(MODOS)}")
        modo = perguntar("modo", "tela").lower()
        if modo not in MODOS:
            print(f"Modo desconhecido: {modo!r}")
            return 1

    secao(f"Modo {modo}")
    linha2 = montar_linha2(modo)
    if linha2 is None:
        print("   Faltou informacao obrigatoria. Nada foi executado.")
        return 1

    print()
    objetivo = perguntar("objetivo do teste (o que a IA deve fazer)")
    if not objetivo:
        print("   Sem objetivo nao ha o que executar.")
        return 1

    print()
    print("   A chave nao aparece na tela e nao fica gravada.")
    chave = getpass.getpass("   chave de API: ")
    if not chave:
        print("   Sem chave nao da para rodar. Use os scripts testar_* para")
        print("   conferir a encanacao sem consumir credito.")
        return 1

    # Mesma ordem que o C++ escreve: chave, linha de modo, objetivo.
    entrada = f"{chave}\n{linha2}\n{objetivo}\n"

    secao("Executando - o progresso vem do proprio agente")
    print("   (stderr = progresso; stdout = resposta final entre CHAT_MSG_*)")
    print()

    try:
        p = subprocess.Popen(
            [sys.executable, "-u", AGENTE],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None,
            text=True, encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"   Nao consegui iniciar o agente: {type(e).__name__}: {e}")
        return 1

    saida, _ = p.communicate(entrada)
    del chave, entrada

    secao("RESPOSTA FINAL")
    dentro = False
    achou = False
    for linha in (saida or "").splitlines():
        if linha.strip() == "CHAT_MSG_INICIO":
            dentro = True
            achou = True
            continue
        if linha.strip() == "CHAT_MSG_FIM":
            dentro = False
            continue
        if dentro:
            print(linha)
    if not achou:
        print("(o agente nao devolveu resposta entre CHAT_MSG_INICIO/FIM)")
        print("Saida crua:")
        print((saida or "(vazia)")[:3000])

    secao("FIM")
    print("   O progresso acima veio direto do agente. Se algo falhou, a")
    print("   explicacao esta nas linhas que comecam com '>>>'.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
