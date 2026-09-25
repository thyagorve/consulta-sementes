# clientes/admin.py

from django.contrib import admin
from .models import CustomUser, Servico, RelatorioFinanceiro

@admin.register(CustomUser)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'username', 'tipo_usuario', 'data_vencimento', 'plano']
    list_filter = ['tipo_usuario', 'data_vencimento', 'plano']
    search_fields = ['first_name', 'username']

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'valor', 'cor', 'revenda']
    search_fields = ['nome']
    list_filter = ['cor', 'revenda']

@admin.register(RelatorioFinanceiro)
class RelatorioFinanceiroAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'valor_pago', 'valor_servico', 'valor_liquido', 'data_geracao']
    search_fields = ['cliente__username', 'servidor']
    list_filter = ['data_geracao']



# admin.py
from django.contrib import admin
from .models import VerificationCode

@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'created_at', 'expires_at', 'is_used', 'is_valid_status']
    list_filter = ['is_used', 'created_at']
    search_fields = ['code']
    readonly_fields = ['code', 'created_at']
    
    def is_valid_status(self, obj):
        return obj.is_valid()
    is_valid_status.boolean = True
    is_valid_status.short_description = 'Válido'

