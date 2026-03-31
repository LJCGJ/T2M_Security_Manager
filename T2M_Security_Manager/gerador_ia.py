import sys
import os
import time
import json
import subprocess

# --- O MOTOR DE AUTO-INSTALAÇÃO SILENCIOSA ---
def garantir_bibliotecas():
    bibliotecas_faltando = []
    
    for lib in ['google-generativeai', 'requests', 'openai', 'beautifulsoup4']:
        try:
            if lib == 'google-generativeai': import google.generativeai
            elif lib == 'beautifulsoup4': import bs4
            else: __import__(lib)
        except ImportError:
            bibliotecas_faltando.append(lib)
            
    if bibliotecas_faltando:
        for lib in bibliotecas_faltando:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib, "--quiet"])

def extrair_contexto_mcp(url):
    """ O 'Olho' da IA: Entra no site e mapeia os elementos reais (MCP Concept) """
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
        return f"--- AVISO MCP --- Não foi possível ler a URL profundamente. Use nomes genéricos. (Erro: {str(e)})\n"

def main():
    try:
        garantir_bibliotecas()
        
        if len(sys.argv) < 4:
            print("ERRO PYTHON: Argumentos insuficientes.")
            return
            
        api_key = sys.argv[1].strip()
        prompt_usuario = sys.argv[2]
        url_alvo = sys.argv[3]
        
        # --- GERENCIADOR DE MEMÓRIA DO CHAT ---
        arquivo_memoria = "memoria_chat.json"
        memoria = []
        
        # Se for um comando para iniciar NOVO chat, limpa a memória e roda o MCP
        if prompt_usuario == "--INICIAR_NOVO_CHAT--":
            mapa_mcp = extrair_contexto_mcp(url_alvo)
            prompt_mestre = f"""
            Você é um Engenheiro de Segurança Sênior. Você está ajudando o usuário através de um Chat interativo.
            
            {mapa_mcp}
            
            INSTRUÇÕES:
            Apresente-se rapidamente, diga que mapeou os elementos acima e pergunte qual teste de segurança o usuário deseja automatizar nesta URL. Não gere código ainda.
            """
            memoria = [{"role": "user", "content": prompt_mestre}]
        else:
            # Continua a conversa: carrega a memória anterior
            if os.path.exists(arquivo_memoria):
                with open(arquivo_memoria, 'r', encoding='utf-8') as f:
                    memoria = json.load(f)
            memoria.append({"role": "user", "content": prompt_usuario})

        resposta_ia = ""

        # --- O ROTEADOR MULTI-IA ---
        if api_key.startswith("AIza"):
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            # Converte a memória pro formato do Gemini
            mensagens_gemini = []
            for m in memoria:
                role = "user" if m["role"] == "user" else "model"
                mensagens_gemini.append({"role": role, "parts": [m["content"]]})
                
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(mensagens_gemini)
            resposta_ia = response.text.strip()

        elif api_key.startswith("sk-"):
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            # OpenAI já usa o formato nativo da nossa memória
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": "Você é um Engenheiro de Segurança. Se for enviar código Python, coloque-o sempre dentro de blocos ```python ``` para o sistema reconhecer."}] + memoria
            )
            resposta_ia = response.choices[0].message.content.strip()

        else:
            print("ERRO PYTHON: API Key não reconhecida.")
            return

        # Salva a resposta da IA na memória para o próximo turno
        memoria.append({"role": "assistant", "content": resposta_ia})
        with open(arquivo_memoria, 'w', encoding='utf-8') as f:
            json.dump(memoria, f, ensure_ascii=False, indent=4)

        # Retorna a resposta para o C++ exibir no Chat
        print("CHAT_MSG_INICIO")
        print(resposta_ia)
        print("CHAT_MSG_FIM")

    except Exception as e:
        print(f"ERRO INTERNO PYTHON: {str(e)}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()