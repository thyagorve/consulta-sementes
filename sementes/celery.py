# sementes/celery.py
import os
from celery import Celery

# Define o módulo de configurações do Django para o Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sementes.settings')

app = Celery('sementes')

# Usa as configurações do Django. O namespace 'CELERY' significa que
# todas as configs do Celery no settings.py devem começar com CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Carrega automaticamente os arquivos tasks.py de todas as apps registradas
app.autodiscover_tasks()