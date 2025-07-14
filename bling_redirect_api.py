# bling_redirect_api.py
import sys
import asyncio
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Configuração para suporte de subprocess no Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configura logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CaptureRequest(BaseModel):
    login_url: str
    target_url: str
    username: str
    password: str

app = FastAPI()

@app.post("/capture-redirect")
def capture_redirect(req: CaptureRequest):
    """
    Fluxo:
    1. Inicia navegador em modo headless com configurações para ambiente Linux
    2. Acessa página de login e aguarda os campos corretos
    3. Preenche credenciais usando os seletores exatos do Bling
    4. Clica no botão Entrar e aguarda navegação
    5. Acessa target_url e aguarda carregamento completo
    6. Retorna URL final redirecionada
    """
    try:
        with sync_playwright() as pw:
            logger.info("1) Iniciando navegador")
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            # Optional: definir user agent para minimizar detecção de bot
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/115.0.0.0 Safari/537.36")
            )
            page = context.new_page()

            logger.info(f"2) Navegando para login_url: {req.login_url}")
            page.goto(req.login_url, timeout=45000)
            page.wait_for_load_state("networkidle", timeout=20000)

            logger.info("3) Aguardando campos de login do Bling")
            # Campo de usuário by ID
            page.wait_for_selector("#username", timeout=30000)
            # Campo de senha: usa data attribute pois o type é text
            page.wait_for_selector("input[data-gtm-form-interact-field-id=\"1\"]", timeout=30000)

            logger.info("4) Preenchendo usuário e senha")
            page.fill("#username", req.username)
            page.fill("input[data-gtm-form-interact-field-id=\"1\"]", req.password)

            logger.info("5) Clicando no botão Entrar")
            # Botão pelo texto ou classe
            with page.expect_navigation(timeout=30000):
                page.click("button.login-button-submit")

            # Aqui você pode validar sucesso de login, por exemplo, aguardando menu ou perfil
            # Exemplo genérico: espera carregamento de um elemento do dashboard
            page.wait_for_load_state("networkidle", timeout=20000)

            logger.info(f"6) Navegando para target_url: {req.target_url}")
            page.goto(req.target_url, timeout=45000)
            page.wait_for_load_state("networkidle", timeout=30000)

            final_url = page.url
            logger.info(f"7) URL final capturada: {final_url}")

            browser.close()
            return {"redirected_url": final_url}

    except PWTimeout as e:
        logger.error(f"Timeout: {e}")
        raise HTTPException(status_code=504, detail="Timeout ao carregar página ou esperar elemento")
    except Exception as e:
        logger.exception("Erro inesperado no fluxo")
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")

# Executar localmente com:
# uvicorn bling_redirect_api:app --reload --host 0.0.0.0 --port 8000
