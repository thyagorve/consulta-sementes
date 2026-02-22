from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal, InvalidOperation

# ============================================================================
# TABELAS AUXILIARES (Cadastros Básicos)
# ============================================================================

class Cultivar(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class Peneira(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class Tratamento(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class Especie(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

# ============================================================================
# PERFIL E CONFIGURAÇÃO
# ============================================================================

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    primeiro_acesso = models.BooleanField(default=True, verbose_name="Deve mudar senha?")
    def __str__(self): return f"Perfil de {self.usuario.username}"

@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        primeiro = False if instance.is_superuser else True
        PerfilUsuario.objects.create(usuario=instance, primeiro_acesso=primeiro)

class Configuracao(models.Model):
    ocultar_esgotados = models.BooleanField(default=False, verbose_name="Ocultar Lotes Esgotados")
    def save(self, *args, **kwargs):
        self.pk = 1
        super(Configuracao, self).save(*args, **kwargs)
    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

# ============================================================================
# ESTOQUE E MOVIMENTAÇÃO
# ============================================================================

class Estoque(models.Model):
    lote = models.CharField(max_length=50)
    produto = models.CharField(max_length=100, blank=True, null=True, default='')
    
    cultivar = models.ForeignKey(Cultivar, on_delete=models.PROTECT)
    peneira = models.ForeignKey(Peneira, on_delete=models.PROTECT)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    tratamento = models.ForeignKey(Tratamento, on_delete=models.SET_NULL, null=True, blank=True)
    especie = models.ForeignKey(Especie, on_delete=models.PROTECT, null=True, blank=True) 
    
    endereco = models.CharField(max_length=20)
    entrada = models.IntegerField(default=0)
    saida = models.IntegerField(default=0)
    saldo = models.IntegerField(default=0)
    conferente = models.ForeignKey(User, on_delete=models.PROTECT)
    origem_destino = models.CharField(max_length=255, blank=True, null=True, default='')
    data_entrada = models.DateTimeField(auto_now_add=True)
    data_ultima_saida = models.DateTimeField(null=True, blank=True)
    data_ultima_movimentacao = models.DateTimeField(auto_now=True)
    
    empresa = models.CharField(max_length=100, blank=True, null=True, default='')
    embalagem = models.CharField(max_length=10, choices=[('SC', 'Saco'), ('BAG', 'Big Bag')], default='BAG')
    peso_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    peso_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    az = models.CharField(max_length=20, blank=True, null=True, default='')
    observacao = models.TextField(blank=True, null=True, default='')
    cliente = models.CharField(max_length=255, blank=True, null=True, default='', verbose_name="Cliente/Dono do Bag")
    status = models.CharField(max_length=20, choices=[('ATIVO', 'Ativo'), ('ESGOTADO', 'Esgotado'), ('INATIVO', 'Inativo'), ('BLOQUEADO', 'Bloqueado')], default='ATIVO')
    
    STATUS_SISTEMICO_CHOICES = [
        ('ok', 'OK - Tudo certo (Verde)'),
        ('parcial', 'Parcial - Divergência (Amarelo)'),
        ('critico', 'Crítico - Sem saldo real (Vermelho)'),
    ]
    
    status_sistemico = models.CharField(
        max_length=20,
        choices=STATUS_SISTEMICO_CHOICES,
        default='critico',  # Começa como vermelho
        verbose_name='Status Sistêmico'
    )
    status_sistemico_alterado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_sistemico_alteracoes'
    )
    status_sistemico_alterado_em = models.DateTimeField(
        null=True,
        blank=True
    )

    def save(self, *args, **kwargs):
        self.saldo = self.entrada - self.saida
        self.status = 'ESGOTADO' if self.saldo <= 0 else 'ATIVO'
        if self.peso_unitario and self.saldo:
            try: self.peso_total = Decimal(str(self.saldo)) * Decimal(str(self.peso_unitario))
            except: self.peso_total = Decimal('0.00')
        super().save(*args, **kwargs)
    
    def __str__(self): return f"{self.lote} - {self.cultivar.nome} ({self.saldo} unidades)"

class HistoricoMovimentacao(models.Model):
    quantidade = models.IntegerField(default=0)
    estoque = models.ForeignKey(Estoque, on_delete=models.SET_NULL, related_name='historico', null=True, blank=True)
    lote_ref = models.CharField(max_length=100, default="--")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50) 
    descricao = models.TextField()
    numero_carga = models.CharField(max_length=50, blank=True, null=True)
    motorista = models.CharField(max_length=100, blank=True, null=True)
    placa = models.CharField(max_length=20, blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    ordem_entrega = models.CharField(max_length=50, blank=True, null=True)
    class Meta: ordering = ['-data_hora']
    def save(self, *args, **kwargs):
        if self.estoque: self.lote_ref = f"{self.estoque.lote}"
        super().save(*args, **kwargs)

class FotoMovimentacao(models.Model):
    historico = models.ForeignKey(HistoricoMovimentacao, related_name='fotos', on_delete=models.CASCADE)
    arquivo = models.ImageField(upload_to='historico_fotos/%Y/%m/')
    data_upload = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Foto de {self.historico}"

# ============================================================================
# MAPA E LAYOUT (NOVO SISTEMA)
# ============================================================================

class ArmazemLayout(models.Model):
    numero = models.IntegerField(unique=True, verbose_name="Número do Armazém")
    nome = models.CharField(max_length=100, default="")
    imagem_fundo = models.ImageField(upload_to='mapa_armazens/', null=True, blank=True)
    largura_canvas = models.IntegerField(default=1000)
    altura_canvas = models.IntegerField(default=600)
    ativo = models.BooleanField(default=True)
    class Meta:
        verbose_name = "Layout do Armazém"
        verbose_name_plural = "Layouts dos Armazéns"
    def __str__(self): return f"Armazém {self.numero} - {self.nome}"

class ElementoMapa(models.Model):
    TIPO_ELEMENTO_CHOICES = [('RETANGULO', 'Retângulo/Endereço'), ('LINHA', 'Linha'), ('TEXTO', 'Texto')]
    
    armazem = models.ForeignKey(ArmazemLayout, on_delete=models.CASCADE, related_name='elementos')
    tipo = models.CharField(max_length=20, choices=TIPO_ELEMENTO_CHOICES)
    
    # Geometria
    pos_x = models.IntegerField(default=0)
    pos_y = models.IntegerField(default=0)
    largura = models.IntegerField(default=100)
    altura = models.IntegerField(default=60)
    rotacao = models.IntegerField(default=0) # CAMPO ADICIONADO AQUI
    
    # Estilo
    cor_preenchimento = models.CharField(max_length=20, default='#CCCCCC')
    cor_borda = models.CharField(max_length=20, default='#000000')
    espessura_borda = models.IntegerField(default=2)
    
    # Texto
    conteudo_texto = models.TextField(blank=True, null=True)
    fonte_nome = models.CharField(max_length=100, default='Arial')
    fonte_tamanho = models.IntegerField(default=14)
    texto_negrito = models.BooleanField(default=False)
    texto_italico = models.BooleanField(default=False)
    texto_direcao = models.CharField(max_length=20, default='horizontal', choices=[('horizontal', 'Horizontal'), ('vertical', 'Vertical')])
    
    # Outros
    linha_tipo = models.CharField(max_length=20, default='solida', choices=[('solida', 'Sólida'), ('tracejada', 'Tracejada'), ('pontilhada', 'Pontilhada')])
    identificador = models.CharField(max_length=50, blank=True, null=True)
    ordem_z = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = "Elemento do Mapa"
        verbose_name_plural = "Elementos do Mapa"
        ordering = ['armazem', 'ordem_z']
    def __str__(self): return f"{self.get_tipo_display()} - {self.identificador or 'Sem ID'}"

# ============================================================================
# SISTEMA DE EMPENHO (Mantido)
# ============================================================================

class EmpenhoStatus(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True, null=True)
    def __str__(self): return self.nome

class Empenho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    status = models.ForeignKey(EmpenhoStatus, on_delete=models.PROTECT, default=1)
    tipo_movimentacao = models.CharField(max_length=20, choices=[('EXPEDICAO', 'Expedição'), ('TRANSFERENCIA', 'Transferência'), ('EDICAO', 'Edição'), ('ENTRADA', 'Entrada')], default='EXPEDICAO')
    observacao = models.TextField(blank=True, null=True)
    numero_carga = models.CharField(max_length=50, blank=True, null=True)
    motorista = models.CharField(max_length=100, blank=True, null=True)
    placa = models.CharField(max_length=20, blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    ordem_entrega = models.CharField(max_length=50, blank=True, null=True)
    class Meta: ordering = ['-data_criacao']
    def __str__(self): return f"Empenho #{self.id} - {self.usuario.username}"
    @property
    def total_itens(self): return self.itens.count()
    @property
    def saldo_afetado(self): return sum(item.quantidade for item in self.itens.all())

class ItemEmpenho(models.Model):
    empenho = models.ForeignKey(Empenho, on_delete=models.CASCADE, related_name='itens')
    estoque = models.ForeignKey(Estoque, on_delete=models.CASCADE, related_name='empenhos')
    quantidade = models.IntegerField(default=0)
    endereco_origem = models.CharField(max_length=20)
    endereco_destino = models.CharField(max_length=20, blank=True, null=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)
    lote = models.CharField(max_length=50)
    cultivar = models.CharField(max_length=100)
    peneira = models.CharField(max_length=50)
    categoria = models.CharField(max_length=50)
    saldo_anterior = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-data_criacao']; unique_together = ['empenho', 'estoque']

    def __str__(self): return f"{self.lote} - {self.quantidade} unidades"
    def save(self, *args, **kwargs):
        if self.estoque and not self.lote:
            self.lote = self.estoque.lote
            self.cultivar = self.estoque.cultivar.nome if self.estoque.cultivar else ''
            self.peneira = self.estoque.peneira.nome if self.estoque.peneira else ''
            self.categoria = self.estoque.categoria.nome if self.estoque.categoria else ''
            self.saldo_anterior = self.estoque.saldo
            self.endereco_origem = self.estoque.endereco
        super().save(*args, **kwargs)
    @property
    def saldo_disponivel(self): return self.estoque.saldo - self.quantidade







class Produto(models.Model):
    cultivar = models.ForeignKey(Cultivar, on_delete=models.PROTECT, verbose_name="Cultivar")
    tipo = models.CharField(max_length=50, verbose_name="Tipo", blank=True, null=True)
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código do Produto")
    descricao = models.TextField(verbose_name="Descrição")
    peneira = models.ForeignKey(Peneira, on_delete=models.PROTECT, verbose_name="Peneira", blank=True, null=True)
    empresa = models.CharField(max_length=100, verbose_name="Empresa", blank=True, null=True)
    especie = models.ForeignKey(Especie, on_delete=models.PROTECT, verbose_name="Espécie", blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name="Categoria", blank=True, null=True)
    tratamento = models.ForeignKey(Tratamento, on_delete=models.PROTECT, verbose_name="Tratamento", blank=True, null=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['cultivar__nome', 'codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.cultivar.nome}"
    
    def info_completa(self):
        info = []
        if self.tipo: info.append(f"Tipo: {self.tipo}")
        if self.peneira: info.append(f"Peneira: {self.peneira.nome}")
        if self.empresa: info.append(f"Empresa: {self.empresa}")
        if self.especie: info.append(f"Espécie: {self.especie.nome}")
        if self.categoria: info.append(f"Categoria: {self.categoria.nome}")
        if self.tratamento: info.append(f"Tratamento: {self.tratamento.nome}")
        return " | ".join(info)





from django.db import models
from django.contrib.auth.models import User
import json

class DashboardConfig(models.Model):
    """Configurações dos gráficos do dashboard"""
    
    TIPO_GRAFICO_CHOICES = [
        ('doughnut', 'Rosca (Doughnut)'),
        ('pie', 'Pizza (Pie)'),
        ('bar', 'Barras'),
        ('horizontalBar', 'Barras Horizontais'),
        ('line', 'Linha'),
        ('area', 'Área'),
    ]
    
    ORDEM_CHOICES = [
        ('valor_desc', 'Maior Valor'),
        ('valor_asc', 'Menor Valor'),
        ('nome_asc', 'Nome (A-Z)'),
        ('nome_desc', 'Nome (Z-A)'),
    ]
    
    PERIODO_CHOICES = [
        (7, 'Últimos 7 dias'),
        (15, 'Últimos 15 dias'),
        (30, 'Últimos 30 dias'),
        (90, 'Últimos 90 dias'),
    ]
    
    # Gráfico de Cultivares
    cultivar_tipo = models.CharField(max_length=20, choices=TIPO_GRAFICO_CHOICES, default='doughnut')
    cultivar_qtd = models.IntegerField(default=10)
    cultivar_ordem = models.CharField(max_length=20, choices=ORDEM_CHOICES, default='valor_desc')
    cultivar_zerados = models.BooleanField(default=False)
    cultivar_agrupar_outros = models.BooleanField(default=True)
    
    # Gráfico de Peneiras
    peneira_tipo = models.CharField(max_length=20, choices=TIPO_GRAFICO_CHOICES, default='pie')
    peneira_qtd = models.IntegerField(default=8)
    peneira_ordem = models.CharField(max_length=20, choices=ORDEM_CHOICES, default='valor_desc')
    
    # Gráfico de Armazéns
    armazem_tipo = models.CharField(max_length=20, choices=TIPO_GRAFICO_CHOICES, default='bar')
    armazem_ordem = models.CharField(max_length=20, choices=ORDEM_CHOICES, default='nome_asc')
    armazem_metrica = models.CharField(max_length=20, choices=[
        ('volume', 'Volume (SC)'),
        ('lotes', 'Quantidade de Lotes'),
        ('peso', 'Peso Total (kg)'),
    ], default='volume')
    
    # Gráfico de Tendência
    tendencia_periodo = models.IntegerField(choices=PERIODO_CHOICES, default=7)
    tendencia_saidas = models.BooleanField(default=True)
    tendencia_transferencias = models.BooleanField(default=False)
    tendencia_agrupamento = models.CharField(max_length=10, choices=[
        ('day', 'Por Dia'),
        ('week', 'Por Semana'),
        ('month', 'Por Mês'),
    ], default='day')
    
    # Configurações Gerais
    auto_refresh = models.IntegerField(default=0, help_text="Tempo em segundos (0 = desativado)")
    unidade_padrao = models.CharField(max_length=10, choices=[
        ('sc', 'Sacas (SC)'),
        ('bags', 'Bags'),
        ('kg', 'Quilogramas (kg)'),
    ], default='sc')
    
    tema_cores = models.CharField(max_length=20, choices=[
        ('default', 'Padrão (Verde)'),
        ('modern', 'Moderno (Azul)'),
        ('pastel', 'Pastel'),
        ('dark', 'Escuro'),
    ], default='default')
    
    mostrar_legendas = models.BooleanField(default=True)
    mostrar_percentuais = models.BooleanField(default=True)
    
    # Filtros Rápidos
    filtro_cultivar = models.BooleanField(default=True)
    filtro_peneira = models.BooleanField(default=True)
    filtro_armazem = models.BooleanField(default=True)
    filtro_periodo = models.BooleanField(default=True)
    
    # Layout dos gráficos (posições e tamanhos)
    layout_config = models.TextField(default='{}', help_text="Configuração de layout em JSON")
    
    # Metadados
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dashboard_configs')
    
    class Meta:
        verbose_name = "Configuração do Dashboard"
        verbose_name_plural = "Configurações do Dashboard"
        unique_together = ['criado_por']  # Garante apenas uma config por usuário

    def __str__(self):
        return f"Dashboard Config - {self.criado_em.strftime('%d/%m/%Y %H:%M')}"
    
    def get_layout_config(self):
        try:
            return json.loads(self.layout_config)
        except:
            return {}
    
    def set_layout_config(self, config_dict):
        self.layout_config = json.dumps(config_dict)


class DashboardFiltroSalvo(models.Model):
    """Filtros salvos pelos usuários"""
    
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    filtros = models.TextField(help_text="Filtros em JSON")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filtros_salvos')
    compartilhado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Filtro Salvo"
        verbose_name_plural = "Filtros Salvos"
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.nome} - {self.usuario.username}"
    
    def get_filtros(self):
        try:
            return json.loads(self.filtros)
        except:
            return {}


class DashboardWidget(models.Model):
    """Widgets personalizados para o dashboard"""
    
    TIPO_WIDGET_CHOICES = [
        ('grafico', 'Gráfico'),
        ('tabela', 'Tabela'),
        ('kpi', 'Indicador KPI'),
        ('lista', 'Lista'),
    ]
    
    ORIGEM_DADOS_CHOICES = [
        ('cultivares', 'Top Cultivares'),
        ('peneiras', 'Distribuição por Peneira'),
        ('armazens', 'Ocupação por Armazém'),
        ('tendencia', 'Tendência de Movimentação'),
        ('estoque_resumo', 'Resumo do Estoque'),
        ('ultimas_mov', 'Últimas Movimentações'),
        ('clientes_top', 'Top Clientes'),
        ('produtos_top', 'Top Produtos'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_WIDGET_CHOICES)
    origem_dados = models.CharField(max_length=30, choices=ORIGEM_DADOS_CHOICES)
    
    # Configurações
    titulo = models.CharField(max_length=200, blank=True)
    subtitulo = models.CharField(max_length=200, blank=True)
    
    # Posição e tamanho
    pos_x = models.IntegerField(default=0)
    pos_y = models.IntegerField(default=0)
    largura = models.IntegerField(default=6)
    altura = models.IntegerField(default=4)
    
    # Configurações específicas
    config = models.TextField(default='{}', help_text="Configurações específicas do widget em JSON")
    
    # Visibilidade
    ativo = models.BooleanField(default=True)
    visivel_para_todos = models.BooleanField(default=False)
    usuarios_permitidos = models.ManyToManyField(User, blank=True, related_name='widgets_permitidos')
    
    # Ordem
    ordem = models.IntegerField(default=0)
    
    # Metadados
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='widgets_criados')
    
    class Meta:
        verbose_name = "Widget do Dashboard"
        verbose_name_plural = "Widgets do Dashboard"
        ordering = ['ordem', 'pos_y', 'pos_x']
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"
    
    def get_config(self):
        try:
            return json.loads(self.config)
        except:
            return {}