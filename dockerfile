# Dockerfile otimizado
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar dependências de sistema mínimas
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar apenas requirements primeiro (melhor cache)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Criar diretórios necessários
RUN mkdir -p /app/media /app/media/logos /app/media/historico_fotos /app/staticfiles \
    && chmod -R 755 /app/media \
    && chmod -R 755 /app/staticfiles

EXPOSE 8001

# Comando Gunicorn
CMD gunicorn --bind 0.0.0.0:8001 \
             --workers 3 \
             --timeout 120 \
             --max-requests 1000 \
             --max-requests-jitter 50 \
             --access-logfile - \
             --error-logfile - \
             sementes.wsgi:application