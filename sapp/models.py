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
    """Configuração geral do dashboard"""
    TIPO_GRAFICO_CHOICES = [
        ('bar', 'Barras Verticais'),
        ('bar_horizontal', 'Barras Horizontais'),
        ('pie', 'Pizza'),
        ('doughnut', 'Rosca'),
        ('line', 'Linha'),
        ('area', 'Área'),
        ('radar', 'Radar'),
        ('polar', 'Polar'),
        ('scatter', 'Dispersão'),
        ('bubble', 'Bolhas'),
    ]
    
    AGRUPAMENTO_CHOICES = [
        ('cultivar', 'Cultivar'),
        ('peneira', 'Peneira'),
        ('especie', 'Espécie'),
        ('categoria', 'Categoria'),
        ('tratamento', 'Tratamento'),
        ('embalagem', 'Embalagem'),
        ('cliente', 'Cliente'),
        ('empresa', 'Empresa'),
        ('az', 'Armazém (AZ)'),
        ('endereco', 'Endereço'),
        ('lote_prefix', 'Prefixo do Lote'),
        ('lote_sufix', 'Sufixo do Lote'),
        ('lote_pattern', 'Padrão no Lote'),
        ('conferente', 'Conferente'),
        ('mes_entrada', 'Mês de Entrada'),
        ('trimestre', 'Trimestre'),
        ('semestre', 'Semestre'),
        ('ano', 'Ano'),
    ]
    
    METRICA_CHOICES = [
        ('saldo', 'Saldo (Quantidade)'),
        ('entrada', 'Total de Entradas'),
        ('saida', 'Total de Saídas'),
        ('peso_total', 'Peso Total (kg)'),
        ('qtd_lotes', 'Quantidade de Lotes'),
        ('media_peso', 'Média de Peso por Lote'),
        ('taxa_giro', 'Taxa de Giro'),
        ('dias_estoque', 'Dias em Estoque'),
    ]
    
    ORDENACAO_CHOICES = [
        ('valor_desc', 'Maior para Menor'),
        ('valor_asc', 'Menor para Maior'),
        ('nome_asc', 'Nome (A-Z)'),
        ('nome_desc', 'Nome (Z-A)'),
        ('data_desc', 'Mais Recente'),
        ('data_asc', 'Mais Antigo'),
    ]
    
    nome = models.CharField('Nome do Gráfico', max_length=100)
    descricao = models.TextField('Descrição', blank=True)
    ordem = models.IntegerField('Ordem de Exibição', default=0)
    ativo = models.BooleanField('Ativo', default=True)
    
    # Tipo e aparência
    tipo_grafico = models.CharField('Tipo de Gráfico', max_length=20, choices=TIPO_GRAFICO_CHOICES, default='bar')
    largura = models.IntegerField('Largura (colunas)', default=6, help_text='1-12 colunas do Bootstrap')
    altura = models.IntegerField('Altura (px)', default=400)
    titulo = models.CharField('Título', max_length=200, blank=True)
    cor_principal = models.CharField('Cor Principal', max_length=20, default='#198754')
    mostrar_legenda = models.BooleanField('Mostrar Legenda', default=True)
    mostrar_valores = models.BooleanField('Mostrar Valores', default=True)
    mostrar_percentual = models.BooleanField('Mostrar %', default=False)
    
    # Configuração dos dados
    agrupamento_principal = models.CharField('Agrupar por', max_length=30, choices=AGRUPAMENTO_CHOICES)
    agrupamento_secundario = models.CharField('Agrupar por (2º nível)', max_length=30, choices=AGRUPAMENTO_CHOICES, blank=True, null=True)
    metrica = models.CharField('Métrica', max_length=20, choices=METRICA_CHOICES, default='saldo')
    ordenacao = models.CharField('Ordenar por', max_length=20, choices=ORDENACAO_CHOICES, default='valor_desc')
    limite_itens = models.IntegerField('Limite de Itens', default=10, help_text='0 = sem limite')
    
    # Filtros (salvos como JSON)
    filtros_json = models.TextField('Filtros', blank=True, help_text='Configuração dos filtros em JSON')
    
    # Datas
    data_inicio = models.DateField('Data Início', null=True, blank=True)
    data_fim = models.DateField('Data Fim', null=True, blank=True)
    
    # Metadados
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = 'Configuração de Dashboard'
        verbose_name_plural = 'Configurações de Dashboards'
    
    def __str__(self):
        return f"{self.ordem}. {self.nome}"
    
    def get_filtros(self):
        """Retorna os filtros como dicionário"""
        if self.filtros_json:
            try:
                return json.loads(self.filtros_json)
            except:
                return {}
        return {}
    
    def set_filtros(self, filtros_dict):
        """Salva os filtros como JSON"""
        self.filtros_json = json.dumps(filtros_dict)
    
    def get_dados_grafico(self):
        """Método principal que busca os dados conforme a configuração"""
        from django.db.models import Sum, Count, Avg, Q, F, DecimalField
        from django.db.models.functions import TruncMonth, TruncYear, TruncQuarter
        from datetime import timedelta
        from decimal import Decimal
        
        # Query base
        queryset = Estoque.objects.all()
        
        # Aplicar filtros de data
        if self.data_inicio:
            queryset = queryset.filter(data_entrada__gte=self.data_inicio)
        if self.data_fim:
            queryset = queryset.filter(data_entrada__lte=self.data_fim)
        
        # Aplicar filtros personalizados do JSON
        filtros = self.get_filtros()
        for campo, valor in filtros.items():
            if valor and valor != 'todos':
                if campo == 'lote_contem':
                    queryset = queryset.filter(lote__icontains=valor)
                elif campo == 'cultivar':
                    queryset = queryset.filter(cultivar__id=valor)
                elif campo == 'peneira':
                    queryset = queryset.filter(peneira__id=valor)
                elif campo == 'especie':
                    queryset = queryset.filter(especie__id=valor)
                elif campo == 'cliente':
                    queryset = queryset.filter(cliente__icontains=valor)
                elif campo == 'az':
                    queryset = queryset.filter(az=valor)
                elif campo == 'saldo_min':
                    queryset = queryset.filter(saldo__gte=int(valor))
                elif campo == 'saldo_max':
                    queryset = queryset.filter(saldo__lte=int(valor))
        
        # Definir agrupamento
        agrupamentos = {
            'cultivar': 'cultivar__nome',
            'peneira': 'peneira__nome',
            'especie': 'especie__nome',
            'categoria': 'categoria__nome',
            'tratamento': 'tratamento__nome',
            'embalagem': 'embalagem',
            'cliente': 'cliente',
            'empresa': 'empresa',
            'az': 'az',
            'endereco': 'endereco',
            'lote_prefix': "SUBSTR(lote, 1, 4)",
            'lote_sufix': "SUBSTR(lote, -4)",
            'conferente': 'conferente__username',
            'mes_entrada': TruncMonth('data_entrada'),
            'trimestre': TruncQuarter('data_entrada'),
            'semestre': "CASE WHEN EXTRACT(month FROM data_entrada) <= 6 THEN '1º Semestre' ELSE '2º Semestre' END",
            'ano': TruncYear('data_entrada'),
        }
        
        # Definir métrica
        metricas = {
            'saldo': Sum('saldo'),
            'entrada': Sum('entrada'),
            'saida': Sum('saida'),
            'peso_total': Sum('peso_total'),
            'qtd_lotes': Count('id'),
            'media_peso': Avg('peso_unitario'),
        }
        
        agrupamento_field = agrupamentos.get(self.agrupamento_principal, 'cultivar__nome')
        metrica_field = metricas.get(self.metrica, Sum('saldo'))
        
        # Se for uma expressão SQL raw (como SUBSTR)
        if isinstance(agrupamento_field, str) and '(' in agrupamento_field:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT {agrupamento_field} as grupo, {metrica_field.field} as valor 
                    FROM sapp_estoque 
                    GROUP BY grupo
                    ORDER BY valor DESC
                """)
                resultados = cursor.fetchall()
            labels = [r[0] for r in resultados]
            valores = [float(r[1]) for r in resultados]
        else:
            # Query normal do Django
            resultados = queryset.values(agrupamento_field).annotate(
                valor=metrica_field
            ).order_by('-valor')
            
            labels = [item[agrupamento_field] or 'Não informado' for item in resultados]
            valores = [float(item['valor']) for item in resultados]
        
        # Aplicar limite
        if self.limite_itens > 0 and len(labels) > self.limite_itens:
            labels = labels[:self.limite_itens]
            valores = valores[:self.limite_itens]
        
        # Calcular percentuais se necessário
        percentuais = []
        if self.mostrar_percentual and sum(valores) > 0:
            total = sum(valores)
            percentuais = [(v / total * 100) for v in valores]
        
        return {
            'labels': labels,
            'valores': valores,
            'percentuais': percentuais,
            'total': sum(valores),
            'qtd_itens': len(labels)
        }