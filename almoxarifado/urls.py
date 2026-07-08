from django.urls import path
from . import views

app_name = 'almoxarifado'

urlpatterns = [
    # Página principal
    path('', views.lista_itens, name='lista_itens'),
    path('buscar/', views.buscar_itens_ajax, name='buscar_itens'),
    path('item/buscar-codigo/', views.buscar_por_codigo, name='buscar_por_codigo'),
    
    # CRUD Itens
    path('item/adicionar/', views.adicionar_item, name='adicionar_item'),
    path('item/<int:pk>/editar/', views.editar_item, name='editar_item'),
    path('item/<int:pk>/detalhe/', views.detalhe_item, name='detalhe_item'),
    path('item/<int:pk>/baixa/', views.dar_baixa, name='dar_baixa'),
    path('item/<int:pk>/excluir/', views.excluir_item, name='excluir_item'),
    
    # Saídas
    path('saidas/', views.saidas_list, name='saidas_list'),
    path('saidas/exportar/', views.exportar_saidas_excel, name='exportar_saidas_excel'),
    
    # Carrinho
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('carrinho/adicionar/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/<int:pk>/remover/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('carrinho/limpar/', views.limpar_carrinho, name='limpar_carrinho'),
    path('carrinho/finalizar/', views.finalizar_carrinho, name='finalizar_carrinho'),
    
    # Exportação
    path('exportar/', views.exportar_excel, name='exportar_excel'),
    path('baixar-modelo/', views.baixar_modelo_excel, name='baixar_modelo_excel'),
    
    # WhatsApp Config
    path('api/config-whatsapp/', views.api_config_whatsapp, name='api_config_whatsapp'),
    path('api/listar-instancias/', views.api_listar_instancias, name='api_listar_instancias'),
    path('api/criar-instancia/', views.api_criar_instancia, name='api_criar_instancia'),
    path('api/qrcode-instancia/', views.api_qrcode_instancia, name='api_qrcode_instancia'),
    path('api/status-instancia/', views.api_status_instancia, name='api_status_instancia'),
    path('api/deletar-instancia/', views.api_deletar_instancia, name='api_deletar_instancia'),
    path('api/enviar-notificacao-agora/', views.api_enviar_notificacao_agora, name='api_enviar_notificacao_agora'),
    
    # Agendamentos
    path('api/agendamentos/', views.listar_agendamentos, name='listar_agendamentos'),
    path('api/agendamentos/criar/', views.criar_agendamento, name='criar_agendamento'),
    path('api/agendamentos/<int:agendamento_id>/deletar/', views.deletar_agendamento, name='deletar_agendamento'),
]