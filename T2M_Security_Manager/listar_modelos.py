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
import os
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


def _base_url(chave):
    """Endereco do endpoint quando a chave NAO e da OpenAI oficial.

    Espelha _base_url_openai do agente e do gerador. Sem isto, uma chave do
    Groq caia no "else" do roteador e era perguntada ao GOOGLE - o erro que
    chegava a tela era "Chave invalida ou revogada", apontando para o lugar
    errado. Quem visse isso trocaria a chave boa por outra."""
    c = (chave or "").strip()
    if c.startswith("gsk_"):
        return os.environ.get("T2M_ENDPOINT", "") or "https://api.groq.com/openai/v1"
    if c.startswith("sk-"):
        return ""
    return os.environ.get("T2M_ENDPOINT", "")


def listar_openai(chave):
    from openai import OpenAI
    base = _base_url(chave)
    cliente = OpenAI(api_key=chave, base_url=base) if base else OpenAI(api_key=chave)
    modelos = []
    for m in cliente.models.list().data:
        # So os de conversa interessam aqui (ignora embeddings, audio, imagem...)
        # O filtro por prefixo so vale para a OpenAI oficial: num endpoint
        # compativel os nomes sao outros (llama, qwen, mixtral, gemma) e ele
        # devolveria uma lista VAZIA - com a mensagem "nenhum modelo retornado",
        # que sugere problema de conta quando o problema era o filtro.
        oficial = not base
        if _serve_para_conversar(m.id) and (
                not oficial or m.id.startswith(("gpt-", "o1", "o3", "o4", "chatgpt"))):
            modelos.append((m.id, ""))
    modelos.sort(key=lambda x: x[0], reverse=True)
    return modelos


# Modelos que respondem a generateContent mas NAO servem para conversar: os de
# imagem devolvem pixels e nenhum texto, os de audio devolvem som, os de
# embedding devolvem vetores. Todos passavam no filtro "generateContent" e
# apareciam na lista - inclusive o de imagem apelidado "nano banana". Escolher
# um deles para o chat produzia uma resposta vazia e um erro sem explicacao,
# porque o codigo procura .text numa resposta que nunca teve texto.
_NAO_CONVERSAM = ("-image", "image-generation", "-tts", "text-to-speech",
                  "embedding", "aqa", "-vision-preview-0", "imagen", "veo",
                  "-audio", "-live-")


def _serve_para_conversar(nome):
    baixo = nome.lower()
    return not any(marca in baixo for marca in _NAO_CONVERSAM)


def listar_gemini(chave):
    import google.generativeai as genai
    genai.configure(api_key=chave)
    modelos = []
    descartados = 0
    for m in genai.list_models():
        # So os que servem para gerar texto
        if "generateContent" in getattr(m, "supported_generation_methods", []):
            nome = m.name.replace("models/", "")
            if not _serve_para_conversar(nome):
                descartados += 1
                continue
            modelos.append((nome, getattr(m, "display_name", "") or ""))
    if descartados:
        log(f">>> {descartados} modelo(s) de imagem/audio/embedding fora da lista: "
            f"eles nao respondem em texto e quebrariam o chat.")
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

    # Mesma ordem de prefixos do agente e do gerador. Divergir aqui produz o
    # pior tipo de erro: a lista consulta um provedor e a conversa usa outro.
    base = _base_url(chave)
    if chave.startswith("sk-ant-"):
        provedor, funcao = "Claude", listar_anthropic
    elif chave.startswith("sk-") or chave.startswith("gsk_") or base:
        provedor = ("Groq" if "groq" in base
                    else "servidor local" if ("localhost" in base or "127.0.0.1" in base)
                    else "OpenAI" if not base else "endpoint compativel")
        funcao = listar_openai
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
