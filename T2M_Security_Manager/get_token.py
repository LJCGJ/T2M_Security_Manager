import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configuração de logs para não poluir o terminal
import logging
import os
os.environ['WDM_LOG_LEVEL'] = '0'
logging.getLogger('WDM').setLevel(logging.ERROR)

def main():
    # 1. Configura o Navegador (Chrome)
    options = webdriver.ChromeOptions()
    options.add_argument("--log-level=3") # Silencia erros do navegador
    options.add_argument("--ignore-certificate-errors")
    
    # Instala/Atualiza o driver do Chrome automaticamente
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"ERRO_DRIVER: {e}")
        return

    # 2. Pega a URL que veio do C++ (ou usa a padrão)
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        target_url = "https://sgidd.t2mlab.com/auth"

    print(f"[*] Abrindo navegador em: {target_url}")
    print("[*] Por favor, faça o LOGIN manualmente no navegador que abriu...")
    
    try:
        driver.get(target_url)
        
        # 3. Loop Infinito: Fica verificando a cada 1 segundo se o token apareceu
        token_encontrado = None
        tentativas = 0
        max_tentativas = 120 # Espera 2 minutos (120 seg)

        while tentativas < max_tentativas:
            time.sleep(1) 
            tentativas += 1

            # --- ESTRATÉGIA 1: LocalStorage (Padrão de SPAs modernas) ---
            # Procura por chaves comuns de autenticação
            chaves_comuns = ['token', 'access_token', 'jwt', 'auth', 'user', 'session']
            
            for chave in chaves_comuns:
                try:
                    valor = driver.execute_script(f"return localStorage.getItem('{chave}')")
                    
                    if valor:
                        # Se for JWT direto (começa com eyJ)
                        if "eyJ" in valor:
                            token_encontrado = valor
                            break
                        
                        # Se for um objeto JSON (ex: {"token": "eyJ..."})
                        if "{" in valor:
                            obj = json.loads(valor)
                            # Tenta chaves dentro do JSON
                            for k in ['token', 'accessToken', 'jwt']:
                                if k in obj and str(obj[k]).startswith('eyJ'):
                                    token_encontrado = obj[k]
                                    break
                except:
                    pass
                if token_encontrado: break

            # --- ESTRATÉGIA 2: Cookies (Caso o site use cookies) ---
            if not token_encontrado:
                cookies = driver.get_cookies()
                for cookie in cookies:
                    val = cookie.get('value', '')
                    if "eyJ" in val and len(val) > 100:
                        token_encontrado = val
                        break

            # --- SE ACHOU O TOKEN ---
            if token_encontrado:
                # Limpa aspas se tiver
                token_encontrado = token_encontrado.strip('"')
                
                # SINALIZA PARA O C++ QUE ACHOU
                print("TOKEN_ENCONTRADO_INICIO") 
                print(token_encontrado)
                print("TOKEN_ENCONTRADO_FIM")
                break
        
        if not token_encontrado:
            print("[!] Tempo esgotado (Timeout) ou login não detectado.")

    except Exception as e:
        print(f"[!] Erro durante execução: {e}")
    finally:
        # Fecha o navegador ao terminar
        try:
            driver.quit()
        except: pass

if __name__ == "__main__":
    main()