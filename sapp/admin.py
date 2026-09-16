from django.contrib import admin
from .models import (
    Cultivar, Peneira, Categoria, Tratamento, Especie,
    Estoque, HistoricoMovimentacao, FotoMovimentacao,
    PerfilUsuario, Configuracao,
    ArmazemLayout, ElementoMapa,  # Novos modelos do mapa
    Empenho, ItemEmpenho, EmpenhoStatus
)

# --- Cadastros Básicos ---
admin.site.register(Cultivar)
admin.site.register(Peneira)
admin.site.register(Categoria)
admin.site.register(Tratamento)
admin.site.register(Especie)
admin.site.register(PerfilUsuario)
admin.site.register(Configuracao)

# --- Estoque e Histórico ---
class FotoInline(admin.TabularInline):
    model = FotoMovimentacao
    extra = 0

class HistoricoInline(admin.StackedInline):
    model = HistoricoMovimentacao
    extra = 0
    inlines = [FotoInline]

@admin.register(Estoque)
class EstoqueAdmin(admin.ModelAdmin):
    list_display = ('lote', 'produto', 'endereco', 'saldo', 'status')
    search_fields = ('lote', 'produto', 'endereco')
    list_filter = ('status', 'cultivar', 'categoria')
    # Historico é readonly aqui geralmente, mas pode deixar sem inline se preferir

@admin.register(HistoricoMovimentacao)
class HistoricoAdmin(admin.ModelAdmin):
    list_display = ('data_hora', 'tipo', 'lote_ref', 'usuario')
    inlines = [FotoInline]

# --- Novo Sistema de Mapa ---
class ElementoMapaInline(admin.TabularInline):
    model = ElementoMapa
    extra = 0
    fields = ('tipo', 'identificador', 'pos_x', 'pos_y', 'largura', 'altura', 'rotacao')

@admin.register(ArmazemLayout)
class ArmazemLayoutAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nome', 'ativo')
    inlines = [ElementoMapaInline]

@admin.register(ElementoMapa)
class ElementoMapaAdmin(admin.ModelAdmin):
    list_display = ('id', 'armazem', 'tipo', 'identificador', 'ordem_z')
    list_filter = ('armazem', 'tipo')
    search_fields = ('identificador', 'conteudo_texto')

# --- Empenho ---
class ItemEmpenhoInline(admin.TabularInline):
    model = ItemEmpenho
    extra = 0

@admin.register(Empenho)
class EmpenhoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'tipo_movimentacao', 'status', 'data_criacao')
    inlines = [ItemEmpenhoInline]

admin.site.register(EmpenhoStatus)



from django.contrib import admin
from django.utils.html import format_html
from .models import ConfiguracaoLogo

@admin.register(ConfiguracaoLogo)
class ConfiguracaoLogoAdmin(admin.ModelAdmin):
    list_display = ['id', 'preview_logo', 'nome_empresa', 'ativo', 'atualizado_em']
    list_editable = ['ativo']
    readonly_fields = ['preview_logo_detail', 'atualizado_em', 'atualizado_por']
    fieldsets = (
        ('Logo da Empresa', {
            'fields': ('logo', 'preview_logo_detail', 'nome_empresa')
        }),
        ('Status', {
            'fields': ('ativo', 'atualizado_em', 'atualizado_por')
        }),
    )
    
    def preview_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 40px;">', obj.logo.url)
        return "Sem logo"
    preview_logo.short_description = "Preview"
    
    def preview_logo_detail(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 100px; border: 1px solid #ccc; padding: 5px;">',
                obj.logo.url
            )
        return "Nenhuma logo cadastrada. Faça upload acima."
    preview_logo_detail.short_description = "Visualização da Logo"
    
    def save_model(self, request, obj, form, change):
        obj.atualizado_por = request.user
        super().save_model(request, obj, form, change)
    
    def has_delete_permission(self, request, obj=None):
        # Permite exclusão apenas para superusuários
        return request.user.is_superuser
# --- Auditoria offline / sincronização ---
from .models import SyncLog, SyncOperation, SyncConflict, LoteSyncState, LoteSyncEvento

@admin.register(SyncOperation)
class SyncOperationAdmin(admin.ModelAdmin):
    list_display = ('operacao_id', 'usuario', 'device_id', 'tipo', 'lote', 'status', 'recebido_em')
    list_filter = ('status', 'tipo', 'recebido_em')
    search_fields = ('operacao_id', 'device_id', 'lote', 'usuario__username')
    readonly_fields = ('operacao_id', 'recebido_em', 'processado_em', 'payload', 'resultado')

@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    list_display = ('id', 'lote', 'status', 'criado_em', 'resolvido_por', 'resolvido_em')
    list_filter = ('status', 'criado_em')
    search_fields = ('lote', 'operacao__operacao_id')
    readonly_fields = ('contexto_servidor', 'resolucao', 'criado_em', 'resolvido_em')

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'device_id', 'recebido_em')
    search_fields = ('device_id', 'usuario__username')
    readonly_fields = ('payload', 'aceitos', 'rejeitados', 'conflitos', 'recebido_em')

admin.site.register(LoteSyncState)
admin.site.register(LoteSyncEvento)
from .models import CargaAjusteLog

@admin.register(CargaAjusteLog)
class CargaAjusteLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'historico', 'usuario', 'criado_em')
    readonly_fields = ('historico', 'usuario', 'criado_em', 'antes', 'depois', 'motivo')
