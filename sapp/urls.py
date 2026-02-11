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
    path('', views.dashboard, name='dashboard'),
    
    # 1. Página Antiga (Tabela Simples)
    path('estoque/', views.lista_estoque, name='lista_estoque'),
    
    # 2. Página Nova (Gestão Avançada)
    path('estoque/gestao/', views.gestao_estoque, name='gestao_estoque'),
    
    # 3. Mapa de Ocupação (Canvas HTML5 - Sistema Novo)
    path('mapa-armazem/', views.lista_armazens, name='lista_armazens'),
    path('mapa-armazem/<int:armazem_numero>/', views.mapa_ocupacao_canvas, name='mapa_canvas'),
    
    # 4. Mapa de Ocupação (Legado - compatibilidade)
    # path('mapa-ocupacao/', views.mapa_ocupacao_legacy, name='mapa_ocupacao_legacy'), # Removido se não usado

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
    path('importar-estoque/', views.importar_estoque, name='importar_estoque'),
    path('aprovar-importacao/', views.aprovar_importacao, name='aprovar_importacao'),
    path('exportar-excel/', views.exportar_excel, name='exportar_estoque_excel'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_estoque_pdf'),
    
    # ============================================================================
    # DEBUG E MANUTENÇÃO
    # ============================================================================
    path('debug-estoque/', views.debug_estoque_completo, name='debug_estoque'),
    path('limpar-cache-importacao/', views.limpar_cache_importacao, name='limpar_cache_importacao'),
    path('lotes-para-remover/', views.lotes_para_remover, name='lotes_para_remover'),
    path('consolidar-duplicados/', views.consolidar_lotes_duplicados, name='consolidar_lotes_duplicados'),

    # ============================================================================
    # APIs PARA ESTOQUE (JSON)
    # ============================================================================
    path('api/buscar-dados-lote/', views.api_buscar_dados_lote, name='api_buscar_dados_lote'),
    path('api/autocomplete-entrada/', views.api_autocomplete_nova_entrada, name='api_autocomplete_entrada'),
    path('api/autocomplete-lotes/', views.api_autocomplete_nova_entrada, name='api_autocomplete_nova_entrada'),
    
    path('api/saldo/<int:id>/', views.api_saldo_lote, name='api_saldo_lote'),
    path('api/buscar-lotes/', views.api_buscar_lotes, name='api_buscar_lotes'),
    path('api/buscar-lote-completo/', views.api_buscar_lote_completo, name='api_buscar_lote_completo'),
    path('api/verificar-lote/', views.api_verificar_lote, name='api_verificar_lote'),
    path('api/estoque-resumo/', views.api_estoque_resumo, name='api_estoque_resumo'),
    path('api/ultimas-movimentacoes/', views.api_ultimas_movimentacoes, name='api_ultimas_movimentacoes'),
    path('api/itens-empenhos/', views.api_itens_empenhos, name='api_itens_empenhos'),
    

    path('api/buscar-produto/', views.api_buscar_produto, name='api_buscar_produto'),
    # ============================================================================
    # APIs PARA MAPA (Canvas HTML5 - Sistema Novo)
    # ============================================================================
    # 1. APIs para o sistema Canvas (principal)
   
    path('api/salvar-todos-elementos/', views.salvar_todos_elementos, name='salvar_todos_elementos'),
  
    path('api/verificar-estoque/<str:endereco>/', views.verificar_estoque_endereco, name='verificar_estoque_endereco'),
    path('api/status-enderecos/', views.api_status_enderecos, name='api_status_enderecos'),
    
    # 2. Importação/exportação do mapa
    path('api/exportar-mapa/<int:armazem_numero>/', views.exportar_mapa_json, name='exportar_mapa_json'),
    path('api/importar-mapa/<int:armazem_numero>/', views.importar_mapa_json, name='importar_mapa_json'),
    
    # 3. Gerenciamento de armazéns
    path('api/criar-armazens-automaticos/', views.criar_armazens_automaticos, name='criar_armazens_automaticos'),
    
    # 4. Armazém e editor
    path('armazem/novo/', views.criar_armazem, name='criar_armazem'),
    

# Caso alguém acesse sem número, manda para o armazém 1 por padrão:
    path('editor-mapa/', views.editor_avancado, {'armazem_numero': 1}, name='editor_avancado_default'),
       
       
       
   # No seu urls.py
    path('api/estoque/<int:id>/detalhes/', views.detalhes_estoque_api, name='detalhes_estoque_api'),    
    # Exemplo no urls.py
    path('mapa-armazem/<int:armazem_numero>/', views.mapa_ocupacao_canvas, name='mapa_canvas'),
    path('editor-mapa/<int:armazem_numero>/', views.editor_avancado, name='editor_avancado'),
    path('api/salvar-mapa-completo/', views.salvar_todos_elementos, name='salvar_todos_elementos'),
    
    path('armazem/editar-config/<int:armazem_id>/', views.editar_config_armazem, name='editar_config_armazem'),

    
]

# ============================================================================
# CONFIGURAÇÃO DE ARQUIVOS ESTÁTICOS E MÍDIA (APENAS EM DESENVOLVIMENTO)
# ============================================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)