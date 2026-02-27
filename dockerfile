# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt gunicorn

COPY . .

# 🔥 CRIAR DIRETÓRIOS E PERMISSÕES
RUN mkdir -p /app/media/logos /app/media/historico_fotos /app/staticfiles \
    && chmod -R 755 /app/media \
    && chmod -R 755 /app/staticfiles

EXPOSE 8001

# 🔥 MUDANÇA CRÍTICA: Usar Gunicorn em vez de runserver
CMD gunicorn --bind 0.0.0.0:8001 \
             --workers 3 \
             --timeout 120 \
             --access-logfile - \
             --error-logfile - \
             sementes.wsgi:application