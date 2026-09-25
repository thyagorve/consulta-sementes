# urls.py - VERSÃO FINAL LIMPA
import sys
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.contrib.staticfiles.views import serve as staticfiles_serve

from clientes import views, views_backup
from clientes.views import (
    ManageInstanceView,
    register,
    configuracao_mensagens,
    remover_mensagem,
    EditarMensagemView,
    ApagarMensagemView,
    get_mensagem_cliente,
    logs_atividade,
    log_detalhe,
    limpar_logs,
    obter_avatar_whatsapp,
)

def admin_handler(request):
    """Handler para URLs do admin inexistentes"""
    return HttpResponse("Página de admin não encontrada", status=404)

urlpatterns = [
    # ==========================================
    # ADMIN
    # ==========================================
    path('admin/', admin.site.urls),
    path('admin/<path:extra>/', admin_handler),

    # ==========================================
    # AUTENTICAÇÃO
    # ==========================================
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login_alias'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', register, name='register'),
    path('send-whatsapp-code/', views.send_whatsapp_code, name='send_whatsapp_code'),
    path('verify-whatsapp-code/', views.verify_whatsapp_code, name='verify_whatsapp_code'),

    # ==========================================
    # DASHBOARD
    # ==========================================
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # ==========================================
    # WHATSAPP
    # ==========================================
    path('integra/', include(('whatsapp_integration.urls', 'integra'), namespace='integra')),
    # Alias legado preservado, mas com namespace próprio para não colidir com integra.
    path('whatsapp/', include(('whatsapp_integration.urls', 'integra'), namespace='integra_legacy')),

    # ==========================================
    # CLIENTES
    # ==========================================
    path('listar_clientes/', views.listar_clientes, name='listar_clientes'),
    path('cliente/<int:pk>/', views.detalhes_cliente, name='detalhes_cliente'),
    path('cliente/', views.cliente_view, name='cliente'),
    path('cadastrar_cliente/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('editar_cliente/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('excluir_cliente/<int:pk>/', views.excluir_cliente, name='excluir_cliente'),
    path('ativar_desativar_cliente/<int:cliente_id>/', views.ativar_desativar_cliente, name='ativar_desativar_cliente'),
    path('verificar-pagamento/<int:cliente_id>/', views.verificar_pagamento, name='verificar_pagamento'),
    path('gerar_novo_link/<int:cliente_id>/', views.gerar_novo_link, name='gerar_novo_link'),
    path('jogos/<uuid:link_uuid>/', views.jogos_do_dia, name='jogos_do_dia'),
    path('renovar-cliente/<int:pk>/', views.renovar_cliente, name='renovar_cliente'),
    path('alterar_saldo/', views.alterar_saldo, name='alterar_saldo'),
    path('get_valor_servico/', views.get_valor_servico, name='get_valor_servico'),

    # ==========================================
    # SERVIÇOS
    # ==========================================
    path('servicos/', views.listar_servicos, name='listar_servicos'),
    path('cadastrar_servico/', views.cadastrar_servico, name='cadastrar_servico'),
    path('editar_servico/<int:pk>/', views.editar_servico, name='editar_servico'),
    path('excluir_servico/<int:pk>/', views.excluir_servico, name='excluir_servico'),
    path('servico/<int:servico_id>/abastecer/', views.abastecer_estoque, name='abastecer_estoque'),
    path('servico/<int:servico_id>/integracao/', views.configurar_integracao_servico, name='configurar_integracao_servico'),
    path('get_custo_fifo/<int:plano_id>/', views.get_custo_fifo, name='get_custo_fifo'),
    path('servico/<int:servico_id>/integracao/testar/', views.api_integracao_testar, name='api_integracao_testar'),
    path('servico/<int:servico_id>/integracao/catalogo/', views.api_integracao_catalogo, name='api_integracao_catalogo'),
    path('testes-painel/', views.testes_painel, name='testes_painel'),
    path('testes-painel/<int:teste_id>/converter/', views.converter_teste_painel, name='converter_teste_painel'),

    # ==========================================
    # TAGS
    # ==========================================
    path('tags/', views.tags_page, name='tags_page'),
    path('tags/edit/<int:tag_id>/', views.edit_tag, name='edit_tag'),
    path('buscar-planos-ajax/', views.buscar_planos_ajax, name='buscar_planos_ajax'),
    path('buscar_tags/', views.buscar_tags, name='buscar_tags'),
    path('tags/delete/<int:tag_id>/', views.delete_tag, name='delete_tag'),
    path('api/buscar-tags/', views.buscar_tags_para_cliente, name='buscar_tags_cliente'),
    path('api/criar-tag/', views.criar_tag_ajax, name='criar_tag_ajax'),
    path('cliente/<int:cliente_id>/adicionar-tags/', views.adicionar_tag_cliente, name='adicionar_tag_cliente'),
    path('cliente/<int:cliente_id>/tags/', views.buscar_tags_do_cliente, name='buscar_tags_do_cliente'),

    # ==========================================
    # FINANCEIRO (NOVO MÓDULO ORGANIZADO)
    # ==========================================

    


    # ==========================================
    # CONFIGURAÇÕES E MENSAGENS
    # ==========================================
    path('configuracao/', views.configuracao_view, name='configuracao'),
    path('configuracao_mensagens/', configuracao_mensagens, name='configuracao_mensagens'),
    path('remover_mensagem/<int:mensagem_id>/', remover_mensagem, name='remover_mensagem'),
    path('editar_mensagem/<int:pk>/', EditarMensagemView.as_view(), name='editar_mensagem'),
    path('apagar_mensagem/<int:pk>/', ApagarMensagemView.as_view(), name='apagar_mensagem'),
    path('get_mensagem_cliente/<int:cliente_id>/', get_mensagem_cliente, name='get_mensagem_cliente'),
    path('mensagens/', views.historico_mensagens, name='mensagens'),
    path('detalhe_mensagem/<int:mensagem_id>/', views.detalhe_mensagem, name='detalhe_mensagem'),
    path('api/configuracao/', views.api_configuracao, name='api_configuracao'),

    # ==========================================
    # INSTÂNCIA EVOLUTION
    # ==========================================
    path('manage-instance/', ManageInstanceView.as_view(), name='manage_instance'),

    # ==========================================
    # IMPORTAÇÃO / EXPORTAÇÃO
    # ==========================================
    path('importar_usuarios/', views.importar_usuarios, name='importar_usuarios'),
    path('exportar_usuarios/', views.exportar_usuarios, name='exportar_usuarios'),

    # ==========================================
    # ATUALIZAÇÕES
    # ==========================================
    path('atualizacoes/', views.atualizacoes, name='atualizacoes'),
    path('atualizacoes/nova/', views.nova_atualizacao, name='nova_atualizacao'),

    # ==========================================
    # INDICAÇÕES
    # ==========================================
    path('api/buscar-clientes-indicacao/', views.buscar_clientes_para_indicacao, name='buscar_clientes_indicacao'),
    path('api/buscar-indicados/', views.buscar_clientes_para_indicacao, name='buscar_clientes_para_indicacao'),
    path('cliente/<int:cliente_id>/adicionar-indicacao/', views.adicionar_indicacao, name='adicionar_indicacao'),
    path('cliente/<int:cliente_id>/salvar-indicacao/', views.adicionar_indicacao, name='salvar_indicacao_legacy'),
    path('cliente/<int:cliente_id>/listar-indicacoes/', views.listar_indicacoes, name='listar_indicacoes'),
    path('cliente/<int:cliente_id>/indicacoes/', views.listar_indicacoes_cliente, name='listar_indicacoes_cliente'),
    path('indicacao/<int:indicacao_id>/remover/', views.remover_indicacao, name='remover_indicacao'),
    path('cliente/remover-indicacao/<int:indicacao_id>/', views.remover_indicacao, name='remover_indicacao_legacy'),
    path('api/configuracao-comissao/', views.api_configuracao_comissao, name='api_config_comissao'),



    # ==========================================
    # LOGS
    # ==========================================
    path('logs/', logs_atividade, name='logs_atividade'),
    path('logs/<int:log_id>/', log_detalhe, name='log_detalhe'),
    path('logs/limpar/', limpar_logs, name='limpar_logs'),
    path('logs/<int:log_id>/delete/', views.log_delete, name='log_delete'),

    # ==========================================
    # BACKUP
    # ==========================================
    path('backup/', views_backup.pagina_backup, name='pagina_backup'),
    path('backup/criar/', views_backup.criar_backup_agora, name='criar_backup_agora'),
    path('backup/baixar/<int:backup_id>/', views_backup.baixar_backup, name='baixar_backup'),
    path('backup/restaurar/', views_backup.restaurar_backup, name='restaurar_backup'),
    path('backup/excluir/<int:backup_id>/', views_backup.excluir_backup, name='excluir_backup'),
    path('backup/agendamento/', views_backup.salvar_agendamento, name='salvar_agendamento'),
    path('backup/testar-telegram/', views_backup.testar_telegram, name='testar_telegram'),

    # ==========================================
    # AVISOS
    # ==========================================
    path('avisos/', views.configurar_avisos, name='configurar_avisos'),
    path('avisos/salvar/', views.salvar_aviso, name='salvar_aviso'),
    path('avisos/editar/<int:aviso_id>/', views.editar_aviso, name='editar_aviso'),
    path('avisos/excluir/<int:aviso_id>/', views.excluir_aviso, name='excluir_aviso'),
    path('avisos/config/', views.salvar_config_avisos, name='salvar_config_avisos'),
    path('avisos/reordenar/', views.reordenar_avisos, name='reordenar_avisos'),
    path('api/avisos/ativos/', views.api_avisos_ativos, name='api_avisos_ativos'),
    path('api/avisos/marcar-visto/', views.marcar_aviso_visto, name='marcar_aviso_visto'),

    # ==========================================
    # AVATAR WHATSAPP
    # ==========================================
    path('obter-avatar-whatsapp/<str:numero>/', obter_avatar_whatsapp, name='obter_avatar_whatsapp'),

    # ==========================================
    # API PESQUISA
    # ==========================================
    path('api/pesquisar-clientes/', views.api_pesquisar_clientes, name='api_pesquisar_clientes'),
    path('buscar-clientes-ajax/', views.buscar_clientes_ajax, name='buscar_clientes_ajax'),

    path('tutoriais/', views.lista_tutoriais, name='lista_tutoriais'),
    path('tutoriais/novo/', views.novo_tutorial, name='novo_tutorial'),
    path('tutoriais/editar/<int:tutorial_id>/', views.editar_tutorial, name='editar_tutorial'),
    path('tutoriais/excluir/<int:tutorial_id>/', views.excluir_tutorial, name='excluir_tutorial'),
# ==========================================
    path('financeiro/', include('financeiro.urls')),


    path('send-recovery-code/', views.send_recovery_code, name='send_recovery_code'),
    path('verify-recovery-code/', views.verify_recovery_code, name='verify_recovery_code'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('check-username/', views.check_username, name='check_username'),

    path(
        "integracoes-playlist/",
        views.pagina_integracoes_playlist,
        name="pagina_integracoes_playlist",
    ),
    path(
        "integracoes-playlist/salvar-dispositivo/",
        views.salvar_integracao_playlist,
        name="salvar_integracao_playlist",
    ),
    path(
        "integracoes-playlist/configuracao/",
        views.salvar_configuracao_playlist,
        name="salvar_configuracao_playlist",
    ),
    path(
        "integracoes-playlist/trocar-dns-em-massa/",
        views.trocar_dns_em_massa,
        name="trocar_dns_em_massa",
    ),
    path(
        "integracoes-playlist/<int:integracao_id>/detalhes/",
        views.detalhes_integracao_playlist,
        name="detalhes_integracao_playlist",
    ),
    path(
        "integracoes-playlist/playlist/<int:playlist_id>/detalhes/",
        views.detalhes_playlist,
        name="detalhes_playlist",
    ),
    path(
        "integracoes-playlist/cliente/<int:cliente_id>/credenciais/",
        views.detalhes_cliente_playlist,
        name="detalhes_cliente_playlist",
    ),
    path(
        "integracoes-playlist/<int:integracao_id>/criar-playlist/",
        views.criar_playlist_local,
        name="criar_playlist_local",
    ),
    path(
        "integracoes-playlist/<int:integracao_id>/migrar-legada/",
        views.migrar_playlist_legada,
        name="migrar_playlist_legada",
    ),
    path(
        "integracoes-playlist/<int:integracao_id>/historico/",
        views.historico_integracao_playlist,
        name="historico_integracao_playlist",
    ),
    path(
        "integracoes-playlist/playlist/<int:playlist_id>/subir/",
        views.subir_playlist,
        name="subir_playlist",
    ),
    path(
        "integracoes-playlist/playlist/<int:playlist_id>/atualizar/",
        views.atualizar_playlist_remota,
        name="atualizar_playlist_remota",
    ),
    path(
        "integracoes-playlist/playlist/<int:playlist_id>/editar/",
        views.editar_playlist,
        name="editar_playlist",
    ),
    path(
        "integracoes-playlist/playlist/<int:playlist_id>/excluir/",
        views.excluir_playlist,
        name="excluir_playlist",
    ),
    path(
        "integracoes-playlist/<int:integracao_id>/excluir-dispositivo/",
        views.excluir_dispositivo_playlist,
        name="excluir_dispositivo_playlist",
),

    path(
        "integracoes-playlist/playlist/<int:playlist_id>/substituir/",
        views.substituir_playlist_remota,
        name="substituir_playlist_remota",
    ),

    path(
        "integracoes-playlist/<int:integracao_id>/ibo/captcha/",
        views.gerar_captcha_ibo,
        name="gerar_captcha_ibo",
    ),
    path(
        "integracoes-playlist/<int:integracao_id>/ibo/autenticar/",
        views.autenticar_ibo_playlist,
        name="autenticar_ibo_playlist",
    ),



]

# ==========================================
# ARQUIVOS ESTÁTICOS / MÍDIA NO DESENVOLVIMENTO
# ==========================================
# `whitenoise.runserver_nostatic` desativa o handler padrão do runserver.
# Esta rota usa os finders do Django e, portanto, serve BASE_DIR/static e os
# diretórios static dos apps sem depender de `collectstatic` durante testes locais.
if 'runserver' in sys.argv:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', staticfiles_serve, {'insecure': True}),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


