# -*- coding: utf-8 -*-
import sys
import os
import datetime
import google.generativeai as genai

def main():
    # O C++ envia: script.py, api_key, prompt, url_alvo
    if len(sys.argv) < 4:
        print("ERRO_ARGS: Faltam argumentos para a IA.")
        return

    api_key = sys.argv[1]
    prompt_usuario = sys.argv[2]
    url_alvo = sys.argv[3]

    if api_key == "PADRAO" or api_key.strip() == "":
        print("ERRO_CHAVE: Por favor, adicione uma API Key válida do Gemini no menu.")
        return

    try:
        # 1. Configura a IA
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # 2. O Prompt com o Contexto da URL
        prompt_sistema = f"""
        Você é um Engenheiro de Segurança de Software Sênior.
        Crie um script Python para realizar um teste de segurança na seguinte URL alvo: {url_alvo}
        
        Objetivo do Teste solicitado pelo usuário: {prompt_usuario}
        
        REGRAS RÍGIDAS E ABSOLUTAS:
        1. O script gerado DEVE utilizar 'sys.argv' para receber argumentos externos. 
           (sys.argv[1] será a URL alvo, sys.argv[2] será o Token JWT).
        2. Use a biblioteca 'requests' se for fazer requisições HTTP.
        3. Imprima resultados claros no terminal (ex: print(">>> Teste Concluído...")).
        4. RETORNE APENAS O CÓDIGO PYTHON PURO. Não use formatação markdown (como ```python).
        """

        response = model.generate_content(prompt_sistema)
        codigo_gerado = response.text

        # Limpeza caso a IA coloque a marcação markdown
        if codigo_gerado.startswith("```python"):
            codigo_gerado = codigo_gerado.replace("```python", "").replace("```", "").strip()
        elif codigo_gerado.startswith("```"):
            codigo_gerado = codigo_gerado.replace("```", "").strip()

        # 3. Criação da pasta "modelos de teste em IA" em Documentos
        pasta_documentos = os.path.join(os.path.expanduser('~'), 'Documents')
        pasta_ia = os.path.join(pasta_documentos, 'modelos de teste em IA')
        os.makedirs(pasta_ia, exist_ok=True)

        # 4. Salva o Arquivo com data e hora
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"scan_ia_{timestamp}.py"
        caminho_completo = os.path.join(pasta_ia, nome_arquivo)

        with open(caminho_completo, "w", encoding="utf-8") as f:
            f.write(codigo_gerado)

        # Retorna o caminho para o C++ adicionar na lista
        print(f"SUCESSO_IA:{caminho_completo}")

    except Exception as e:
        print(f"ERRO_API: {e}")

if __name__ == "__main__":
    main()