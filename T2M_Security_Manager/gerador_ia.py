# -*- coding: utf-8 -*-
"""
T2M Copilot - Motor de IA (roteador multi-provedor)

MUDANCA IMPORTANTE DE SEGURANCA:
    A entrada agora chega por STDIN em JSON, e nao mais por sys.argv.
    Isso resolve tres problemas da versao anterior:
      1) A API key nao aparece mais na lista de processos (Gerenciador de Tarefas).
      2) Prompts/conversas longas nao esbarram no limite da linha de comando (~32KB).
      3) Aspas e caracteres especiais no prompt nao quebram mais o parsing.

    Contrato de entrada (stdin, UTF-8):
        {"api_key": "...", "prompt": "...", "url": "..."}

    Contrato de saida (stdout):
        CHAT_MSG_INICIO
        <resposta>
        CHAT_MSG_FIM
"""

import sys
import os
import json
import subprocess


# ==============================================================================
# --- 1. AUTO-INSTALACAO SILENCIOSA DE DEPENDENCIAS ---
# ==============================================================================
def garantir_bibliotecas():
    bibliotecas_faltando = []
    checagem = {
        'google-generativeai': 'google.generativeai',
        'requests': 'requests',
        'openai': 'openai',
        'beautifulsoup4': 'bs4',
        'anthropic': 'anthropic',
    }
    for pacote, modulo in checagem.items():
        try:
            __import__(modulo)
        except ImportError:
            bibliotecas_faltando.append(pacote)

    for lib in bibliotecas_faltando:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", lib, "--quiet"]
            )
        except Exception as e:
            # Nao derruba o programa; apenas registra. A rota correspondente
            # falhara de forma controlada se a lib for realmente necessaria.
            print(f"--- AVISO: falha ao instalar {lib}: {e}", file=sys.stderr)


# ==============================================================================
# --- 2. LIMPEZA DE JSON SCHEMA (base para futuras 'tools' MCP-like) ---
# ==============================================================================
def clean_schema(schema):
    """Remove chaves de JSON Schema que a API do Gemini nao aceita."""
    if not isinstance(schema, dict):
        return schema
    cleaned = {}
    for key, value in schema.items():
        if key in ("$schema", "additionalProperties", "additional_properties"):
            continue
        if isinstance(value, dict):
            cleaned[key] = clean_schema(value)
        elif isinstance(value, list):
            cleaned[key] = [
                clean_schema(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


# ==============================================================================
# --- 3. SCANNER DE INTERFACE (DOM) ---
#     Observacao honesta: isto NAO e o protocolo MCP. E scraping do HTML da
#     URL alvo para mapear inputs/botoes/forms e dar contexto real ao modelo.
#     Para QA/automacao de tela isso e uma abordagem legitima e util.
# ==============================================================================
def extrair_contexto_dom(url):
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {'User-Agent': 'Mozilla/5.0 (T2M-QA-Scanner)'}
        req = requests.get(url, headers=headers, timeout=8)
        req.raise_for_status()
        soup = BeautifulSoup(req.text, 'html.parser')

        inputs = soup.find_all('input')
        botoes = soup.find_all('button')
        forms = soup.find_all('form')
        links = soup.find_all('a')

        linhas = [f"=== CONTEXTO EXTRAIDO DA URL ({url}) ==="]
        linhas.append(f"Total de Formularios: {len(forms)}")
        linhas.append(f"Total de Links: {len(links)}")
        linhas.append("Inputs encontrados:")
        for i in inputs:
            linhas.append(
                f" - Tipo: {i.get('type', 'N/A')} | "
                f"ID: {i.get('id', 'N/A')} | "
                f"Name: {i.get('name', 'N/A')} | "
                f"Placeholder: {i.get('placeholder', 'N/A')}"
            )
        linhas.append("Botoes encontrados:")
        for b in botoes:
            texto = (b.get_text() or "").strip()[:60]
            linhas.append(f" - Texto: {texto} | ID: {b.get('id', 'N/A')}")

        linhas.append("=======================================")
        return "\n".join(linhas) + "\n"
    except Exception as e:
        return (
            "--- AVISO: nao foi possivel ler a URL profundamente. "
            f"Use nomes genericos de elementos. (Erro: {e})\n"
        )


# ==============================================================================
# --- 4. LEITURA DA ENTRADA (STDIN JSON) ---
# ==============================================================================
def ler_entrada():
    """Le o payload JSON enviado pelo C++ via stdin."""
    raw = sys.stdin.read()
    if not raw or not raw.strip():
        raise ValueError("Nenhum dado recebido via stdin.")
    dados = json.loads(raw)
    return (
        (dados.get("api_key") or "").strip(),
        dados.get("prompt") or "",
        dados.get("url") or "",
    )


# ==============================================================================
# --- 5. FUNCAO PRINCIPAL E ROTEAMENTO MULTI-IA ---
# ==============================================================================
def main():
    try:
        garantir_bibliotecas()

        try:
            api_key, prompt_usuario, url_alvo = ler_entrada()
        except Exception as e:
            print(f"ERRO PYTHON: entrada invalida ({e}).")
            return

        if not api_key:
            print("ERRO PYTHON: API Key nao informada.")
            return

        arquivo_memoria = "memoria_chat.json"
        memoria = []

        # --- NOVO CHAT + CONTROLE DO SCANNER DE INTERFACE ---
        if prompt_usuario.startswith("--INICIAR_NOVO_CHAT--"):
            usar_scanner = "MCP_OFF" not in prompt_usuario

            if usar_scanner and url_alvo:
                mapa = extrair_contexto_dom(url_alvo)
                status_visual = ("INFORME AO USUARIO: o Scanner de Interface esta "
                                 "ATIVO e a URL foi mapeada com sucesso.")
            else:
                mapa = "--- SCANNER DE INTERFACE DESATIVADO ---"
                status_visual = ("INFORME AO USUARIO: o Scanner de Interface esta "
                                 "DESLIGADO a pedido do operador.")

            prompt_mestre = f"""
Aja como um Arquiteto Senior de Automacao, Qualidade (QA) e Engenharia de Seguranca.
A missao e auxiliar na estruturacao de testes avancados, com capacidade de gerar
scripts em Robot Framework (incluindo DatabaseLibrary e conexoes), Python, consultas
SQL complexas e automacoes mobile/web.

{mapa}

INSTRUCOES OBRIGATORIAS:
1. Faca uma apresentacao profissional e amigavel.
2. {status_visual}
3. Coloque seu conhecimento avancado de automacao a disposicao e pergunte qual e o
   desafio tecnico atual.
Atencao: NAO gere codigo nesta primeira resposta, apenas a apresentacao inicial.
Sempre que gerar codigo, use blocos ```linguagem ... ``` para o sistema reconhecer.
"""
            memoria = [{"role": "user", "content": prompt_mestre}]
        else:
            if os.path.exists(arquivo_memoria):
                try:
                    with open(arquivo_memoria, 'r', encoding='utf-8') as f:
                        memoria = json.load(f)
                except Exception:
                    memoria = []
            memoria.append({"role": "user", "content": prompt_usuario})

        resposta_ia = ""
        sistema = ("Aja como um Arquiteto de Automacao e Seguranca. Se houver codigo, "
                   "coloque-o sempre dentro de blocos ```linguagem ``` para o sistema "
                   "reconhecer.")

        # Roteador por provedor. Ordem importa: prefixos mais especificos primeiro.
        # Gemini fica como padrao porque o Google mudou o formato da chave em 2026
        # (AIza -> AQ.) e pode mudar de novo; validar so "AIza" quebraria com as
        # chaves novas. Chaves Gemini validas hoje: AIza..., AQ...., AQ_...

        # --- ROTA ANTHROPIC (CLAUDE) ---
        if api_key.startswith("sk-ant-"):
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            # Dica: voce pode trocar por um modelo mais novo quando quiser.
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2048,
                system=sistema,
                messages=memoria,
            )
            resposta_ia = response.content[0].text.strip()

        # --- ROTA OPENAI (CHATGPT) ---
        elif api_key.startswith("sk-"):
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": sistema}] + memoria,
            )
            resposta_ia = response.choices[0].message.content.strip()

        # --- ROTA GOOGLE GEMINI (padrao; aceita AIza, AQ. e formatos futuros) ---
        else:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            mensagens = [
                {"role": "user" if m["role"] == "user" else "model",
                 "parts": [m["content"]]}
                for m in memoria
            ]
            modelos = ['gemini-2.5-flash', 'gemini-2.0-flash',
                       'gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-pro']
            sucesso, ultimo_erro = False, ""
            for nome_modelo in modelos:
                try:
                    model = genai.GenerativeModel(nome_modelo)
                    response = model.generate_content(mensagens)
                    resposta_ia = response.text.strip()
                    sucesso = True
                    break
                except Exception as e:
                    ultimo_erro = str(e)
                    continue
            if not sucesso:
                print(f"ERRO PYTHON: nenhum modelo Gemini respondeu. "
                      f"Ultimo erro: {ultimo_erro}")
                return

        # --- PERSISTE MEMORIA E RETORNA PARA A INTERFACE ---
        memoria.append({"role": "assistant", "content": resposta_ia})
        try:
            with open(arquivo_memoria, 'w', encoding='utf-8') as f:
                json.dump(memoria, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

        print("CHAT_MSG_INICIO")
        print(resposta_ia)
        print("CHAT_MSG_FIM")

    except Exception as e:
        print(f"ERRO INTERNO PYTHON: {e}")


if __name__ == "__main__":
    try:
        sys.stdin.reconfigure(encoding='utf-8')
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()