# -*- coding: utf-8 -*-
"""
T2M - Lista os modelos disponiveis AGORA, consultando o provedor.

Por que isso existe: modelos sao lancados e aposentados com frequencia. Deixar
a lista fixa no codigo significa que, a cada mudanca, o programa precisaria ser
atualizado - e usar um modelo aposentado faz as chamadas falharem. Perguntando
ao provedor, a lista esta sempre correta.

CONTRATO (igual aos outros scripts):
    stdin  : chave de API (uma linha)
    stdout : MODELOS_INICIO / um modelo por linha / MODELOS_FIM
    stderr : mensagens de progresso e erro
"""
import sys


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def listar_anthropic(chave):
    from anthropic import Anthropic
    cliente = Anthropic(api_key=chave)
    # A API devolve os mais recentes primeiro
    resposta = cliente.models.list(limit=100)
    modelos = []
    for m in resposta.data:
        nome = getattr(m, "display_name", "") or ""
        modelos.append((m.id, nome))
    return modelos


def listar_openai(chave):
    from openai import OpenAI
    cliente = OpenAI(api_key=chave)
    modelos = []
    for m in cliente.models.list().data:
        # So os de conversa interessam aqui (ignora embeddings, audio, imagem...)
        if m.id.startswith(("gpt-", "o1", "o3", "o4", "chatgpt")):
            modelos.append((m.id, ""))
    modelos.sort(key=lambda x: x[0], reverse=True)
    return modelos


def listar_gemini(chave):
    import google.generativeai as genai
    genai.configure(api_key=chave)
    modelos = []
    for m in genai.list_models():
        # So os que servem para gerar texto
        if "generateContent" in getattr(m, "supported_generation_methods", []):
            nome = m.name.replace("models/", "")
            modelos.append((nome, getattr(m, "display_name", "") or ""))
    modelos.sort(key=lambda x: x[0], reverse=True)
    return modelos


def main():
    try:
        chave = (sys.stdin.read() or "").strip().split("\n")[0].strip()
    except Exception:
        chave = ""

    if not chave:
        log("Nenhuma chave informada.")
        return 1

    if chave.startswith("sk-ant-"):
        provedor, funcao = "Claude", listar_anthropic
    elif chave.startswith("sk-"):
        provedor, funcao = "OpenAI", listar_openai
    else:
        provedor, funcao = "Gemini", listar_gemini

    log(f">>> Consultando os modelos disponiveis na {provedor}...")

    try:
        modelos = funcao(chave)
    except ImportError as e:
        log(f"Biblioteca ausente para {provedor}: {e}")
        return 1
    except Exception as e:
        texto = str(e)
        if "not valid" in texto or "authentication" in texto.lower() \
                or "API_KEY_INVALID" in texto:
            log("Chave invalida ou revogada.")
        else:
            log(f"Falha ao consultar: {type(e).__name__}: {texto[:200]}")
        return 1

    if not modelos:
        log("Nenhum modelo retornado pelo provedor.")
        return 1

    log(f">>> {len(modelos)} modelos disponiveis.")
    print("MODELOS_INICIO")
    for ident, descricao in modelos:
        print(f"{ident}|{descricao}")
    print("MODELOS_FIM")
    return 0


if __name__ == "__main__":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
