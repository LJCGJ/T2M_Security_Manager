# -*- coding: utf-8 -*-
import sys
import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_MEMORIA = os.path.join(SCRIPT_DIR, "memoria_chat.json")

def responder(texto):
    print("CHAT_MSG_INICIO")
    print(texto)
    print("CHAT_MSG_FIM")

def tem_lib(modulo):
    try:
        __import__(modulo)
        return True
    except ImportError:
        return False

def extrair_contexto_dom(url):
    if not tem_lib("requests") or not tem_lib("bs4"):
        return ("--- AVISO: bibliotecas 'requests'/'beautifulsoup4' ausentes. "
                "Scanner de interface desativado. Rode: pip install -r requirements.txt ---\n")
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=headers, timeout=8)
        html = req.text[:500_000]
        soup = BeautifulSoup(html, 'html.parser')
        inputs = soup.find_all('input')
        botoes = soup.find_all('button')
        forms = soup.find_all('form')
        mapa = f"=== CONTEXTO EXTRAÍDO DA URL ({url}) ===\n"
        mapa += f"Total de Formulários: {len(forms)}\n"
        mapa += "Inputs Encontrados:\n"
        for i in inputs[:60]:
            mapa += f" - Tipo: {i.get('type', 'N/A')} | ID: {i.get('id', 'N/A')} | Name: {i.get('name', 'N/A')}\n"
        mapa += "Botões Encontrados:\n"
        for b in botoes[:60]:
            mapa += f" - Texto: {b.text.strip()[:40]} | ID: {b.get('id', 'N/A')}\n"
        return mapa + "\n=======================================\n"
    except Exception as e:
        return f"--- AVISO: Não foi possível ler a URL. Use nomes genéricos. (Erro: {e}) ---\n"

def main():
    try:
        dados = sys.stdin.read()
        partes = dados.split('\n', 2)
        api_key = partes[0].strip() if len(partes) > 0 else ""
        url_alvo = partes[1].strip() if len(partes) > 1 else ""
        prompt_usuario = partes[2] if len(partes) > 2 else ""

        if not api_key:
            responder("Erro: nenhuma chave de API foi informada.")
            return

        memoria = []

        if prompt_usuario.startswith("--INICIAR_NOVO_CHAT--"):
            usar_mcp = "MCP_OFF" not in prompt_usuario
            if usar_mcp and url_alvo:
                mapa = extrair_contexto_dom(url_alvo)
                status = "INFORME AO USUÁRIO: O escâner de interface está ATIVO e a URL foi mapeada."
            else:
                mapa = "--- SCANNER DE INTERFACE DESATIVADO ---"
                status = "INFORME AO USUÁRIO: O escâner está DESLIGADO a pedido do operador."

            prompt_mestre = f"""
Aja como um Arquiteto Sênior de Automação, Qualidade (QA) e Engenharia de Segurança.
Sua missão é auxiliar na estruturação de testes avançados, com capacidade de gerar scripts
em Robot Framework (incluindo DatabaseLibrary e conexões), Python, consultas SQL complexas
e automações web/mobile.

{mapa}

REGRAS TÉCNICAS PARA GERAÇÃO DE CÓDIGO:
- Todo código deve vir dentro de blocos ```linguagem ... ``` (ex.: ```python, ```robot, ```sql).
- Nos scripts Python de teste, leia a URL de sys.argv[1] e o TOKEN de os.environ.get('T2M_AUTH_TOKEN', '').
  NUNCA leia o token de sys.argv, pois ele não é mais passado por linha de comando.

INSTRUÇÕES OBRIGATÓRIAS:
1. Faça uma apresentação profissional e amigável.
2. {status}
3. Coloque seu conhecimento à disposição e pergunte qual é o desafio técnico atual.
Atenção: NÃO gere código nesta primeira resposta, apenas a apresentação.
"""
            memoria = [{"role": "user", "content": prompt_mestre}]
        else:
            if os.path.exists(ARQUIVO_MEMORIA):
                with open(ARQUIVO_MEMORIA, 'r', encoding='utf-8') as f:
                    memoria = json.load(f)
            memoria.append({"role": "user", "content": prompt_usuario})

        resposta_ia = ""

        if api_key.startswith("AIza"):  # Google Gemini
            if not tem_lib("google.generativeai"):
                responder("Biblioteca ausente: google-generativeai. Rode: pip install -r requirements.txt")
                return
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            mensagens = [{"role": ("user" if m["role"] == "user" else "model"),
                          "parts": [m["content"]]} for m in memoria]
            modelos = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash-latest', 'gemini-1.5-flash']
            ultimo_erro = ""
            for nome in modelos:
                try:
                    resposta_ia = genai.GenerativeModel(nome).generate_content(mensagens).text.strip()
                    break
                except Exception as e:
                    ultimo_erro = str(e)
            if not resposta_ia:
                responder(f"Nenhum modelo Gemini respondeu para esta chave. Último erro: {ultimo_erro}")
                return

        elif api_key.startswith("sk-ant-"):  # Anthropic Claude
            if not tem_lib("anthropic"):
                responder("Biblioteca ausente: anthropic. Rode: pip install -r requirements.txt")
                return
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2048,
                system="Aja como Arquiteto de Automação e Segurança. Envolva todo código em blocos ```linguagem ```.",
                messages=memoria,
            )
            resposta_ia = resp.content[0].text.strip()

        elif api_key.startswith("sk-"):  # OpenAI
            if not tem_lib("openai"):
                responder("Biblioteca ausente: openai. Rode: pip install -r requirements.txt")
                return
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Aja como Arquiteto de Automação e Segurança. Envolva código em blocos ```linguagem ```."}] + memoria,
            )
            resposta_ia = resp.choices[0].message.content.strip()
        else:
            responder("Chave de API não reconhecida (esperado prefixo AIza / sk-ant- / sk-).")
            return

        memoria.append({"role": "assistant", "content": resposta_ia})
        with open(ARQUIVO_MEMORIA, 'w', encoding='utf-8') as f:
            json.dump(memoria, f, ensure_ascii=False, indent=4)

        responder(resposta_ia)

    except Exception as e:
        responder(f"ERRO INTERNO PYTHON: {e}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()