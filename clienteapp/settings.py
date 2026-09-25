import os  # ← ESSENCIAL: Adicione esta linha!
import sys
from pathlib import Path
import environ

# Inicialização do environ
env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent

# Carregar variáveis de ambiente
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    environ.Env.read_env(env_file)

# ==========================================
# SEGURANÇA E CONFIGURAÇÕES BÁSICAS
# ==========================================
SECRET_KEY = env('SECRET_KEY', default='dev-only-change-me')

# Limites de upload
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Tipos de mídia permitidos
ALLOWED_MEDIA_TYPES = [
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/pdf',
    'video/mp4',
    'video/mpeg',
    'audio/mpeg',
    'audio/ogg',
]

DEBUG = env.bool('DJANGO_DEBUG', default=False)
if not DEBUG and SECRET_KEY == 'dev-only-change-me':
    raise RuntimeError('SECRET_KEY deve ser configurada no ambiente em produção.')

# ==========================================
# CONFIGURAÇÕES DE HOST E URL
# ==========================================
ALLOWED_HOSTS = [
    'gestor.tlsprimesolutions.com.br',
    'gestortls-mainel2.99vew9.easypanel.host',
    'localhost',
    '127.0.0.1',
    '0.0.0.0',  # Adicionado para Docker
    '192.168.100.66',
]

CSRF_TRUSTED_ORIGINS = [
    'https://gestor.tlsprimesolutions.com.br',
    'https://gestortls-mainel2.99vew9.easypanel.host',
]

# Configurações para proxy reverso (Easypanel)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Configurações da aplicação Django
ROOT_URLCONF = 'clienteapp.urls'
WSGI_APPLICATION = 'clienteapp.wsgi.application'

# ==========================================
# APPS INSTALADAS
# ==========================================
INSTALLED_APPS = [
    # Apps de terceiros primeiro
    'whitenoise.runserver_nostatic',
    
    # Apps do Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    
    # Seus apps
    'rest_framework',
    'clientes',
    'whatsapp_integration',
    'django_extensions',
    'financeiro',
  
]

# ==========================================
# MIDDLEWARE
# ==========================================
MIDDLEWARE = [
    #'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'django.middleware.cache.FetchFromCacheMiddleware',
    
    # Seu middleware personalizado
    'clienteapp.middleware.redirect_404.Redirect404ToLoginMiddleware',
    'clientes.middleware.LogAcessoMiddleware',  # ← ADICIONE ESTA LINHA
]

# ==========================================
# CONFIGURAÇÃO DE TEMPLATES
# ==========================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'whatsapp_integration' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'clientes.context_processors.user_config',
            ],
        },
    },
]

# ==========================================
# BANCO DE DADOS
# ==========================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
        'CONN_MAX_AGE': 60,
    }
}

# ==========================================
# ARQUIVOS ESTÁTICOS (CONFIGURAÇÃO CORRIGIDA)
# ==========================================
STATIC_URL = '/static/'  # ← ADICIONE ESTA LINHA
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    BASE_DIR / 'clientes' / 'static',
    BASE_DIR / 'whatsapp_integration' / 'static',
    BASE_DIR / 'static',
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}



# ==========================================
# AUTENTICAÇÃO E USUÁRIOS
# ==========================================
AUTH_USER_MODEL = 'clientes.CustomUser'

# URLs de login/logout
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ==========================================
# INTERNACIONALIZAÇÃO E FUSO HORÁRIO
# ==========================================
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True
USE_TZ = True

USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = '.'
DECIMAL_SEPARATOR = ','

# ==========================================
# CONFIGURAÇÕES DE SESSÃO
# ==========================================
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 horas
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = 'Lax'

# ==========================================
# SEGURANÇA
# ==========================================
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# ==========================================
# CONFIGURAÇÕES DA EVOLUTION API
# ==========================================
EVOLUTION_API_BASE_URL = env('EVOLUTION_API_BASE_URL')
EVOLUTION_GLOBAL_API_KEY = env('EVOLUTION_GLOBAL_API_KEY')
EVOLUTION_WEBHOOK_URL = env('EVOLUTION_WEBHOOK_URL')
EVOLUTION_DIRECT_WEBHOOK_PATH = env('EVOLUTION_DIRECT_WEBHOOK_PATH')
EVOLUTION_WEBHOOK_SECRET = env('EVOLUTION_WEBHOOK_SECRET', default='')
EVOLUTION_API_URL = env('EVOLUTION_API_BASE_URL')
EVOLUTION_API_KEY = env('EVOLUTION_GLOBAL_API_KEY')
EVOLUTION_RECOVERY_INSTANCE = env('EVOLUTION_RECOVERY_INSTANCE', default='gestor')
GROQ_API_KEY = env('GROQ_API_KEY', default='')

EVOLUTION_API_HEADERS = {
    'apikey': EVOLUTION_GLOBAL_API_KEY,
    'Content-Type': 'application/json',
}


# ==========================================
# CONFIGURAÇÕES DO SITE
# ==========================================
SITE_ID = env.int('SITE_ID', default=1)

# No início do settings.py, BASE_DIR já está definido
log_file_path = BASE_DIR / ('debug.log' if DEBUG else 'app.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': str(log_file_path),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.utils.autoreload': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'clienteapp': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
        'whatsapp_integration': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
    },
}

# ==========================================
# REST FRAMEWORK
# ==========================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        ['rest_framework.renderers.JSONRenderer', 'rest_framework.renderers.BrowsableAPIRenderer']
        if DEBUG else ['rest_framework.renderers.JSONRenderer']
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    }
}

# ==========================================
# CONFIGURAÇÕES ADICIONAIS
# ==========================================
HEALTH_CHECK_ENDPOINT = env('HEALTH_CHECK_ENDPOINT', default='/')

# Configuração para arquivos de mídia
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Tamanho máximo de requisições
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

# Configuração para email (caso precise)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'



# ==========================================
# CONFIGURAÇÃO DE CACHE (OTIMIZADO PARA AVATARES)
# ==========================================

# Crie a pasta de cache se não existir
CACHE_DIR = BASE_DIR / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': str(CACHE_DIR),
        'TIMEOUT': 60 * 60 * 24 * 30,  # 30 dias
        'OPTIONS': {
            'MAX_ENTRIES': 5000,
        }
    }
}

# WhiteNoise
WHITENOISE_MAX_AGE = 31536000  # 1 ano
RUNNING_DEV_SERVER = 'runserver' in sys.argv
# Em desenvolvimento, serve os arquivos-fonte sem exigir collectstatic.
# Em produção, continua usando STATIC_ROOT normalmente.
WHITENOISE_USE_FINDERS = DEBUG or RUNNING_DEV_SERVER
WHITENOISE_AUTOREFRESH = DEBUG or RUNNING_DEV_SERVER

# ==========================================
# CONFIGURAÇÕES FINAIS
# ==========================================



        
# ==========================================
# CONFIGURAÇÕES FINAIS
# ==========================================
X_FRAME_OPTIONS = 'DENY'
APPEND_SLASH = True
SECURE_CONTENT_TYPE_NOSNIFF = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
