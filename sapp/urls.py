from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'sapp'

urlpatterns = [
    # --- Autenticação ---
    path('login/', auth_views.LoginView.as_view(template_name='sapp/registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('mudar-senha/', views.mudar_senha, name='mudar_senha'),

    # --- Dashboard ---
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # --- Gestão de Estoque (Prefixos corrigidos) ---
    path('estoque/', views.lista_estoque, name='lista_estoque'),
    path('estoque/gestao/', views.gestao_estoque, name='gestao_estoque'),
    
    # --- Operações CRUD (URLs ajustadas para evitar 404) ---
    path('estoque/nova-entrada/', views.nova_entrada, name='nova_entrada'),
    path('estoque/transferir/<int:id>/', views.transferir, name='transferir'), # CORRIGIDO AQUI
    path('estoque/editar/<int:id>/', views.editar, name='editar'),             # CORRIGIDO AQUI
    path('estoque/excluir/<int:id>/', views.excluir_lote, name='excluir_lote'),
    
    # --- Saídas ---
    path('estoque/registrar-saida/<int:id>/', views.registrar_saida, name='registrar_saida'),
    path('estoque/nova-saida/', views.nova_saida, name='nova_saida'),
    path('relatorio-saidas/', views.relatorio_saidas, name='relatorio_saidas'),
    
    # --- APIs (Mantidas) ---
    path('api/buscar-dados-lote/', views.api_buscar_dados_lote, name='api_buscar_dados_lote'),
    path('api/saldo/<int:id>/', views.api_saldo_lote, name='api_saldo_lote'),
    path('api/buscar-lotes/', views.api_buscar_lotes, name='api_buscar_lotes'),
    path('api/buscar-lote-completo/', views.api_buscar_lote_completo, name='api_buscar_lote_completo'),
    path('api/verificar-lote/', views.api_verificar_lote, name='api_verificar_lote'),
    path('api/estoque-resumo/', views.api_estoque_resumo, name='api_estoque_resumo'),
    path('api/ultimas-movimentacoes/', views.api_ultimas_movimentacoes, name='api_ultimas_movimentacoes'),
    
    # --- Configurações e Histórico ---
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('historico-geral/', views.historico_geral, name='historico_geral'),
    
    # --- Import/Export ---
    path('importar-estoque/', views.importar_estoque, name='importar_estoque'),
    path('aprovar-importacao/', views.aprovar_importacao, name='aprovar_importacao'),
    path('exportar-excel/', views.exportar_excel, name='exportar_estoque_excel'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_estoque_pdf'),
    
    # --- Debug ---
    path('debug-estoque/', views.debug_estoque_completo, name='debug_estoque'),
    path('limpar-cache-importacao/', views.limpar_cache_importacao, name='limpar_cache_importacao'),
    
    
    
    
    
    path('api/buscar-dados-lote/', views.api_buscar_dados_lote, name='api_buscar_dados_lote'),
    
        # --- Sistema de Empenho/Rascunho ---
    path('empenho/', views.pagina_rascunho, name='pagina_rascunho'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)