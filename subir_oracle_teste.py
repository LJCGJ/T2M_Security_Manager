# -*- coding: utf-8 -*-
"""
subir_oracle_teste.py - Sobe um Oracle local em container, so para testes.

O QUE FAZ:
    1. Sobe a imagem oficial gratuita da Oracle (Database Free) num container
    2. Espera o banco ficar pronto (a primeira vez leva alguns minutos)
    3. Cria um usuario de teste com tabelas e dados de exemplo
    4. Imprime os dados de conexao para usar no T2M

O QUE NAO FAZ:
    Nao toca em nenhum Oracle que voce ja tenha. O container e isolado e
    descartavel - para remover: docker rm -f oracle-t2m

REQUISITOS:
    Docker Desktop instalado e rodando.
    A imagem tem cerca de 2,5 GB; a primeira execucao demora.

COMO USAR:
    python subir_oracle_teste.py           # sobe e prepara
    python subir_oracle_teste.py --remover # apaga o container
"""

import subprocess
import sys
import time

NOME = "oracle-t2m"
IMAGEM = "container-registry.oracle.com/database/free:latest"
SENHA_ADMIN = "T2mTeste_2026"
PORTA = 1521
SERVICO = "FREEPDB1"          # o PDB padrao da edicao Free
USUARIO_TESTE = "T2M_TESTE"
SENHA_TESTE = "t2m_teste"


def secao(t):
    print()
    print("=" * 64)
    print(f"  {t}")
    print("=" * 64)


def rodar(cmd, timeout=None, mostrar=False):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, errors="replace")
        if mostrar and (p.stdout or p.stderr):
            print((p.stdout or p.stderr).strip()[:400])
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return -1, "(docker nao encontrado)"
    except subprocess.TimeoutExpired:
        return -2, "(tempo esgotado)"
    except Exception as e:
        return -3, f"({type(e).__name__}: {e})"


def docker_ok():
    cod, saida = rodar(["docker", "version", "--format", "{{.Server.Version}}"], 30)
    if cod != 0:
        print("Docker nao esta disponivel ou nao esta rodando.")
        print(f"  detalhe: {saida.strip()[:200]}")
        print("\nOpcoes:")
        print("  1. Instale o Docker Desktop e deixe-o aberto:")
        print("     winget install --id Docker.DockerDesktop")
        print("  2. Ou instale o Oracle Database Free direto no Windows:")
        print("     https://www.oracle.com/database/free/download/")
        return False
    print(f"Docker: servidor versao {saida.strip()}")
    return True


def porta_livre(p):
    import socket
    with socket.socket() as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", p)) != 0


def remover():
    secao("Removendo o container de teste")
    cod, saida = rodar(["docker", "rm", "-f", NOME], 60, mostrar=True)
    print("Removido." if cod == 0 else "Nada a remover (ou falhou).")


def estado_container():
    cod, saida = rodar(["docker", "ps", "-a", "--filter", f"name=^{NOME}$",
                        "--format", "{{.State}}"], 30)
    return saida.strip() if cod == 0 else ""


def subir():
    global PORTA
    if not docker_ok():
        return None

    estado = estado_container()
    if estado == "running":
        print(f"\nO container '{NOME}' ja esta rodando.")
    elif estado:
        print(f"\nO container '{NOME}' existe (estado: {estado}). Reiniciando...")
        rodar(["docker", "start", NOME], 120, mostrar=True)
    else:
        if not porta_livre(PORTA):
            print(f"\nA porta {PORTA} ja esta ocupada (outro Oracle?). Usando 1522.")
            PORTA = 1522
            if not porta_livre(PORTA):
                print("A 1522 tambem esta ocupada. Libere uma delas e tente de novo.")
                return None

        secao("Baixando e subindo o Oracle Database Free")
        print(f"Imagem: {IMAGEM}")
        print("A primeira vez baixa cerca de 2,5 GB e leva varios minutos.")
        print("Pode acompanhar em outra janela com: docker logs -f " + NOME)
        print()
        cod, saida = rodar([
            "docker", "run", "-d", "--name", NOME,
            "-p", f"{PORTA}:1521",
            "-e", f"ORACLE_PWD={SENHA_ADMIN}",
            IMAGEM], timeout=3600, mostrar=True)
        if cod != 0:
            print("Falha ao subir o container.")
            return None

    secao("Esperando o banco ficar pronto")
    print("(a inicializacao do Oracle leva alguns minutos na primeira vez)")
    inicio = time.time()
    limite = 900          # 15 minutos
    while time.time() - inicio < limite:
        cod, logs = rodar(["docker", "logs", "--tail", "20", NOME], 30)
        if "DATABASE IS READY TO USE" in logs.upper():
            print(f"\nBanco pronto em {int(time.time() - inicio)}s.")
            return PORTA
        cod2, estado = rodar(["docker", "inspect", "-f", "{{.State.Running}}", NOME], 30)
        if estado.strip() != "true":
            print("\nO container parou. Ultimas linhas do log:")
            print(logs[-800:])
            return None
        print(f"  ... {int(time.time() - inicio)}s", end="\r", flush=True)
        time.sleep(10)
    print("\nTempo esgotado esperando o banco. Veja: docker logs " + NOME)
    return None


def preparar_schema(porta):
    secao("Criando o usuario e os dados de teste")
    try:
        import oracledb
    except ImportError:
        print("A biblioteca oracledb nao esta instalada.")
        print("  pip install oracledb")
        return False

    dsn = f"localhost:{porta}/{SERVICO}"
    try:
        conn = oracledb.connect(user="system", password=SENHA_ADMIN, dsn=dsn)
    except Exception as e:
        print(f"Nao consegui conectar como system: {type(e).__name__}: {e}")
        return False

    comandos = [
        # Usuario de teste. O DROP no inicio deixa o script repetivel.
        f"BEGIN EXECUTE IMMEDIATE 'DROP USER {USUARIO_TESTE} CASCADE'; "
        f"EXCEPTION WHEN OTHERS THEN NULL; END;",
        f"CREATE USER {USUARIO_TESTE} IDENTIFIED BY {SENHA_TESTE}",
        f"GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {USUARIO_TESTE}",
        # Tabelas com cara de sistema real, para os testes fazerem sentido
        f"""CREATE TABLE {USUARIO_TESTE}.CLIENTES (
              ID NUMBER PRIMARY KEY, NOME VARCHAR2(100), EMAIL VARCHAR2(120),
              CPF VARCHAR2(14), CRIADO_EM DATE DEFAULT SYSDATE)""",
        f"""CREATE TABLE {USUARIO_TESTE}.PEDIDOS (
              ID NUMBER PRIMARY KEY, CLIENTE_ID NUMBER, TOTAL NUMBER(10,2),
              STATUS VARCHAR2(20), DATA_PEDIDO DATE DEFAULT SYSDATE)""",
        f"""CREATE TABLE {USUARIO_TESTE}.LOG_ACESSO (
              ID NUMBER PRIMARY KEY, USUARIO VARCHAR2(50), ACAO VARCHAR2(50),
              SUCESSO NUMBER(1), QUANDO DATE DEFAULT SYSDATE)""",
    ]
    cur = conn.cursor()
    for c in comandos:
        try:
            cur.execute(c)
        except Exception as e:
            print(f"  aviso em '{c[:45]}...': {type(e).__name__}: {e}")

    # Dados de exemplo
    try:
        cur.executemany(
            f"INSERT INTO {USUARIO_TESTE}.CLIENTES (ID,NOME,EMAIL,CPF) VALUES (:1,:2,:3,:4)",
            [(i, f"Cliente {i}", f"cliente{i}@exemplo.com", f"000.000.000-{i:02d}")
             for i in range(1, 51)])
        cur.executemany(
            f"INSERT INTO {USUARIO_TESTE}.PEDIDOS (ID,CLIENTE_ID,TOTAL,STATUS) VALUES (:1,:2,:3,:4)",
            [(i, (i % 50) + 1, 100.0 + i, ["NOVO", "PAGO", "ENVIADO", "CANCELADO"][i % 4])
             for i in range(1, 201)])
        cur.executemany(
            f"INSERT INTO {USUARIO_TESTE}.LOG_ACESSO (ID,USUARIO,ACAO,SUCESSO) VALUES (:1,:2,:3,:4)",
            [(i, f"user{i % 10}", ["LOGIN", "LOGOUT", "SENHA_ERRADA"][i % 3], i % 3 != 2)
             for i in range(1, 301)])
        conn.commit()
        print("  50 clientes, 200 pedidos e 300 registros de acesso criados.")
    except Exception as e:
        print(f"  falha ao inserir dados: {type(e).__name__}: {e}")

    cur.close()
    conn.close()
    return True


def main():
    if "--remover" in sys.argv:
        remover()
        return

    print("ORACLE LOCAL PARA TESTES - T2M")
    print("Container isolado e descartavel; nao afeta outros bancos.")

    porta = subir()
    if not porta:
        return
    if not preparar_schema(porta):
        return

    secao("PRONTO - use estes dados no T2M e no teste")
    print("  host    : localhost")
    print(f"  porta   : {porta}")
    print(f"  servico : {SERVICO}")
    print(f"  usuario : {USUARIO_TESTE}")
    print(f"  senha   : {SENHA_TESTE}")
    print()
    print("  (admin, se precisar: system / " + SENHA_ADMIN + ")")
    print()
    print("Tabelas: CLIENTES, PEDIDOS, LOG_ACESSO")
    print()
    print("Para remover tudo depois:")
    print(f"  python {sys.argv[0]} --remover")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
