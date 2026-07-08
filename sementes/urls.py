from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.urls import re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    # Aponta para o arquivo urls.py que limpamos dentro da pasta sapp
    path('', include('sapp.urls')), 
    path('almoxarifado/', include('almoxarifado.urls', namespace='almoxarifado')),
]


if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]