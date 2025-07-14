# Exemplo para Playwright v1.53.0:
FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

WORKDIR /app

# Copia e instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala os binários e dependências necessárias para o Chromium
RUN playwright install --with-deps

# Copia o código da API
COPY bling_redirect_api.py .

# Expõe a porta que o Uvicorn usa
EXPOSE 8000

# Inicia o servidor Uvicorn
CMD ["uvicorn", "bling_redirect_api:app", "--host", "0.0.0.0", "--port", "8000"]