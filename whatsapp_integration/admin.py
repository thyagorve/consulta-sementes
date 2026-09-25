from django.contrib import admin
from .models import UserInstance

@admin.register(UserInstance)
class UserInstanceAdmin(admin.ModelAdmin):
    list_display = [
        'instance_name', 
        'user', 
        'status_display', 
        'profile_name', 
        'last_check', 
        'is_active'
    ]
    
    list_filter = ['status', 'is_active', 'created_at', 'user']
    
    search_fields = ['instance_name', 'user__username', 'profile_name']
    
    readonly_fields = ['created_at', 'last_check', 'qr_generated_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'instance_name', 'instance_token', 'is_active')
        }),
        ('Status WhatsApp', {
            'fields': ('status', 'profile_name', 'owner_jid', 'profile_pic_url', 'last_check')
        }),
        ('QR Code', {
            'fields': ('qr_code_data', 'qr_generated_at'),
            'classes': ('collapse',)
        }),
        ('Datas', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        return obj.display_status
    status_display.short_description = 'Status'
    
    actions = ['activate_instances', 'deactivate_instances']
    
    def activate_instances(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} instância(s) ativada(s)")
    activate_instances.short_description = "Ativar instâncias selecionadas"
    
    def deactivate_instances(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} instância(s) desativada(s)")
    deactivate_instances.short_description = "Desativar instâncias selecionadas"
    
    





# whatsapp_integration/admin.py
from django.contrib import admin
from .models import MensagemMassa, HistoricoEnvioMassa

@admin.register(MensagemMassa)
class MensagemMassaAdmin(admin.ModelAdmin):
    list_display = ('id', 'remetente', 'status', 'total_destinatarios', 
                   'data_agendamento', 'data_criacao')
    list_filter = ('status', 'agendada', 'data_agendamento', 'data_criacao')
    search_fields = ('mensagem', 'remetente__username', 'remetente__email')
    readonly_fields = ('data_criacao', 'data_envio_inicio', 'data_envio_fim',
                      'enviados_com_sucesso', 'enviados_com_falha')
    filter_horizontal = ('tags_filtro',)
    date_hierarchy = 'data_agendamento'
    
    def has_add_permission(self, request):
        return False  # Mensagens só são criadas via interface do usuário


@admin.register(HistoricoEnvioMassa)
class HistoricoEnvioMassaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'whatsapp', 'status', 'mensagem_massa', 
                   'data_envio', 'data_confirmacao')
    list_filter = ('status', 'data_envio', 'mensagem_massa')
    search_fields = ('cliente__nome', 'cliente__whatsapp', 'whatsapp',
                    'mensagem_erro', 'message_id')
    readonly_fields = ('data_envio', 'data_confirmacao')
    date_hierarchy = 'data_envio'