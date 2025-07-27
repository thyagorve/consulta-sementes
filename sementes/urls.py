from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# Importa as views do nosso app
from sapp import views as sapp_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- Rotas Principais da Aplicação ---
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('dashboard/', sapp_views.dashboard, name='dashboard'),
    path('consulta/', sapp_views.consulta_view, name='consulta'),
    path('configuracao/', sapp_views.configuracao_view, name='configuracao'),
    
    # --- Rotas de Autenticação ---
    # Usamos nossa view customizada para logout via POST
    path('accounts/logout/', sapp_views.logout_view, name='logout'),
    # Incluímos as outras URLs do Django (troca de senha, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    path('historico/', sapp_views.historico_view, name='historico'),
]

# Adiciona o serviço de arquivos de media em modo de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)