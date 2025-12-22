import environ
import os
from pathlib import Path
from datetime import timedelta

# ========== INICIALIZAÇÃO DO AMBIENTE ==========
env = environ.Env()
# Le arquivo .env se existir
environ.Env.read_env()

# ========== CONFIGURAÇÕES BÁSICAS ==========
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: não exponha isso em produção!
SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-sua-chave-secreta-provisoria-aqui')

# SECURITY WARNING: não execute com debug ativado em produção!
DEBUG = env.bool('DJANGO_DEBUG', default=True)

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'tiagorve2.pythonanywhere.com'])

# ========== APLICAÇÕES INSTALADAS ==========
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Apps de terceiros
    'django_filters',
    'widget_tweaks',
    
    # Celery
    'django_celery_results',
    
    # Nossa aplicação
    'sapp',
]

# ========== MIDDLEWARE ==========
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir arquivos estáticos em produção
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Nossos middlewares personalizados
    'sapp.middleware.AutoLogoutMiddleware',
    'sapp.middleware.Smart404FallbackMiddleware',
    'sapp.middleware.ForcePasswordChangeMiddleware',
]

# ========== AUTO LOGOUT ==========
AUTO_LOGOUT_DELAY = env.int('AUTO_LOGOUT_DELAY', default=1800)  # 30 minutos

# ========== URLS E TEMPLATES ==========
ROOT_URLCONF = 'sementes.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Para templates globais
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'sapp.context_processors.app_version_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'sementes.wsgi.application'

# ========== BANCO DE DADOS POSTGRESQL ==========
# CONFIGURAÇÃO SIMPLIFICADA
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DATABASE_NAME', default='sementes_db'),
        'USER': env('DATABASE_USER', default='postgres'),
        'PASSWORD': env('DATABASE_PASSWORD', default=''),
        'HOST': env('DATABASE_HOST', default='localhost'),
        'PORT': env('DATABASE_PORT', default='5432'),
        # Configurações otimizadas
        'CONN_MAX_AGE': 60,  # Conexões persistentes por 60 segundos
        'CONN_HEALTH_CHECKS': True,
    }
}

# Fallback para SQLite se PostgreSQL não estiver disponível
if not env.bool('USE_POSTGRESQL', default=True):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ========== VALIDAÇÕES DE SENHA ==========
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ========== I18N E TIMEZONE ==========
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
USE_L10N = True

# ========== ARQUIVOS ESTÁTICOS E MEDIA ==========
# Arquivos estáticos
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Otimização de arquivos estáticos com WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Arquivos de mídia (uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ========== AUTENTICAÇÃO E SESSÃO ==========
LOGIN_URL = 'sapp:login'
LOGIN_REDIRECT_URL = 'sapp:dashboard'
LOGOUT_REDIRECT_URL = 'sapp:login'

# Configurações de sessão (usando banco de dados para evitar problemas com Redis)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # IMPORTANTE: Usando DB em vez de cache
SESSION_COOKIE_AGE = env.int('SESSION_COOKIE_AGE', default=1209600)  # 2 semanas
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool('SESSION_EXPIRE_AT_BROWSER_CLOSE', default=False)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=not DEBUG)
SESSION_COOKIE_HTTPONLY = True
SESSION_SAVE_EVERY_REQUEST = True

# Configurações de CSRF
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=not DEBUG)
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# ========== SEGURANÇA ADICIONAL ==========
if not DEBUG:
    # HTTPS em produção
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HSTS
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Outras configurações de segurança
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

# ========== CELERY (TAREFAS ASSÍNCRONAS) ==========
# Configuração simplificada - usando banco de dados como backend
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='django://')  # Usa Django como broker
CELERY_RESULT_BACKEND = 'django-db'  # Usa o próprio PostgreSQL para resultados
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=True)  # Executa sincrono se True
CELERY_TASK_EAGER_PROPAGATES = True

# ========== CACHE ==========
# Cache simples usando memória local (evita problemas com Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'sementes-cache',
        'TIMEOUT': 300,  # 5 minutos
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# ========== LOGGING ==========
# Cria diretório de logs se não existir
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'ERROR',
        },
        'django.server': {
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': env('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
        'sapp': {
            'handlers': ['console', 'file', 'error_file'],
            'level': env('APP_LOG_LEVEL', default='DEBUG'),
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file', 'error_file'],
            'level': env('CELERY_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
    },
}

# ========== CONFIGURAÇÕES PERSONALIZADAS ==========
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Versão da aplicação
APP_VERSION = '1.0.1'

# Configurações específicas do seu app
MAX_UPLOAD_SIZE = env.int('MAX_UPLOAD_SIZE', default=10485760)  # 10MB
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']

# ========== CONFIGURAÇÕES PARA EASYPANEL ==========
# O Easypanel pode injetar variáveis específicas
EASYPANEL = env.bool('EASYPANEL', default=False)

# Se estiver rodando no Easypanel, ajuste algumas configurações
if EASYPANEL:
    # Garante que os caminhos absolutos funcionem
    STATIC_ROOT = env('STATIC_ROOT', default=STATIC_ROOT)
    MEDIA_ROOT = env('MEDIA_ROOT', default=MEDIA_ROOT)
    
    # Força HTTPS em produção
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Configurações de banco de dados específicas do Easypanel
    if env('DATABASE_URL', default=None):
        # Converte DATABASE_URL para configuração do Django
        DATABASES['default'] = env.db('DATABASE_URL')
    
    # Configurações de Redis se disponível
    if env('REDIS_URL', default=None):
        try:
            CACHES['default'] = {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': env('REDIS_URL'),
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'CONNECTION_POOL_KWARGS': {
                        'max_connections': 50,
                    }
                },
                'KEY_PREFIX': 'sementes',
            }
            # Opcional: usar Redis para sessões se estiver funcionando
            # SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
            # SESSION_CACHE_ALIAS = 'default'
            
            # Configurar Celery com Redis se disponível
            CELERY_BROKER_URL = env('REDIS_URL')
            CELERY_RESULT_BACKEND = env('REDIS_URL')
            CELERY_TASK_ALWAYS_EAGER = False
        except Exception as e:
            print(f"Redis não configurado: {e}")
            # Mantém configurações locais se Redis falhar

