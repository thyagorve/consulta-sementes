# sementes/urls.py

from django.contrib import admin
from django.urls import path, include 
from django.conf import settings # Para arquivos estáticos em desenvolvimento
from django.conf.urls.static import static # Para arquivos estáticos em desenvolvimento

urlpatterns = [
    path('admin/', admin.site.urls),
    # Inclui as URLs do seu aplicativo 'sapp' na raiz do projeto
    path('', include('sapp.urls')), 
]

# Apenas para servir arquivos estáticos e de mídia em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    

