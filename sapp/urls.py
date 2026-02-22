from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'sapp'

urlpatterns = [
    # ============================================================================
    # AUTENTICAÇÃO
    # ============================================================================
    path('login/', auth_views.LoginView.as_view(template_name='sapp/registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('mudar-senha/', views.mudar_senha, name='mudar_senha'),

    # ============================================================================
    # DASHBOARD E PÁGINAS PRINCIPAIS
    # ============================================================================
    path('', views.dashboard, name='dashboard'),  # Mantém o dashboard original
    path('dashboard/', views.dashboard_view, name='dashboard_novo'),  # Renomeado para não conflitar
    
    path('estoque/', views.lista_estoque, name='lista_estoque'),
    path('estoque/gestao/', views.gestao_estoque, name='gestao_estoque'),
    path('mapa-armazem/', views.lista_armazens, name='lista_armazens'),
    path('mapa-armazem/<int:armazem_numero>/', views.mapa_ocupacao_canvas, name='mapa_canvas'),

    # ============================================================================
    # OPERAÇÕES CRUD - ESTOQUE
    # ============================================================================
    path('estoque/nova-entrada/', views.nova_entrada, name='nova_entrada'),
    path('estoque/transferir/<int:id>/', views.transferir, name='transferir'),
    path('estoque/editar/<int:id>/', views.editar, name='editar'),
    path('estoque/excluir/<int:id>/', views.excluir_lote, name='excluir_lote'),
    
    # ============================================================================
    # SAÍDAS E RELATÓRIOS
    # ============================================================================
    path('estoque/registrar-saida/<int:id>/', views.registrar_saida, name='registrar_saida'),
    path('estoque/nova-saida/', views.nova_saida, name='nova_saida'),
    path('relatorio-saidas/', views.relatorio_saidas, name='relatorio_saidas'),
    path('api/estoque/estatisticas/', views.api_estoque_estatisticas, name='api_estoque_estatisticas'),

    # ============================================================================
    # CONFIGURAÇÕES, HISTÓRICO E EMPENHO
    # ============================================================================
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('historico-geral/', views.historico_geral, name='historico_geral'),
    path('empenho/', views.pagina_rascunho, name='pagina_rascunho'),
    path('pagina-rascunho/', views.pagina_rascunho, name='pagina_rascunho'),
    
    # ============================================================================
    # IMPORT/EXPORT
    # ============================================================================
    path('exportar-excel/', views.exportar_excel, name='exportar_estoque_excel'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_estoque_pdf'),
    
    # ============================================================================
    # CONFIGURAÇÃO DO DASHBOARD
    # ============================================================================
    path('salvar-config-dashboard/', views.salvar_config_dashboard, name='salvar_config_dashboard'),  # APENAS UMA VEZ

    # ============================================================================
    # DEBUG E MANUTENÇÃO
    # ============================================================================
    path('debug-estoque/', views.debug_estoque_completo, name='debug_estoque'),
    path('api/buscar-dados-lote/', views.api_buscar_dados_lote, name='api_buscar_dados_lote'),
    path('api/autocomplete-entrada/', views.api_autocomplete_nova_entrada, name='api_autocomplete_entrada'),
    path('api/saldo/<int:id>/', views.api_saldo_lote, name='api_saldo_lote'),
    path('api/buscar-lotes/', views.api_buscar_lotes, name='api_buscar_lotes'),
    path('api/buscar-lote-completo/', views.api_buscar_lote_completo, name='api_buscar_lote_completo'),
    path('api/verificar-lote/', views.api_verificar_lote, name='api_verificar_lote'),
    path('api/estoque-resumo/', views.api_estoque_resumo, name='api_estoque_resumo'),
    path('api/ultimas-movimentacoes/', views.api_ultimas_movimentacoes, name='api_ultimas_movimentacoes'),
    path('api/itens-empenhos/', views.api_itens_empenhos, name='api_itens_empenhos'),
    path('api/buscar-produto/', views.api_buscar_produto, name='api_buscar_produto'),
    path('api/salvar-todos-elementos/', views.salvar_todos_elementos, name='salvar_todos_elementos'),
    path('api/verificar-estoque/<str:endereco>/', views.verificar_estoque_endereco, name='verificar_estoque_endereco'),
    path('api/status-enderecos/', views.api_status_enderecos, name='api_status_enderecos'),
    path('api/exportar-mapa/<int:armazem_numero>/', views.exportar_mapa_json, name='exportar_mapa_json'),
    path('api/importar-mapa/<int:armazem_numero>/', views.importar_mapa_json, name='importar_mapa_json'),
    path('api/criar-armazens-automaticos/', views.criar_armazens_automaticos, name='criar_armazens_automaticos'),
    path('armazem/novo/', views.criar_armazem, name='criar_armazem'),
    path('editor-mapa/', views.editor_avancado, {'armazem_numero': 1}, name='editor_avancado_default'),
    path('api/atualizar-status-sistemico/', views.api_atualizar_status_sistemico, name='api_atualizar_status_sistemico'),
    path('api/estoque/<int:id>/detalhes/', views.detalhes_estoque_api, name='detalhes_estoque_api'),
    path('mapa-armazem/<int:armazem_numero>/', views.mapa_ocupacao_canvas, name='mapa_canvas'),
    path('editor-mapa/<int:armazem_numero>/', views.editor_avancado, name='editor_avancado'),
    path('armazem/editar-config/<int:armazem_id>/', views.editar_config_armazem, name='editar_config_armazem'),
]

# ============================================================================
# CONFIGURAÇÃO DE ARQUIVOS ESTÁTICOS E MÍDIA
# ============================================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)