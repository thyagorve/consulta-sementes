# Dockerfile
FROM python:3.12-slim

# Evita que o Python escreva arquivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# Garante que a saída do python seja exibida no terminal
ENV PYTHONUNBUFFERED=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copia o projeto
COPY . .

# Porta que o Django vai usar
EXPOSE 8001

# Comando para rodar a aplicação
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]