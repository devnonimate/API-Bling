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
    last_html = ""  # Armazena o HTML da página para debug
    try:
        with sync_playwright() as pw:
            logger.info("1) Iniciando navegador")
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(
                user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/115.0.0.0 Safari/537.36")
            )
            page = context.new_page()

            logger.info(f"2) Navegando para login_url: {req.login_url}")
            page.goto(req.login_url, timeout=45000)
            page.wait_for_load_state("networkidle", timeout=20000)
            last_html = page.content()

            logger.info("3) Aguardando campos de login do Bling")
            page.wait_for_selector("#username", timeout=30000)
            page.wait_for_selector("input[data-gtm-form-interact-field-id=\"1\"]", timeout=30000)

            logger.info("4) Preenchendo usuário e senha")
            page.fill("#username", req.username)
            page.fill("input[data-gtm-form-interact-field-id=\"1\"]", req.password)

            logger.info("5) Clicando no botão Entrar")
            with page.expect_navigation(timeout=30000):
                page.click("button.login-button-submit")

            page.wait_for_load_state("networkidle", timeout=20000)
            last_html = page.content()

            logger.info(f"6) Navegando para target_url: {req.target_url}")
            page.goto(req.target_url, timeout=45000)
            page.wait_for_load_state("networkidle", timeout=30000)

            final_url = page.url
            last_html = page.content()

            logger.info(f"7) URL final capturada: {final_url}")
            browser.close()
            return {"redirected_url": final_url}

    except PWTimeout as e:
        logger.error(f"Timeout: {e}\nHTML capturado:\n{last_html[:1000]}")
        raise HTTPException(status_code=504, detail={"error": "Timeout", "html": last_html[:10000]})
    except Exception as e:
        logger.exception("Erro inesperado no fluxo")
        raise HTTPException(status_code=500, detail={"error": str(e), "html": last_html[:10000]})
