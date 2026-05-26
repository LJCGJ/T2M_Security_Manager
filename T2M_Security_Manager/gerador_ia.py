import sys
import os
import time
import json
import subprocess

# ==============================================================================
# --- 1. O MOTOR DE AUTO-INSTALAÇÃO SILENCIOSA ---
# ==============================================================================
def garantir_bibliotecas():
    bibliotecas_faltando = []
    
    for lib in ['google-generativeai', 'requests', 'openai', 'beautifulsoup4', 'anthropic']:
        try:
            if lib == 'google-generativeai': import google.generativeai
            elif lib == 'beautifulsoup4': import bs4
            else: __import__(lib)
        except ImportError:
            bibliotecas_faltando.append(lib)
            
    if bibliotecas_faltando:
        for lib in bibliotecas_faltando:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib, "--quiet"])


# ==============================================================================
# --- 2. FUNÇÃO DE LIMPEZA E FORMATAÇÃO DE ESQUEMAS (PREPARAÇÃO PARA TOOLS) ---
# ==============================================================================
def clean_schema(schema: dict) -> dict:
    """
    Remove chaves do JSON Schema que a API do Gemini não suporta,
    preparando a base para integração futura com servidores de ferramentas autônomas.
    """
    if not isinstance(schema, dict):
        return schema

    cleaned = {}
    for key, value in schema.items():
        if key in ["$schema", "additionalProperties", "additional_properties"]:
            continue
        
        if isinstance(value, dict):
            cleaned[key] = clean_schema(value)
        elif isinstance(value, list):
            cleaned[key] = [clean_schema(item) if isinstance(item, dict) else item for item in value]
        else:
            cleaned[key] = value
            
    return cleaned


# ==============================================================================
# --- 3. EXTRAÇÃO DE CONTEXTO MCP (O "OLHO" DA INTELIGÊNCIA ARTIFICIAL) ---
# ==============================================================================
def extrair_contexto_mcp(url):
    """ Mapeia elementos estruturais reais da URL alvo """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(req.text, 'html.parser')
        
        inputs = soup.find_all('input')
        botoes = soup.find_all('button')
        forms = soup.find_all('form')
        
        mapa = f"=== CONTEXTO EXTRAÍDO DA URL ({url}) ===\n"
        mapa += f"Total de Formulários: {len(forms)}\n"
        mapa += "Inputs Encontrados:\n"
        for i in inputs:
            mapa += f" - Tipo: {i.get('type', 'N/A')} | ID: {i.get('id', 'N/A')} | Name: {i.get('name', 'N/A')}\n"
            
        mapa += "Botões Encontrados:\n"
        for b in botoes:
            mapa += f" - Texto: {b.text.strip()} | ID: {b.get('id', 'N/A')}\n"
            
        return mapa + "\n=======================================\n"
    except Exception as e:
        return f"--- AVISO SISTEMA --- Não foi possível ler a URL profundamente. Use nomes genéricos. (Erro: {str(e)})\n"


# ==============================================================================
# --- 4. FUNÇÃO PRINCIPAL E ROTEAMENTO "FLEX" ---
# ==============================================================================
def main():
    try:
        garantir_bibliotecas()
        
        if len(sys.argv) < 4:
            print("ERRO PYTHON: Argumentos insuficientes.")
            return
            
        api_key = sys.argv[1].strip()
        prompt_usuario = sys.argv[2]
        url_alvo = sys.argv[3]
        
        arquivo_memoria = "memoria_chat.json"
        memoria = []
        
        # --- VERIFICAÇÃO DE NOVO CHAT E CONTROLE DO MCP ---
        if prompt_usuario.startswith("--INICIAR_NOVO_CHAT--"):
            
            # A flag MCP_OFF será recebida do C++ caso a caixa de seleção seja desmarcada
            usar_mcp = "MCP_OFF" not in prompt_usuario
            
            if usar_mcp and url_alvo:
                mapa_mcp = extrair_contexto_mcp(url_alvo)
                status_visual = "INFORME AO USUÁRIO: O escâner MCP está ATIVO e a URL foi mapeada com sucesso."
            else:
                mapa_mcp = "--- MODO MCP DESATIVADO ---"
                status_visual = "INFORME AO USUÁRIO: O escâner MCP está DESLIGADO a pedido do operador. Foco exclusivo na geração abstrata de código."
            
            # NOVO PROMPT MESTRE UNIVERSAL (Segurança, QA, Robot Framework, Banco de Dados)
            prompt_mestre = f"""
            Aja como um Arquiteto Sênior de Automação, Qualidade (QA) e Engenharia de Segurança.
            A missão é auxiliar na estruturação de testes avançados, possuindo capacidade total para gerar scripts em Robot Framework (incluindo bibliotecas como DatabaseLibrary e conexões), Python, consultas SQL complexas e automações mobile/web.
            
            {mapa_mcp}
            
            INSTRUÇÕES OBRIGATÓRIAS:
            1. Realize uma apresentação profissional e amigável.
            2. {status_visual}
            3. Coloque o conhecimento avançado de automação à disposição e pergunte qual é o desafio técnico atual.
            Atenção: Não gere código nesta primeira resposta, apenas faça a apresentação inicial.
            """
            memoria = [{"role": "user", "content": prompt_mestre}]
            
        else:
            if os.path.exists(arquivo_memoria):
                with open(arquivo_memoria, 'r', encoding='utf-8') as f:
                    memoria = json.load(f)
            memoria.append({"role": "user", "content": prompt_usuario})

        resposta_ia = ""

        # --- ROTEADOR FLEX MULTI-IA ---
        
        # 1. Rota do GOOGLE GEMINI (Com resiliência a falhas de modelo)
        if api_key.startswith("AIza"):
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            mensagens_gemini = []
            for m in memoria:
                role = "user" if m["role"] == "user" else "model"
                mensagens_gemini.append({"role": role, "parts": [m["content"]]})
                
            modelos_para_testar = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-pro']
            
            sucesso = False
            ultimo_erro = ""
            for nome_modelo in modelos_para_testar:
                try:
                    model = genai.GenerativeModel(nome_modelo)
                    response = model.generate_content(mensagens_gemini)
                    resposta_ia = response.text.strip()
                    sucesso = True
                    break
                except Exception as e:
                    ultimo_erro = str(e)
                    continue
            
            if not sucesso:
                print(f"ERRO PYTHON: Nenhum modelo Gemini funcionou para esta chave. Último erro: {ultimo_erro}")
                return

        # 2. Rota da ANTHROPIC (CLAUDE)
        elif api_key.startswith("sk-ant-"):
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key)
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2048,
                system="Aja como um Arquiteto de Automação e Segurança. Se houver envio de código, o mesmo deve ser colocado sempre dentro de blocos ```nome_da_linguagem ``` para o sistema reconhecer.",
                messages=memoria
            )
            resposta_ia = response.content[0].text.strip()

        # 3. Rota da OPENAI (CHATGPT)
        elif api_key.startswith("sk-"):
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Aja como um Arquiteto de Automação e Segurança. Se houver envio de código, o mesmo deve ser colocado sempre dentro de blocos ```nome_da_linguagem ``` para o sistema reconhecer."}] + memoria
            )
            resposta_ia = response.choices[0].message.content.strip()

        else:
            print("ERRO PYTHON: API Key não reconhecida ou formato inválido.")
            return

        # --- SALVAMENTO E RETORNO PARA A INTERFACE C++ ---
        memoria.append({"role": "assistant", "content": resposta_ia})
        with open(arquivo_memoria, 'w', encoding='utf-8') as f:
            json.dump(memoria, f, ensure_ascii=False, indent=4)

        print("CHAT_MSG_INICIO")
        print(resposta_ia)
        print("CHAT_MSG_FIM")

    except Exception as e:
        print(f"ERRO INTERNO PYTHON: {str(e)}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()