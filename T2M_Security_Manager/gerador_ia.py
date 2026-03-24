import sys
import os
import time
import subprocess

# --- O MOTOR DE AUTO-INSTALAÇÃO SILENCIOSA ---
def garantir_bibliotecas():
    bibliotecas_faltando = []
    
    try:
        import google.generativeai
    except ImportError:
        bibliotecas_faltando.append("google-generativeai")
        
    try:
        import requests
    except ImportError:
        bibliotecas_faltando.append("requests")
        
    try:
        import openai
    except ImportError:
        bibliotecas_faltando.append("openai")
        
    if bibliotecas_faltando:
        for lib in bibliotecas_faltando:
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib, "--quiet"])

def main():
    try:
        garantir_bibliotecas()
        import requests
        
        if len(sys.argv) < 4:
            print("ERRO PYTHON: O C++ não enviou a chave, prompt ou URL corretamente.")
            return
            
        api_key = sys.argv[1].strip()
        prompt_usuario = sys.argv[2]
        url_alvo = sys.argv[3]
        
        prompt_mestre = f"""
        Você é um Engenheiro de Segurança da Informação Sênior focado em testes automatizados.
        Crie um script Python focado em testar vulnerabilidades na seguinte URL: {url_alvo}
        
        Ação solicitada pelo usuário:
        {prompt_usuario}
        
        REGRAS ABSOLUTAS:
        1. Retorne APENAS o código Python. Sem formatação markdown, sem textos extras.
        2. O script gerado deve receber a URL por sys.argv[1] e o Token por sys.argv[2].
        3. O script deve importar 'sys' e 'requests'.
        4. Faça tratamento de erros (try/except) para não travar em falhas de conexão.
        """

        codigo = ""

        # --- O NOVO ROTEADOR MULTI-IA ---
        if api_key.startswith("AIza"):
            # ROTA 1: GOOGLE GEMINI
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            modelos_disponiveis = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            preferencias = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']
            
            modelo_escolhido = None
            for pref in preferencias:
                if pref in modelos_disponiveis:
                    modelo_escolhido = pref
                    break
                    
            if not modelo_escolhido:
                if modelos_disponiveis:
                    modelo_escolhido = modelos_disponiveis[0]
                else:
                    print("ERRO PYTHON: Esta API Key não tem acesso a nenhum modelo de texto da Google.")
                    return

            model = genai.GenerativeModel(modelo_escolhido)
            response = model.generate_content(prompt_mestre)
            codigo = response.text.strip()

        elif api_key.startswith("sk-"):
            # ROTA 2: OPENAI (CHATGPT)
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Modelo super rápido e excelente para código
                messages=[
                    {"role": "system", "content": "Você é um Engenheiro de Segurança Sênior experiente em Python."},
                    {"role": "user", "content": prompt_mestre}
                ]
            )
            codigo = response.choices[0].message.content.strip()

        else:
            print("ERRO PYTHON: Formato de API Key não reconhecido. Use uma chave do Google Gemini (AIza...) ou OpenAI (sk-...).")
            return

        # --- LIMPEZA E SALVAMENTO ---
        marcador_python = "```" + "python"
        marcador_simples = "```"
        if codigo.startswith(marcador_python):
            codigo = codigo[len(marcador_python):]
        elif codigo.startswith(marcador_simples):
            codigo = codigo[len(marcador_simples):]
        if codigo.endswith(marcador_simples):
            codigo = codigo[:-len(marcador_simples)]
        codigo = codigo.strip()

        pasta_docs = os.path.expanduser("~/Documents")
        pasta_ia = os.path.join(pasta_docs, "modelos de teste em IA")
        os.makedirs(pasta_ia, exist_ok=True)
        
        nome_arquivo = f"scan_dinamico_{int(time.time())}.py"
        caminho_completo = os.path.join(pasta_ia, nome_arquivo)
        
        with open(caminho_completo, "w", encoding="utf-8") as f:
            f.write(codigo)
            
        print(f"SUCESSO_IA:{caminho_completo}")

    except Exception as e:
        print(f"ERRO INTERNO PYTHON: {str(e)}")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()