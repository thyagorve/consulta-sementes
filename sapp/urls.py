from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'sapp'

urlpatterns = [
    # Autenticação
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='sapp/registration/login.html',
            redirect_authenticated_user=True,
        ),
        name='login'
    ),
    path('logout/', views.logout_view, name='logout'),

    # Tela Inicial (Dashboard)
    path('', views.dashboard, name='dashboard'),
    
    # --- CORREÇÃO AQUI ---
    # Coloquei 'estoque/' para diferenciar da página inicial
    path('estoque/', views.lista_estoque, name='lista_estoque'), 
    
    path('nova-entrada/', views.nova_entrada, name='nova_entrada'),
    path('transferir/<int:id>/', views.transferir, name='transferir'),
    path('editar/<int:id>/', views.editar, name='editar'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    
    # ...
    path('historico-geral/', views.historico_geral, name='historico_geral'),
    path('excluir/<int:id>/', views.excluir_lote, name='excluir_lote'),
    path('mudar-senha/', views.mudar_senha, name='mudar_senha'),
    path('api/buscar-dados-lote/', views.api_buscar_dados_lote, name='api_buscar_dados_lote'),
    
    
    path('gestao-estoque/', views.gestao_estoque, name='gestao_estoque'),
    path('exportar-excel/', views.exportar_excel, name='exportar_estoque_excel'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_estoque_pdf'),
    path('importar-estoque/', views.importar_estoque, name='importar_estoque'),
    

    path('gestao-estoque/', views.gestao_estoque, name='gestao_estoque'),
    path('exportar-excel/', views.exportar_excel, name='exportar_estoque_excel'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_estoque_pdf'),
    path('importar-estoque/', views.importar_estoque, name='importar_estoque'),
    path('aprovar-importacao/', views.aprovar_importacao, name='aprovar_importacao'),

# ...
]