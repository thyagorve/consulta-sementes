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