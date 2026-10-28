# Dockerfile otimizado - Almoxarifado sem integrações externas
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV TZ=America/Sao_Paulo
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Instalar dependências de sistema necessárias
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Fuso horário do sistema operacional/logs
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

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

# ============================================
# SCRIPT DE INICIALIZAÇÃO (ENTRYPOINT)
# ============================================

# Criar script de entrypoint
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "========================================="\n\
echo "🚀 Iniciando aplicação..."\n\
echo "========================================="\n\
\n\
# Coletar arquivos estáticos\n\
echo "📦 Coletando arquivos estáticos..."\n\
python manage.py collectstatic --noinput --clear\n\
echo "✅ Arquivos estáticos coletados!"\n\
\n\
# Aplicar migrações\n\
echo "🔄 Aplicando migrações..."\n\
python manage.py migrate --noinput\n\
echo "✅ Migrações aplicadas!"\n\
\n\
echo "========================================="\n\
echo "🌟 Aplicação pronta!"\n\
echo "========================================="\n\
\n\
# Iniciar gunicorn\n\
exec gunicorn --bind 0.0.0.0:8001 \\\n\
             --workers 3 \\\n\
             --timeout 120 \\\n\
             --max-requests 1000 \\\n\
             --max-requests-jitter 50 \\\n\
             --access-logfile - \\\n\
             --error-logfile - \\\n\
             sementes.wsgi:application' \
> /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8001

# Usar o entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]