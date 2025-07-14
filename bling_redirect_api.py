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
    1. Inicia navegador com user agent real para evitar bloqueios
    2. Acessa página de login e aguarda campo de usuário
    3. Preenche credenciais e submete o formulário
    4. Aguarda elemento pós-login para confirmar autenticação
    5. Acessa target_url e aguarda carregamento completo
    6. Retorna URL final
    """
    try:
        with sync_playwright() as pw:
            logger.info("1) Iniciando navegador")
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            # Define user agent como Chrome desktop comum
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                                          "Chrome/115.0.0.0 Safari/537.36")
            page = context.new_page()

            logger.info(f"2) Indo para login_url: {req.login_url}")
            page.goto(req.login_url, timeout=45000)

            logger.info("3) Aguardando campo de usuário")
            page.wait_for_selector("#username", timeout=30000)
            page.wait_for_selector("input[type='password']", timeout=30000)

            logger.info("4) Preenchendo usuário e senha")
            page.fill("#username", req.username)
            page.fill("input[type='password']", req.password)

            logger.info("5) Clicando no botão Entrar")
            with page.expect_navigation(timeout=30000):
                page.click("button.login-button-submit")

            # Valida login: espera um elemento que só existe dentro do dashboard
            logger.info("6) Aguardando indicador de login bem-sucedido")
            page.wait_for_selector("nav[data-gtm='app-menu']", timeout=30000)

            logger.info(f"7) Indo para target_url: {req.target_url}")
            page.goto(req.target_url, timeout=45000)
            page.wait_for_load_state("networkidle", timeout=30000)

            final_url = page.url
            logger.info(f"8) URL final capturada: {final_url}")

            browser.close()
            return {"redirected_url": final_url}
    except PWTimeout as e:
        logger.error(f"Timeout: {e}")
        raise HTTPException(status_code=504, detail="Timeout ao carregar página ou esperar elemento")
    except Exception as e:
        logger.exception("Erro no fluxo")
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")
