# -*- coding: utf-8 -*-
"""
servidor_http_mcp.py - Servidor MCP do T2M para testes de API HTTP.

POR QUE UM SERVIDOR PROPRIO, E NAO UM PACOTE DE TERCEIROS:

  - Os servidores HTTP MCP publicos fixam URL base e autenticacao na
    INICIALIZACAO (variaveis de ambiente). Aqui a IA precisa trocar de endpoint,
    metodo e cabecalhos no meio do teste - uma base fixa por sessao inviabiliza
    o modo API.
  - Mantem sob nosso controle o timeout definido na tela de Configuracoes, o
    truncamento do corpo da resposta e o mascaramento de credenciais.
  - Nao acrescenta pacote npm com @latest a cadeia de suprimentos de uma
    ferramenta de seguranca, nem passa a exigir Node.js para o modo API.

O trabalho pesado de HTTP (TLS, redirecionamentos, pool de conexoes, encoding,
chunked transfer, proxy) continua sendo do `requests`. Este arquivo e apenas a
cola entre o protocolo MCP e ele - a mesma cola que um pacote de terceiros
escreveria, com as decisoes sendo nossas.

CONTRATO: falado por stdio; quem sobe este processo e o agente_mcp.py.
  Variavel de ambiente:
    T2M_TIMEOUT - segundos por requisicao (vem da tela de Configuracoes)
"""

import json
import os

from mcp.server.fastmcp import FastMCP

# Timeout por requisicao. Vem do agente_mcp.py, que por sua vez le a tela de
# Configuracoes; o padrao so vale se o processo for iniciado a mao.
try:
    TIMEOUT = max(5, min(3600, int(os.environ.get("T2M_TIMEOUT", "120"))))
except Exception:
    TIMEOUT = 120

# Orcamento total (em caracteres) do JSON devolvido a IA por chamada.
LIMITE_RESPOSTA = 6000

app = FastMCP("t2m-http")


def _como_dict(valor):
    """Aceita dicionario OU texto JSON e devolve dicionario (ou None).

    Os modelos mandam ora um, ora outro. E o Gemini so consegue mandar TEXTO:
    a API dele nao aceita objeto de forma livre num schema de ferramenta, entao
    a conversao de schema declara estes campos como string."""
    if valor is None:
        return None
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            d = json.loads(valor)
            return d if isinstance(d, dict) else None
        except Exception:
            return None
    return None


@app.tool()
def fazer_requisicao_http(metodo: str, url: str,
                          headers: str | dict | None = None,
                          body: str | dict | list | None = None) -> str:
    """Executa uma requisicao HTTP real e devolve status, cabecalhos, corpo e tempo.

    Use para testar endpoints: ajuste metodo, URL, cabecalhos e corpo conforme
    o objetivo do teste, e analise a resposta.

    metodo:  GET, POST, PUT, DELETE, PATCH...
    url:     URL completa do endpoint (pode mudar a cada chamada)
    headers: cabecalhos HTTP (objeto ou JSON em texto), incluindo Authorization
    body:    corpo da requisicao (objeto, JSON em texto, ou texto puro)
    """
    import requests

    try:
        m = (metodo or "GET").upper()

        # body pode chegar como texto JSON ou como texto puro.
        dados = None
        json_data = None
        if body:
            if isinstance(body, (dict, list)):
                json_data = body
            else:
                try:
                    json_data = json.loads(body)
                except Exception:
                    dados = body

        resp = requests.request(m, url, headers=_como_dict(headers) or {},
                                json=json_data, data=dados, timeout=TIMEOUT)

        r = {
            "status_code": resp.status_code,
            "ok": resp.ok,
            "headers": dict(resp.headers),
            "url_final": resp.url,
            "tempo_ms": int(resp.elapsed.total_seconds() * 1000),
        }

        # Trunca SOMENTE o corpo, respeitando o espaco que sobra depois dos
        # metadados. Cortar o JSON ja serializado - como era feito antes -
        # partia a resposta no meio de uma string, e o modelo relatava
        # "a API devolveu JSON malformado": um falso positivo num teste de API.
        corpo = resp.text or ""
        folga = LIMITE_RESPOSTA - len(json.dumps(r, ensure_ascii=False))
        if folga < 500:
            folga = 500
        if len(corpo) > folga:
            r["body"] = corpo[:folga]
            r["body_truncado"] = True
            r["body_tamanho_real"] = len(corpo)
            r["aviso"] = ("Corpo cortado para caber no limite de contexto. NAO conclua "
                          "que a resposta e invalida ou incompleta por causa do corte.")
        else:
            r["body"] = corpo

        return json.dumps(r, ensure_ascii=False)

    except requests.exceptions.Timeout:
        return json.dumps({
            "erro": f"A requisicao nao respondeu em {TIMEOUT}s "
                    f"(limite definido em Configuracoes)."
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"erro": f"{type(e).__name__}: {e}"}, ensure_ascii=False)


if __name__ == "__main__":
    app.run()
