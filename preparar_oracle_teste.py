# -*- coding: utf-8 -*-
"""
preparar_oracle_teste.py - Cria o usuario e os dados de teste num Oracle
que JA esteja instalado na maquina (sem container, sem Docker).

O QUE FAZ:
    1. Conecta como SYSTEM no seu Oracle local
    2. Cria o usuario T2M_TESTE com tabelas e dados de exemplo
    3. Imprime os dados de conexao para usar no T2M e no testar_mcp_local.py

O QUE NAO FAZ:
    Nao instala o Oracle. Nao toca em nenhum outro usuario ou schema.
    Tudo que ele cria vive dentro do usuario T2M_TESTE e some com
    "DROP USER T2M_TESTE CASCADE".

ANTES DE RODAR:
    Instale o Oracle Database Free (23ai) para Windows:
        https://www.oracle.com/database/free/get-started/
    No fim da instalacao ele pede uma senha - e a senha do SYSTEM,
    que este script vai pedir.

COMO USAR:
    python preparar_oracle_teste.py
    python preparar_oracle_teste.py --remover    # apaga o usuario de teste
"""

import getpass
import sys

SERVICO_PADRAO = "FREEPDB1"      # PDB padrao do Oracle Database Free 23ai
USUARIO_TESTE = "T2M_TESTE"
SENHA_TESTE = "t2m_teste"


def secao(t):
    print()
    print("=" * 64)
    print(f"  {t}")
    print("=" * 64)


def conectar():
    try:
        import oracledb
    except ImportError:
        print("A biblioteca oracledb nao esta instalada. Rode:")
        print("    pip install oracledb")
        return None, None

    print("Dados do SEU Oracle local (o script so usa nesta maquina):")
    host = input("   host [localhost]: ").strip() or "localhost"
    porta = input("   porta [1521]: ").strip() or "1521"
    servico = input(f"   servico [{SERVICO_PADRAO}]: ").strip() or SERVICO_PADRAO
    admin = input("   usuario admin [system]: ").strip() or "system"
    senha = getpass.getpass("   senha do admin (nao aparece): ")

    if not porta.isdigit():
        print(f"\nPorta invalida: {porta!r}. Normalmente e 1521.")
        return None, None
    if not senha:
        print("\nSenha em branco. E a senha que voce definiu no instalador do Oracle.")
        return None, None

    dsn = f"{host}:{porta}/{servico}"
    print(f"\nConectando em {dsn} como {admin} ...")
    try:
        conn = oracledb.connect(user=admin, password=senha, dsn=dsn)
    except Exception as e:
        print(f"Nao consegui conectar: {type(e).__name__}: {e}")
        print("\nDicas:")
        print("  ORA-12541 / TNS:no listener -> o servico do Oracle nao esta")
        print("     rodando. Abra 'Servicos' e inicie OracleServiceFREE e")
        print("     OracleOraDB23Home1TNSListener.")
        print("  ORA-12514 -> o nome do servico esta errado. Rode no cmd:")
        print("     lsnrctl status      (a lista de servicos aparece no fim)")
        print("  ORA-01017 -> usuario ou senha invalidos.")
        return None, None
    print("Conectado.")
    return conn, dsn


def remover(conn):
    secao("Removendo o usuario de teste")
    cur = conn.cursor()
    try:
        cur.execute(f"DROP USER {USUARIO_TESTE} CASCADE")
        conn.commit()
        print(f"  {USUARIO_TESTE} removido.")
    except Exception as e:
        print(f"  nada a remover (ou falhou): {type(e).__name__}: {e}")
    cur.close()


def preparar(conn):
    secao("Criando o usuario e as tabelas de teste")
    cur = conn.cursor()

    comandos = [
        # O DROP no inicio deixa o script repetivel sem dar erro.
        f"BEGIN EXECUTE IMMEDIATE 'DROP USER {USUARIO_TESTE} CASCADE'; "
        f"EXCEPTION WHEN OTHERS THEN NULL; END;",
        f"CREATE USER {USUARIO_TESTE} IDENTIFIED BY {SENHA_TESTE}",
        f"GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {USUARIO_TESTE}",
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
    for c in comandos:
        try:
            cur.execute(c)
            print(f"  ok: {' '.join(c.split())[:60]}")
        except Exception as e:
            print(f"  AVISO em '{' '.join(c.split())[:45]}...': "
                  f"{type(e).__name__}: {e}")

    try:
        cur.executemany(
            f"INSERT INTO {USUARIO_TESTE}.CLIENTES (ID,NOME,EMAIL,CPF) "
            f"VALUES (:1,:2,:3,:4)",
            [(i, f"Cliente {i}", f"cliente{i}@exemplo.com", f"000.000.000-{i:02d}")
             for i in range(1, 51)])
        cur.executemany(
            f"INSERT INTO {USUARIO_TESTE}.PEDIDOS (ID,CLIENTE_ID,TOTAL,STATUS) "
            f"VALUES (:1,:2,:3,:4)",
            [(i, (i % 50) + 1, 100.0 + i,
              ["NOVO", "PAGO", "ENVIADO", "CANCELADO"][i % 4])
             for i in range(1, 201)])
        cur.executemany(
            f"INSERT INTO {USUARIO_TESTE}.LOG_ACESSO (ID,USUARIO,ACAO,SUCESSO) "
            f"VALUES (:1,:2,:3,:4)",
            [(i, f"user{i % 10}", ["LOGIN", "LOGOUT", "SENHA_ERRADA"][i % 3],
              1 if i % 3 != 2 else 0)
             for i in range(1, 301)])
        conn.commit()
        print("\n  50 clientes, 200 pedidos e 300 registros de acesso criados.")
    except Exception as e:
        print(f"\n  falha ao inserir os dados: {type(e).__name__}: {e}")
        cur.close()
        return False

    cur.close()
    return True


def main():
    print("ORACLE LOCAL PARA TESTES DO T2M - preparacao do schema")
    print("(usa um Oracle ja instalado; nao instala nada)\n")

    conn, dsn = conectar()
    if not conn:
        return

    try:
        if "--remover" in sys.argv:
            remover(conn)
            return
        if not preparar(conn):
            return

        host_porta_servico = dsn
        secao("PRONTO - use estes dados no T2M e no testar_mcp_local.py")
        print(f"  dsn     : {host_porta_servico}")
        print(f"  usuario : {USUARIO_TESTE}")
        print(f"  senha   : {SENHA_TESTE}")
        print()
        print("  Tabelas: CLIENTES, PEDIDOS, LOG_ACESSO")
        print()
        print("  Proximo passo:")
        print("     python testar_mcp_local.py")
        print()
        print("  Para apagar o usuario de teste depois:")
        print(f"     python {sys.argv[0]} --remover")
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
