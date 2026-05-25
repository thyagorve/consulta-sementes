# almoxarifado/urls.py
from django.urls import path
from . import views

app_name = 'almoxarifado'

urlpatterns = [
    path('', views.lista_itens, name='lista_itens'),
    path('saidas/', views.saidas_list, name='saidas_list'),
    path('buscar/', views.buscar_itens_ajax, name='buscar_itens_ajax'),
    path('item/buscar-codigo/', views.buscar_por_codigo, name='buscar_por_codigo'),
    path('item/adicionar/', views.adicionar_item, name='adicionar_item'),
    path('item/<int:pk>/detalhe/', views.detalhe_item, name='detalhe_item'),
    path('item/<int:pk>/editar/', views.editar_item, name='editar_item'),
    path('item/<int:pk>/baixa/', views.dar_baixa, name='dar_baixa'),
    path('item/<int:pk>/excluir/', views.excluir_item, name='excluir_item'),
    path('importar-xml-nfe/', views.importar_xml_nfe, name='importar_xml_nfe'),
    
    # Carrinho
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('carrinho/adicionar/', views.adicionar_ao_carrinho, name='adicionar_carrinho'),
    path('carrinho/<int:pk>/remover/', views.remover_do_carrinho, name='remover_carrinho'),
    path('carrinho/finalizar/', views.finalizar_carrinho, name='finalizar_carrinho'),
    path('carrinho/limpar/', views.limpar_carrinho, name='limpar_carrinho'),
    
    # Excel
    path('exportar/', views.exportar_excel, name='exportar_excel'),
    path('importar/', views.importar_excel, name='importar_excel'),
    path('saidas/exportar/', views.exportar_saidas_excel, name='exportar_saidas_excel'),
    path('modelo/', views.baixar_modelo_excel, name='baixar_modelo_excel'),
    path('visualizar-xml-nfe/', views.visualizar_xml_nfe, name='visualizar_xml_nfe'),
    
    # ============================================
    # WHATSAPP API ENDPOINTS
    # ============================================
    path('api/config-whatsapp/', views.api_config_whatsapp, name='api_config_whatsapp'),
    path('api/listar-instancias/', views.api_listar_instancias, name='api_listar_instancias'),
    path('api/criar-instancia/', views.api_criar_instancia, name='api_criar_instancia'),
    path('api/qrcode-instancia/', views.api_qrcode_instancia, name='api_qrcode_instancia'),
    path('api/status-instancia/', views.api_status_instancia, name='api_status_instancia'),
    path('api/deletar-instancia/', views.api_deletar_instancia, name='api_deletar_instancia'),
    path('api/proxy-evolution/', views.api_proxy_evolution, name='api_proxy_evolution'),
    path('api/enviar-notificacao-agora/', views.api_enviar_notificacao_agora, name='api_enviar_notificacao_agora'),
    
]