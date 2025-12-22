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

class Estoque(models.Model):
    lote = models.CharField(max_length=50)
    produto = models.CharField(max_length=100, blank=True, null=True)
    cultivar = models.ForeignKey(Cultivar, on_delete=models.PROTECT)
    peneira = models.ForeignKey(Peneira, on_delete=models.PROTECT)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    tratamento = models.ForeignKey(Tratamento, on_delete=models.SET_NULL, null=True, blank=True)
    endereco = models.CharField(max_length=20)
    entrada = models.IntegerField(default=0)
    saida = models.IntegerField(default=0)
    saldo = models.IntegerField(default=0)
    conferente = models.ForeignKey(User, on_delete=models.PROTECT)
    origem_destino = models.CharField(max_length=255, blank=True, null=True)
    data_entrada = models.DateTimeField(auto_now_add=True)
    data_ultima_saida = models.DateTimeField(null=True, blank=True)
    data_ultima_movimentacao = models.DateTimeField(auto_now=True)
    especie = models.CharField(max_length=50, default='SOJA')
    empresa = models.CharField(max_length=100, blank=True, null=True)
    embalagem = models.CharField(max_length=10, choices=[('SC', 'Saco'), ('BAG', 'Big Bag')], default='BAG')
    peso_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    az = models.CharField(max_length=20, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    cliente = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
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
            self.peso_total = Decimal(self.saldo) * Decimal(self.peso_unitario)
        
        super().save(*args, **kwargs)
    
    def registrar_saida(self, quantidade, destino, usuario, observacao=''):
        """Método para registrar saída de forma controlada"""
        if quantidade <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        
        if quantidade > self.saldo:
            raise ValueError(f"Saldo insuficiente. Disponível: {self.saldo}")
        
        # Salvar estado anterior
        saldo_anterior = self.saldo
        
        # Atualizar
        self.saida += quantidade
        self.saldo = self.entrada - self.saida
        self.data_ultima_saida = timezone.now()
        
        # Recalcular peso
        if self.peso_unitario:
            self.peso_total = Decimal(self.saldo) * Decimal(self.peso_unitario)
        
        self.save()
        
        # Registrar histórico
        HistoricoMovimentacao.objects.create(
            estoque=self,
            usuario=usuario,
            tipo='Saída Controlada',
            descricao=(
                f"<b>SAÍDA SISTEMÁTICA</b><br>"
                f"<b>Quantidade:</b> {quantidade}<br>"
                f"<b>Destino:</b> {destino}<br>"
                f"<b>Saldo anterior:</b> {saldo_anterior}<br>"
                f"<b>Novo saldo:</b> {self.saldo}<br>"
                f"<b>Observação:</b> {observacao}"
            )
        )
        
        return self
    
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
    placa = models.CharField(max_length=20, blank=True, null=True) # Novo
    cliente = models.CharField(max_length=255, blank=True, null=True)
    ordem_entrega = models.CharField(max_length=50, blank=True, null=True) # Novo
    
    class Meta: 
        ordering = ['-data_hora']
    
    def save(self, *args, **kwargs):
        if self.estoque: 
            self.lote_ref = f"{self.estoque.lote}"
        super().save(*args, **kwargs)


# --- Fotos (Essencial para múltiplas fotos) ---
class FotoMovimentacao(models.Model):
    historico = models.ForeignKey(HistoricoMovimentacao, related_name='fotos', on_delete=models.CASCADE)
    arquivo = models.ImageField(upload_to='historico_fotos/%Y/%m/')
    data_upload = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto de {self.historico}"