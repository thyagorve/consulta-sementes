from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Aponta para o arquivo urls.py que limpamos dentro da pasta sapp
    path('', include('sapp.urls')), 
]