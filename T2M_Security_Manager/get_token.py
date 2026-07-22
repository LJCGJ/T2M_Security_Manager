# -*- coding: utf-8 -*-
"""
T2M Security Manager - captura de token JWT apos login.

CONTRATO COM O APP (C++):
  A URL chega pela ENTRADA PADRAO (stdin), nao por argumento de linha de comando.
  Este era o bug anterior: o script lia sys.argv e por isso ignorava a URL
  digitada no app, tentando sempre um endereco fixo.

SAIDA:
  Sucesso -> TOKEN_ENCONTRADO_INICIO / <token> / TOKEN_ENCONTRADO_FIM  (stdout)
  Falhas  -> mensagens em stderr, para o app exibir o motivo real.
"""
import sys
import time

# Nomes de chave mais comuns onde sistemas guardam o token.
CHAVES_COMUNS = [
    "token", "access_token", "accessToken", "authToken", "auth_token",
    "jwt", "jwtToken", "id_token", "idToken", "bearerToken",
]

TEMPO_ESPERA_SEGUNDOS = 180   # tempo para o usuario fazer o login com calma


def log(msg):
    """Mensagens de progresso vao para stderr, separadas do token (stdout)."""
    print(msg, file=sys.stderr, flush=True)


def ler_url():
    """Le a URL do stdin (contrato com o app); aceita tambem argv em uso manual.
    Nao existe endereco padrao: a URL e sempre informada por quem usa."""
    url = ""
    try:
        if not sys.stdin.isatty():
            url = (sys.stdin.read() or "").strip()
    except Exception:
        url = ""
    if not url and len(sys.argv) > 1:
        url = sys.argv[1].strip()
    return url


def procurar_token(driver):
    """Varre localStorage e sessionStorage atras de um token.
    Primeiro tenta os nomes conhecidos; depois procura qualquer valor com cara de JWT."""
    for storage in ("localStorage", "sessionStorage"):
        # 1) nomes conhecidos
        for chave in CHAVES_COMUNS:
            try:
                valor = driver.execute_script(
                    f"return window.{storage}.getItem(arguments[0]);", chave)
                if valor and len(valor) > 20:
                    return valor, f"{storage}.{chave}"
            except Exception:
                continue
        # 2) qualquer chave cujo valor pareca um JWT (tres partes separadas por ponto)
        try:
            achado = driver.execute_script(f"""
                var s = window.{storage};
                for (var i = 0; i < s.length; i++) {{
                    var k = s.key(i);
                    var v = s.getItem(k);
                    if (v && v.split('.').length === 3 && v.length > 40) {{
                        return [k, v];
                    }}
                }}
                return null;
            """)
            if achado:
                return achado[1], f"{storage}.{achado[0]} (detectado como JWT)"
        except Exception:
            pass
    return None, None


def main():
    url = ler_url()
    if not url:
        log("Nenhuma URL informada. Preencha a URL do sistema onde deseja fazer login.")
        return 1
    if not (url.startswith("http://") or url.startswith("https://")):
        log(f"URL invalida: {url}. Ela deve comecar com http:// ou https://")
        return 1
    log(f">>> URL alvo: {url}")

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        log("ModuleNotFoundError: selenium nao instalado. "
            "Rode: pip install selenium webdriver-manager")
        return 1

    log(">>> Iniciando o navegador...")
    driver = None
    try:
        options = webdriver.ChromeOptions()
        # Opcoes que estabilizam a automacao (util em maquinas corporativas)
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Tenta o Selenium Manager (embutido no Selenium 4.6+). Se falhar,
        # recorre ao webdriver-manager, que baixa o driver correspondente.
        try:
            driver = webdriver.Chrome(options=options)
        except Exception:
            from webdriver_manager.chrome import ChromeDriverManager
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=options)

        driver.get(url)
        log(">>> Pagina aberta. FACA O LOGIN na janela do navegador.")
        log(f">>> Aguardando ate {TEMPO_ESPERA_SEGUNDOS}s pelo token...")

        token, origem = None, None
        for segundo in range(TEMPO_ESPERA_SEGUNDOS):
            time.sleep(1)
            try:
                token, origem = procurar_token(driver)
            except Exception:
                # Navegador pode estar navegando/recarregando: tenta de novo
                token = None
            if token:
                break
            # Sinal de vida a cada 15s, para o usuario saber que ainda esta esperando
            if segundo > 0 and segundo % 15 == 0:
                restante = TEMPO_ESPERA_SEGUNDOS - segundo
                log(f">>> Ainda aguardando o login... ({restante}s restantes)")
            # Se o usuario fechou o navegador, encerra sem esperar o tempo todo
            try:
                _ = driver.current_url
            except Exception:
                log(">>> A janela do navegador foi fechada antes do login.")
                return 1

        if token:
            log(f">>> Token localizado em {origem}.")
            print("TOKEN_ENCONTRADO_INICIO")
            print(token)
            print("TOKEN_ENCONTRADO_FIM")
            return 0

        log(">>> Tempo esgotado sem encontrar o token. "
            "Confirme se o login foi concluido e se o sistema guarda o token no navegador.")
        return 1

    except Exception as e:
        log(f">>> Erro no Selenium: {type(e).__name__}: {e}")
        return 1
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())