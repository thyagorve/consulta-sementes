# sapp/urls.py

from django.urls import path
from . import views
# Importe as views de autenticação prontas do Django
from django.contrib.auth import views as auth_views
#from .views import MeuLoginView

app_name = 'sapp'

urlpatterns = [
    # URLs de Autenticação



    
  
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='sapp/registration/login.html',
            redirect_field_name=None,               # ignora ?next=...
            redirect_authenticated_user=True,       # quem já tá logado vai direto pro dashboard
        ),
        name='login'
    ),
    path('logout/', views.logout_view, name='logout'),
    

    # Suas outras URLs
    path('', views.dashboard, name='dashboard'), # Dashboard na raiz
    path('consulta/', views.consulta_view, name='consulta'),
    path('historico/', views.historico_view, name='historico'),
    path('configuracao/', views.configuracao_view, name='configuracao'),
    path('api/importar-lotes-clipboard/', views.importar_clipboard_em_lotes_view, name='api_importar_lotes_clipboard'),
    path('produtos/', views.listar_produtos_view, name='listar_produtos'),
    path('lotes/', views.listar_lotes_view, name='listar_lotes'),
]


