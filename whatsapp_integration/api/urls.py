from django.urls import path
from . import views

# O namespace aqui ajuda, mas como usamos include no principal, 
# a URL final será /integra/api/instances/
urlpatterns = [
    path('instances/', views.InstanceAPIView.as_view(), name='instance-list'),
    path('instances/<int:instance_id>/', views.InstanceDetailAPIView.as_view(), name='instance-detail'),
    path('instances/<int:instance_id>/connect/', views.ConnectionAPIView.as_view(), name='instance-connect'),
    path('instances/<int:instance_id>/disconnect/', views.ConnectionAPIView.as_view(), name='instance-disconnect'),
    path('instances/<int:instance_id>/status/', views.StatusAPIView.as_view(), name='instance-status'),
    # whatsapp_integration/api/urls.py (adicionar)

    # Configurações de IA
    path('ai/config/', views.AIConfigView.as_view(), name='ai-config'),
    path('ai/config/<int:config_id>/', views.AIConfigView.as_view(), name='ai-config-detail'),

    # Controle de conversas
    path('ai/conversations/', views.AIConversationsListView.as_view(), name='ai-conversations'),
    path('ai/conversations/<int:pk>/', views.AIConversationDetailView.as_view(), name='ai-conversation-detail'),
    path('ai/conversations/<int:pk>/pause/', views.AIPauseConversationView.as_view(), name='ai-pause-conversation'),
    path('ai/conversations/<int:pk>/close/', views.AICloseConversationView.as_view(), name='ai-close-conversation'),

    # Configurações por cliente
    path('ai/client-settings/', views.AIClientSettingsView.as_view(), name='ai-client-settings'),
    path('ai/client-settings/<int:client_id>/', views.AIClientSettingsView.as_view(), name='ai-client-settings-detail'),
    path('ai/client/<int:client_id>/ignore/', views.AIIgnoreClientView.as_view(), name='ai-ignore-client'),

    # Respostas rápidas
    path('ai/quick-replies/', views.AIQuickReplyView.as_view(), name='ai-quick-replies'),
    path('ai/quick-replies/<int:pk>/', views.AIQuickReplyView.as_view(), name='ai-quick-reply-detail'),

    # Controle geral
    path('ai/pause-all/', views.AIPauseAllView.as_view(), name='ai-pause-all'),
    path('ai/stats/', views.AIStatsView.as_view(), name='ai-stats'),

    # whatsapp_integration/api/urls.py
    path('ai/admin/revendas/', views.AIAdminRevendasView.as_view(), name='ai-admin-revendas'),
    
]