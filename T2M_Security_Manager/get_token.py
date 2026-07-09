# -*- coding: utf-8 -*-
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def main():
    url = ""
    try:
        entrada = sys.stdin.read().strip()
        if entrada:
            url = entrada.splitlines()[0].strip()
    except Exception:
        pass
    if not url:
        url = sys.argv[1] if len(sys.argv) > 1 else "https://sgidd.t2mlab.com/auth"

    print(">>> Iniciando navegador para login...")
    driver = None
    try:
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        print(">>> Aguardando o login. Faça o login no navegador se necessário...")

        token = None
        chaves = ['token', 'access_token', 'jwt', 'authToken', 'id_token']
        for _ in range(60):
            time.sleep(1)
            for chave in chaves:
                token = driver.execute_script(
                    "return window.localStorage.getItem(arguments[0]) "
                    "|| window.sessionStorage.getItem(arguments[0]);", chave)
                if token:
                    break
            if token:
                break

        if token:
            print("TOKEN_ENCONTRADO_INICIO")
            print(token)
            print("TOKEN_ENCONTRADO_FIM")
        else:
            print(">>> Tempo esgotado. Token não encontrado.")
    except Exception as e:
        print(f">>> Erro no Selenium: {e}")
    finally:
        if driver is not None:
            try: driver.quit()
            except Exception: pass

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    main()