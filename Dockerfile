# Use imagem base oficial do Node.js para compatibilidade com Playwright
FROM mcr.microsoft.com/playwright/python:latest

# Diretório de trabalho
WORKDIR /app

# Copia requirements e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da API
COPY bling_redirect_api.py .

# Expor porta
EXPOSE 8000

# Comando de inicialização
CMD ["uvicorn", "bling_redirect_api:app", "--host", "0.0.0.0", "--port", "8000"]