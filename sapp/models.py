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
    
    def save(self, *args, **kwargs):
        self.saldo = self.entrada - self.saida
        self.status = 'ESGOTADO' if self.saldo <= 0 else 'ATIVO'
        if self.peso_unitario and self.saldo:
            try: self.peso_total = Decimal(str(self.saldo)) * Decimal(str(self.peso_unitario))
            except: self.peso_total = Decimal('0.00')
        super().save(*args, **kwargs)
    
    def __str__(self): return f"{self.lote} - {self.cultivar.nome} ({self.saldo} unidades)"

class HistoricoMovimentacao(models.Model):
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