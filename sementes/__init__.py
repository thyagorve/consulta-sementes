# sementes/__init__.py

# Isso garantirá que o app seja sempre importado quando o Django iniciar
from .celery import app as celery_app

__all__ = ('celery_app',)