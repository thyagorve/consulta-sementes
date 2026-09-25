# whatsapp_integration/urls.py
from django.urls import path, include
from . import views 
from . import webhook_handler  # NOVO import

app_name = "integra"

urlpatterns = [
    # ==========================================
    # PÁGINA PRINCIPAL
    # ==========================================
    path('', views.whatsapp_dashboard, name='whatsapp_dashboard'),
    path('whatsapp/', views.whatsapp_dashboard, name='whatsapp_dashboard_alias'),
    
    # ==========================================
    # WEBHOOKS (NOVO PRIMEIRO - Mais específico)
    # ==========================================
    
    # 🆕 NOVO - Webhook Unificado (USE ESTE no Evolution API)
    path('webhook/receiver/', webhook_handler.webhook_receiver, name='webhook_receiver'),
    
    # ⚠️ ANTIGOS - Manter para compatibilidade durante migração
    path('webhook/', views.evolution_direct_webhook_view, name='evolution_webhook'),
    path('webhook', views.evolution_direct_webhook_view, name='evolution_webhook_noslash'),
    path('webhook/<path:dummy>/', views.evolution_direct_webhook_view, name='evolution_webhook_any'),
    
    # ==========================================
    # APIs DE INSTÂNCIAS
    # ==========================================
    path('api/', include('whatsapp_integration.api.urls')),
    
    # ==========================================
    # ROTAS DE AVATAR
    # ==========================================
    path('api/user/<int:user_id>/avatar/', views.get_user_avatar, name='get_user_avatar'),
    path('api/user/<int:user_id>/avatar/refresh/', views.refresh_user_avatar, name='refresh_user_avatar'),
    path('api/user/<int:user_id>/avatar/status/', views.check_avatar_status, name='check_avatar_status'),
    path('api/user/<int:user_id>/avatar/clear/', views.clear_user_avatar, name='clear_user_avatar'),
    path('api/avatar/<str:phone_number>/', views.get_whatsapp_avatar, name='get_whatsapp_avatar'),
    path('api/avatars/batch-check/', views.batch_check_avatars, name='batch_check_avatars'),

    # ==========================================
    # ENVIO EM MASSA
    # ==========================================
    path('envio-massa/', views.enviar_mensagem_massa, name='enviar_mensagem_massa'),
    path('mensagens/', views.lista_mensagens_massa, name='lista_mensagens_massa'),
    path('mensagens/<int:mensagem_id>/', views.detalhe_mensagem_massa, name='detalhe_mensagem_massa'),
    path('mensagens/<int:mensagem_id>/cancelar/', views.cancelar_mensagem_massa, name='cancelar_mensagem_massa'),
    path('mensagens/<int:mensagem_id>/reenviar/', views.reenviar_mensagem_massa, name='reenviar_mensagem_massa'),
    path('mensagens/<int:mensagem_id>/duplicar/', views.duplicar_mensagem_massa, name='duplicar_mensagem_massa'),

    # ==========================================
    # APIs DE ENVIO EM MASSA
    # ==========================================
    # Compatibilidade com URLs antigas, sem duplicar os nomes canônicos.
    path('api/filter-clients/', views.api_filter_clients, name='legacy_api_filter_clients'),
    path('api/send-mass/', views.api_send_mass_message, name='legacy_api_send_mass_message'),
    path('api/save-draft/', views.api_save_mass_message, name='legacy_api_save_mass_message'),

    path('api/envio-massa/filtrar-clientes/', views.api_filter_clients, name='api_filter_clients'),
    path('api/envio-massa/salvar/', views.api_save_mass_message, name='api_save_mass_message'),
    path('api/envio-massa/enviar/', views.api_send_mass_message, name='api_send_mass_message'),
    path('api/envio-massa/status/<int:mensagem_id>/', views.api_mass_message_status, name='api_mass_message_status'),

    # ==========================================
    # HISTÓRICO
    # ==========================================
    path('historico/', views.historico_mensagens_view, name='historico'),
    path('historico/delete/<int:pk>/', views.remover_historico_mensagem_view, name='api_delete_historico'),
    path('historico/clear/', views.remover_todo_historico_view, name='api_clear_all_historico'),

    # ==========================================
    # IA MANAGER
    # ==========================================
    path('ia/gerenciar/', views.ai_manager_view, name='ai_manager'),
]