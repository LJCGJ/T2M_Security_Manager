# -*- coding: utf-8 -*-
"""
ver_historico.py - Le o historico de execucoes do T2M pela linha de comando.

O aplicativo grava uma linha de JSON por teste executado (historico_execucoes.
jsonl). Este script mostra esse arquivo de forma legivel, sem precisar abrir o
app - util para conferir se o registro esta saindo certo, para achar uma
execucao antiga, e para gerar um resumo quando alguem pedir a trilha de
auditoria de um periodo.

Nada aqui grava nem apaga: e somente leitura.

COMO USAR:
    python ver_historico.py                 # lista as ultimas 20
    python ver_historico.py --todas
    python ver_historico.py --modo Oracle
    python ver_historico.py --com-recusa    # so as que bateram em bloqueio
    python ver_historico.py --erros         # so as que nao chegaram a rodar
    python ver_historico.py --ver 3         # relatorio inteiro da execucao 3
    python ver_historico.py --resumo        # contagem por modo e por resultado
"""

import os
import sys

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "T2M_Security_Manager")
if os.path.isdir(PASTA):
    sys.path.insert(0, PASTA)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import agente_mcp as A
except Exception as e:
    print(f"Nao consegui importar o agente_mcp.py: {type(e).__name__}: {e}")
    sys.exit(1)


# A leitura do arquivo e o veredito de cada execucao vivem no agente_mcp.py: sao
# os mesmos para os tres leitores (esta tela de linha de comando, a tela do
# aplicativo e a suite de testes). Regra de leitura em tres copias derivaria, e a
# copia esquecida seria sempre a que ninguem testa.
def carregar():
    return A.ler_historico()


def rotulo_resultado(r):
    return A.rotulo_resultado(r)


def uma_linha(i, r):
    recusas = sum((r.get("recusas") or {}).values())
    return (f"{i:>4}  {r.get('inicio', '?')[:16]:<16}  "
            f"{r.get('modo', '?'):<8}  "
            f"{(r.get('provedor') or '-'):<7}  "
            f"{r.get('passos_usados', 0):>2}/{r.get('passos_max', 0):<3} "
            f"{r.get('duracao_s', 0):>4}s  "
            f"{('recusa:' + str(recusas)) if recusas else '':<9}  "
            f"{rotulo_resultado(r):<10}  "
            f"{(r.get('alvo') or '')[:34]}")


def cabecalho():
    print(f"{'#':>4}  {'quando':<16}  {'modo':<8}  {'IA':<7}  "
          f"{'passos':<7} {'tempo':>4}  {'bloqueio':<9}  "
          f"{'resultado':<10}  alvo")
    print("-" * 118)


def detalhar(r):
    print("=" * 70)
    for chave, rotulo in (("inicio", "inicio"), ("fim", "fim"),
                          ("duracao_s", "duracao (s)"), ("modo", "modo"),
                          ("alvo", "alvo"), ("somente_leitura", "somente leitura"),
                          ("provedor", "provedor"), ("modelo", "modelo"),
                          ("passos_usados", "passos usados"),
                          ("passos_max", "passos maximos"),
                          ("limite_atingido", "bateu no teto"),
                          ("instrucoes_operador", "instrucoes permanentes"),
                          ("erro", "nao rodou")):
        if r.get(chave) is not None:
            print(f"  {rotulo:<22}: {r.get(chave)}")
    recusas = r.get("recusas") or {}
    if recusas:
        print("  recusas               :")
        for nome, vezes in recusas.items():
            print(f"      {nome} ({vezes}x)")
    print("  objetivo              :")
    for linha in (r.get("objetivo") or "").splitlines() or ["(vazio)"]:
        print(f"      {linha}")
    print("=" * 70)
    print(r.get("relatorio") or "(sem relatorio)")


def resumo(registros):
    por_modo, por_resultado, recusadas = {}, {}, {}
    passos = 0
    for r in registros:
        por_modo[r.get("modo", "?")] = por_modo.get(r.get("modo", "?"), 0) + 1
        rot = rotulo_resultado(r)
        por_resultado[rot] = por_resultado.get(rot, 0) + 1
        passos += r.get("passos_usados", 0) or 0
        for nome, vezes in (r.get("recusas") or {}).items():
            recusadas[nome] = recusadas.get(nome, 0) + vezes
    print(f"\n  execucoes registradas : {len(registros)}")
    if registros:
        print(f"  periodo               : {registros[0].get('inicio', '?')[:16]}"
              f"  ->  {registros[-1].get('inicio', '?')[:16]}")
    print(f"  passos de IA somados  : {passos}")
    print("\n  por modo:")
    for k, v in sorted(por_modo.items(), key=lambda x: -x[1]):
        print(f"      {k:<10} {v}")
    print("\n  por resultado:")
    for k, v in sorted(por_resultado.items(), key=lambda x: -x[1]):
        print(f"      {k:<12} {v}")
    if recusadas:
        print("\n  ferramentas recusadas (somando todas as execucoes):")
        for k, v in sorted(recusadas.items(), key=lambda x: -x[1]):
            print(f"      {k:<26} {v}x")
        print("\n  Recusa repetida na mesma ferramenta costuma dizer que falta")
        print("  uma opcao ligada, ou que o objetivo pede algo que o app nao faz.")


def main():
    print("HISTORICO DE EXECUCOES - T2M")
    print(f"arquivo: {A.ARQUIVO_HISTORICO}")

    registros, ruins = carregar()
    if ruins:
        print(f"AVISO: {ruins} linha(s) ilegivel(is) foram puladas.")
    if not registros:
        print("\nNenhuma execucao registrada ainda. O arquivo e criado na")
        print("primeira vez que um teste roda pelo aplicativo.")
        return 0

    args = [a.lower() for a in sys.argv[1:]]

    if "--ver" in args:
        i = args.index("--ver")
        try:
            n = int(args[i + 1])
        except (IndexError, ValueError):
            print("\nUse: python ver_historico.py --ver <numero da lista>")
            return 1
        if not 1 <= n <= len(registros):
            print(f"\nNumero fora da lista (ha {len(registros)} execucoes).")
            return 1
        detalhar(registros[n - 1])
        return 0

    if "--resumo" in args:
        resumo(registros)
        return 0

    filtrados = list(registros)
    if "--modo" in args:
        i = args.index("--modo")
        alvo = args[i + 1] if i + 1 < len(args) else ""
        filtrados = [r for r in filtrados
                     if (r.get("modo") or "").lower() == alvo]
    if "--com-recusa" in args:
        filtrados = [r for r in filtrados if r.get("recusas")]
    if "--erros" in args:
        filtrados = [r for r in filtrados if r.get("erro")]

    # O numero mostrado e o da posicao no ARQUIVO, nao na lista filtrada: e ele
    # que voce passa para --ver, e mudar de significado conforme o filtro seria
    # a receita para alguem abrir a execucao errada.
    indices = {id(r): n + 1 for n, r in enumerate(registros)}

    mostrar = filtrados if "--todas" in args else filtrados[-20:]
    print(f"\nmostrando {len(mostrar)} de {len(filtrados)} "
          f"(total no arquivo: {len(registros)})\n")
    cabecalho()
    for r in mostrar:
        print(uma_linha(indices[id(r)], r))
    print("\n  --ver <numero> mostra o relatorio inteiro daquela execucao.")
    print("  --resumo mostra a contagem por modo e por resultado.")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
