from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-sua-chave-secreta-aqui' # Mantenha a sua chave original
DEBUG = True
ALLOWED_HOSTS = ['tiagorve2.pythonanywhere.com','127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Nosso app principal
    'sapp',
    'django_filters',
    'widget_tweaks',
    
]

AUTO_LOGOUT_DELAY = 1800
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'sapp.middleware.AutoLogoutMiddleware',
]

ROOT_URLCONF = 'sementes.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- NOSSAS CONFIGURAÇÕES ---
# 1. Configuração para Media Files (Uploads do usuário)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 2. Configurações de Autenticação

LOGOUT_REDIRECT_URL = 'login'


# sementes/settings.py

# ... (resto das suas configurações) ...

# Redirecionamento após login e URL da página de login
LOGIN_REDIRECT_URL = 'sapp:dashboard' # Para onde ir após o login com sucesso
LOGIN_URL = 'sapp:login'              # Para onde ir se o acesso for negado (@login_required)
# sementes/settings.py

# ... (suas outras configurações) ...

# --- CONFIGURAÇÕES DO CELERY ---
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Broker (intermediário)
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0' # Onde os resultados são armazenados
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Sao_Paulo' # Use seu fuso horário

APP_VERSION = '1.0.0'