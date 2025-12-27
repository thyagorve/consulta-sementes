from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal, InvalidOperation

# --- Tabelas Auxiliares ---
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

# --- NOVO: Tabela de Espécie (Adicionado) ---
class Especie(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

# --- NOVO: Perfil para controlar Primeiro Acesso ---
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    primeiro_acesso = models.BooleanField(default=True, verbose_name="Deve mudar senha?")

    def __str__(self): return f"Perfil de {self.usuario.username}"

# Sinal para criar perfil automaticamente quando cria User
@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Se for superuser, não precisa mudar senha no início
        primeiro = False if instance.is_superuser else True
        PerfilUsuario.objects.create(usuario=instance, primeiro_acesso=primeiro)

# --- Configuração ---
class Configuracao(models.Model):
    ocultar_esgotados = models.BooleanField(default=False, verbose_name="Ocultar Lotes Esgotados")
    def save(self, *args, **kwargs):
        self.pk = 1
        super(Configuracao, self).save(*args, **kwargs)
    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

# --- Modelo Principal de Estoque ---
class Estoque(models.Model):
    lote = models.CharField(max_length=50)
    produto = models.CharField(max_length=100, blank=True, null=True, default='')
    
    # Chaves Estrangeiras (Dropdowns)
    cultivar = models.ForeignKey(Cultivar, on_delete=models.PROTECT)
    peneira = models.ForeignKey(Peneira, on_delete=models.PROTECT)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    tratamento = models.ForeignKey(Tratamento, on_delete=models.SET_NULL, null=True, blank=True)
    
    # ALTERADO: Agora Especie é uma ForeignKey para "puxar" da lista
    #especie_antiga = models.CharField(max_length=50, default='SOJA', blank=True, null=True)
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
    cliente = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        default='',
        verbose_name="Cliente/Dono do Bag"
    )
    status = models.CharField(max_length=20, 
        choices=[
            ('ATIVO', 'Ativo'),
            ('ESGOTADO', 'Esgotado'),
            ('INATIVO', 'Inativo'),
            ('BLOQUEADO', 'Bloqueado')
        ], default='ATIVO')
    
    def save(self, *args, **kwargs):
        # Calcular saldo automaticamente
        self.saldo = self.entrada - self.saida
        
        # Atualizar status baseado no saldo
        if self.saldo <= 0:
            self.status = 'ESGOTADO'
        else:
            self.status = 'ATIVO'
        
        # Calcular peso total
        if self.peso_unitario and self.saldo:
            try:
                self.peso_total = Decimal(str(self.saldo)) * Decimal(str(self.peso_unitario))
            except:
                self.peso_total = Decimal('0.00')
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.lote} - {self.cultivar.nome} ({self.saldo} unidades)"
    
class HistoricoMovimentacao(models.Model):
    estoque = models.ForeignKey(Estoque, on_delete=models.SET_NULL, related_name='historico', null=True, blank=True)
    lote_ref = models.CharField(max_length=100, default="--")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50) 
    descricao = models.TextField() # Armazena o HTML rico
    
    # NOVOS CAMPOS PARA EXPEDIÇÃO DETALHADA
    numero_carga = models.CharField(max_length=50, blank=True, null=True)
    motorista = models.CharField(max_length=100, blank=True, null=True)
    placa = models.CharField(max_length=20, blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    ordem_entrega = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta: 
        ordering = ['-data_hora']
    
    def save(self, *args, **kwargs):
        if self.estoque: 
            self.lote_ref = f"{self.estoque.lote}"
        super().save(*args, **kwargs)


# --- Fotos ---
class FotoMovimentacao(models.Model):
    historico = models.ForeignKey(HistoricoMovimentacao, related_name='fotos', on_delete=models.CASCADE)
    arquivo = models.ImageField(upload_to='historico_fotos/%Y/%m/')
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto de {self.historico}"
    
    
# --- Sistema de Empenho/Rascunho ---
class EmpenhoStatus(models.Model):
    """Status de um empenho (rascunho, pendente, confirmado, cancelado)"""
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True, null=True)
    
    def __str__(self): return self.nome

class Empenho(models.Model):
    """Registro de empenho (rascunho de movimentação)"""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    status = models.ForeignKey(EmpenhoStatus, on_delete=models.PROTECT, default=1)  # 1 = Rascunho
    tipo_movimentacao = models.CharField(max_length=20, choices=[
        ('EXPEDICAO', 'Expedição'),
        ('TRANSFERENCIA', 'Transferência'),
        ('EDICAO', 'Edição'),
        ('ENTRADA', 'Entrada'),
    ], default='EXPEDICAO')
    observacao = models.TextField(blank=True, null=True)
    
    # Campos para expedição
    numero_carga = models.CharField(max_length=50, blank=True, null=True)
    motorista = models.CharField(max_length=100, blank=True, null=True)
    placa = models.CharField(max_length=20, blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    ordem_entrega = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Empenho #{self.id} - {self.usuario.username} - {self.get_tipo_movimentacao_display()}"
    
    @property
    def total_itens(self):
        return self.itens.count()
    
    @property
    def saldo_afetado(self):
        return sum(item.quantidade for item in self.itens.all())

class ItemEmpenho(models.Model):
    """Itens de um empenho"""
    empenho = models.ForeignKey(Empenho, on_delete=models.CASCADE, related_name='itens')
    estoque = models.ForeignKey(Estoque, on_delete=models.CASCADE, related_name='empenhos')
    quantidade = models.IntegerField(default=0)  # Quantidade empenhada
    endereco_origem = models.CharField(max_length=20)  # Endereço original
    endereco_destino = models.CharField(max_length=20, blank=True, null=True)  # Para transferências
    observacao = models.CharField(max_length=255, blank=True, null=True)
    
    # Cópia dos dados do estoque no momento do empenho
    lote = models.CharField(max_length=50)
    cultivar = models.CharField(max_length=100)
    peneira = models.CharField(max_length=50)
    categoria = models.CharField(max_length=50)
    saldo_anterior = models.IntegerField(default=0)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data_criacao']
        unique_together = ['empenho', 'estoque']  # Evita duplicações no mesmo empenho
    
    def __str__(self):
        return f"{self.lote} - {self.quantidade} unidades"
    
    def save(self, *args, **kwargs):
        # Ao salvar, copia os dados atuais do estoque
        if self.estoque and not self.lote:
            self.lote = self.estoque.lote
            self.cultivar = self.estoque.cultivar.nome if self.estoque.cultivar else ''
            self.peneira = self.estoque.peneira.nome if self.estoque.peneira else ''
            self.categoria = self.estoque.categoria.nome if self.estoque.categoria else ''
            self.saldo_anterior = self.estoque.saldo
            self.endereco_origem = self.estoque.endereco
        super().save(*args, **kwargs)
    
    @property
    def saldo_disponivel(self):
        """Saldo disponível após o empenho"""
        return self.estoque.saldo - self.quantidade