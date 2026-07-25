from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.views.static import serve

app_name = 'sapp'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='sapp/registration/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('mudar-senha/', views.mudar_senha, name='mudar_senha'),
    path('', views.redirecionar_usuario, name='redirecionar'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard-data/', views.dashboard_data, name='dashboard_data'),   
    
    path('estoque/', views.lista_estoque, name='lista_estoque'),
    path('estoque/gestao/', views.gestao_estoque, name='gestao_estoque'),
    path('mapa-armazem/', views.lista_armazens, name='lista_armazens'),
    path('mapa-armazem/<int:armazem_numero>/', views.mapa_ocupacao_canvas, name='mapa_canvas'),
    path('estoque/nova-entrada/', views.nova_entrada, name='nova_entrada'),
    path('estoque/transferir/<int:id>/', views.transferir, name='transferir'),
    path('estoque/editar/<int:id>/', views.editar, name='editar'),
    path('estoque/excluir/<int:id>/', views.excluir_lote, name='excluir_lote'),
    path('estoque/registrar-saida/<int:id>/', views.registrar_saida, name='registrar_saida'),
    path('estoque/nova-saida/', views.nova_saida, name='nova_saida'),
    path('relatorio-saidas/', views.relatorio_saidas, name='relatorio_saidas'),
    path('api/estoque/estatisticas/', views.api_estoque_estatisticas, name='api_estoque_estatisticas'),
    path('api/estoque/opcoes-filtro/', views.api_opcoes_filtro, name='api_opcoes_filtro'),
    path('configuracoes/', views.configuracoes, name='configuracoes'),
    path('historico-geral/', views.historico_geral, name='historico_geral'),
    
    path('pagina-rascunho/', views.pagina_rascunho, name='pagina_rascunho'),
    path('exportar-excel/', views.exportar_excel, name='exportar_estoque_excel'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_estoque_pdf'),
    path('salvar-config-dashboard/', views.salvar_config_dashboard, name='salvar_config_dashboard'),
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
    path('editor-mapa/<int:armazem_numero>/', views.editor_avancado, name='editor_avancado'),
    path('armazem/editar-config/<int:armazem_id>/', views.editar_config_armazem, name='editar_config_armazem'),
    path('ficha-rastreabilidade/', views.ficha_rastreabilidade, name='ficha_rastreabilidade'),
    path('ficha-rastreabilidade/<int:estoque_id>/', views.ficha_rastreabilidade_por_id, name='ficha_rastreabilidade_id'),
    path('ficha-rastreabilidade/multipla/', views.ficha_rastreabilidade_multipla, name='ficha_rastreabilidade_multipla'),
    path('api/validar-endereco/', views.validar_endereco, name='validar_endereco'),
    path('api/buscar-origens/', views.buscar_origens, name='buscar_origens'),
    path('api/buscar-enderecos/', views.api_buscar_enderecos, name='api_buscar_enderecos'),
    path('api/listar-enderecos/', views.api_listar_enderecos, name='api_listar_enderecos'),
    path('marcar-ultimo-lote/<int:estoque_id>/', views.marcar_ultimo_lote_linha, name='marcar_ultimo_lote'),
    path('get-marcacoes-linha/<str:rua>/<str:ln>/', views.get_marcacoes_linha, name='get_marcacoes_linha'),   
    path('api/mapa-dados/<int:armazem_numero>/', views.api_mapa_dados, name='api_mapa_dados'),
    path('api/marcacoes-ultimo-lote/', views.api_marcacoes_ultimo_lote, name='api_marcacoes_ultimo_lote'),
    path('api/user-permissions/<int:user_id>/', views.api_user_permissions, name='api_user_permissions'),
    path('api/atualizar-status-sistemico/', views.api_atualizar_status_sistemico, name='api_atualizar_status_sistemico'),
    path('api/listar-status/', views.api_listar_status, name='api_listar_status'),
    path('api/criar-status/', views.api_criar_status, name='api_criar_status'),
    path('api/editar-status/<int:status_id>/', views.api_editar_status, name='api_editar_status'),
    path('api/excluir-status/<int:status_id>/', views.api_excluir_status, name='api_excluir_status'),
    path('api/estoque/opcoes-filtro/', views.opcoes_filtro_api, name='opcoes_filtro_api'),
    path('exportar-estoque-excel/', views.exportar_estoque_excel, name='exportar_estoque_excel'),
    # ADICIONAR
    path('api/solicitacoes/listar/', views.api_listar_solicitacoes, name='api_listar_solicitacoes'),




    # ADICIONAR no urlpatterns (após as URLs existentes)

# FASE 2 - Solicitações
    path('solicitacoes/', views.pagina_solicitacoes, name='pagina_solicitacoes'),
    path('solicitacoes/nova/', views.criar_solicitacao, name='criar_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/lotes-disponiveis/', 
        views.api_lotes_disponiveis_para_solicitacao, 
        name='api_lotes_disponiveis_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/empenhar/', 
        views.empenhar_na_solicitacao, 
        name='api_empenhar_solicitacao'),


    # ADICIONAR no urlpatterns

    # FASE 3 - Movimentação e Impressão
    path('api/solicitacoes/<int:solicitacao_id>/movimentar/', 
        views.api_movimentar_solicitacao, 
        name='api_movimentar_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/impressao/', 
        views.api_dados_impressao_solicitacao, 
        name='api_impressao_solicitacao'),


    # ADICIONAR no urlpatterns

    # FASE 4 - Atualização ao vivo, feed e som
    path('api/cards/versao/', views.api_versao_cards, name='api_versao_cards'),
    path('api/cards/atualizacoes/', views.api_atualizacoes_recentes, name='api_atualizacoes_recentes'),
    path('api/cards/html/', views.api_html_cards_atualizados, name='api_html_cards'),
    path('api/configuracao-atualizacao/', views.api_configuracao_atualizacao, name='api_config_atualizacao'),

    # ADICIONAR no urlpatterns

    # FASE 5 - Kanban e Workflow
    path('kanban/', views.pagina_kanban, name='pagina_kanban'),
    path('api/kanban/dados/', views.api_kanban_dados, name='api_kanban_dados'),
    path('api/solicitacoes/<int:solicitacao_id>/mover-kanban/', 
        views.api_mover_card_kanban, 
        name='api_mover_card_kanban'),
    path('api/workflow/config/', views.api_config_workflow, name='api_config_workflow'),
    path('configuracao-workflow/', views.pagina_config_workflow, name='pagina_config_workflow'),
    path('api/solicitacoes/<int:solicitacao_id>/remover-itens/', 
        views.api_remover_itens_solicitacao, 
        name='api_remover_itens_solicitacao'),

    path('api/solicitacoes/<int:solicitacao_id>/remover-item/<int:item_id>/', 
        views.api_remover_item_empenho, 
        name='api_remover_item_empenho'),

    path('api/solicitacoes/<int:solicitacao_id>/excluir/', 
        views.api_excluir_solicitacao, 
        name='api_excluir_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/movimentar/', views.api_movimentar_solicitacao, name='api_movimentar_solicitacao'),


    # Certifique-se que estas URLs existem:
    path('solicitacoes/', views.pagina_solicitacoes, name='pagina_solicitacoes'),
    path('solicitacoes/nova/', views.criar_solicitacao, name='criar_solicitacao'),
    path('api/solicitacoes/listar/', views.api_listar_solicitacoes, name='api_listar_solicitacoes'),
    path('api/solicitacoes/<int:solicitacao_id>/lotes-disponiveis/', views.api_lotes_disponiveis_para_solicitacao, name='api_lotes_disponiveis_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/empenhar/', views.empenhar_na_solicitacao, name='api_empenhar_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/remover-item/<int:item_id>/', views.api_remover_item_empenho, name='api_remover_item_empenho'),
    path('api/solicitacoes/<int:solicitacao_id>/movimentar/', views.api_movimentar_solicitacao, name='api_movimentar_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/impressao/', views.api_dados_impressao_solicitacao, name='api_impressao_solicitacao'),
    path('api/solicitacoes/<int:solicitacao_id>/excluir/', views.api_excluir_solicitacao, name='api_excluir_solicitacao'),
    path('api/workflow/config/', views.api_config_workflow, name='api_config_workflow'),
    path('api/cards/atualizacoes/', views.api_atualizacoes_recentes, name='api_atualizacoes_recentes'),


]

# ============================================================================
# CONFIGURAÇÃO DE ARQUIVOS ESTÁTICOS E MÍDIA
# ============================================================================
# Servir arquivos de mídia (uploads)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# Servir arquivos estáticos (sempre, para debugging)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Fallback: servir estáticos via Django se Nginx não estiver configurado
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]