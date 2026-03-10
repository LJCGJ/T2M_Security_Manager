# -*- coding: utf-8 -*-
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def main():
    # Pega a URL que o C++ enviou ou usa a padrão
    url = sys.argv[1] if len(sys.argv) > 1 else "https://sgidd.t2mlab.com/auth"
    
    print(">>> Iniciando navegador para login...")
    
    try:
        # Configura e abre o Chrome
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless") # Remova o '#' no início desta linha se quiser que ele rode invisível
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        
        print(">>> Aguardando o login. Por favor, faça o login no navegador se necessário...")
        
        token = None
        # Fica tentando achar o token no LocalStorage por até 60 segundos
        for _ in range(60):
            time.sleep(1)
            # Tenta pegar o token (ajuste 'token' para o nome exato da chave do seu sistema se for diferente)
            token = driver.execute_script("return window.localStorage.getItem('token');")
            if token:
                break
                
        if token:
            print("TOKEN_ENCONTRADO_INICIO")
            print(token)
            print("TOKEN_ENCONTRADO_FIM")
        else:
            print(">>> Tempo esgotado. Token não encontrado.")
            
        driver.quit()

    except Exception as e:
        print(f">>> Erro no Selenium: {e}")

if __name__ == "__main__":
    main()