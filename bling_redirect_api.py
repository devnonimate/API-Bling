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
    1. Navega para página de login
    2. Aguarda campos de usuário e senha
    3. Preenche credenciais e clica em Entrar
    4. Aguarda navegação pós-login
    5. Navega para target_url
    6. Aguarda rede ociosa e captura URL final
    """
    try:
        with sync_playwright() as pw:
            logger.info("1) Iniciando navegador")
            browser = pw.chromium.launch(headless=True)  # headless para produção
            context = browser.new_context()
            page = context.new_page()

            logger.info(f"2) Indo para login_url: {req.login_url}")
            page.goto(req.login_url, timeout=30000)

            logger.info("3) Aguardando campos de login")
            page.wait_for_selector("#username", timeout=15000)
            page.wait_for_selector("input[type='password']", timeout=15000)

            logger.info("4) Preenchendo usuário e senha")
            page.fill("#username", req.username)
            page.fill("input[type='password']", req.password)

            logger.info("5) Clicando em Entrar e aguardando navegação")
            with page.expect_navigation(timeout=20000):
                page.click("button.login-button-submit")

            logger.info(f"6) URL após login: {page.url}")

            logger.info(f"7) Indo para target_url: {req.target_url}")
            page.goto(req.target_url, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=20000)

            final_url = page.url
            logger.info(f"8) URL final capturada: {final_url}")

            browser.close()
            return {"redirected_url": final_url}

    except PWTimeout as e:
        logger.error(f"Timeout: {e}")
        raise HTTPException(status_code=504, detail="Timeout ao carregar página")
    except Exception as e:
        logger.exception("Erro no fluxo")
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")