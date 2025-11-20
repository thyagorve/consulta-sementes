from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

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

# --- Estoque ---
class Estoque(models.Model):
    EMBALAGEM_CHOICES = [('BAG', 'Big Bag'), ('SC', 'Saco')]

    lote = models.CharField(max_length=50)
    cultivar = models.ForeignKey(Cultivar, on_delete=models.PROTECT, verbose_name="Cultivar")
    peneira = models.ForeignKey(Peneira, on_delete=models.PROTECT, verbose_name="PN")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name="CAT")
    
    # --- MUDANÇA AQUI: Agora aponta para o Usuário do Django ---
    conferente = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Conferente")
    
    tratamento = models.ForeignKey(Tratamento, on_delete=models.PROTECT, verbose_name="Tratamento", null=True, blank=True)
    az = models.CharField(max_length=10, verbose_name="AZ", blank=True, null=True)
    endereco = models.CharField(max_length=50)
    entrada = models.IntegerField(default=0)
    saida = models.IntegerField(default=0)
    saldo = models.IntegerField(default=0, editable=False)
    origem_destino = models.CharField(max_length=100, verbose_name="Origem/Destino")
    data_entrada = models.DateField(default=timezone.now)
    especie = models.CharField(max_length=50, default="SOJA")
    empresa = models.CharField(max_length=50)
    embalagem = models.CharField(max_length=3, choices=EMBALAGEM_CHOICES)
    peso_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Peso (Kg)")
    lote_anterior = models.CharField(max_length=50, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação") 
    peso_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.saldo = self.entrada - self.saida
        self.peso_total = self.saldo * self.peso_unitario
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.lote}"

class HistoricoMovimentacao(models.Model):
    estoque = models.ForeignKey(Estoque, on_delete=models.SET_NULL, related_name='historico', null=True, blank=True)
    lote_ref = models.CharField(max_length=100, default="--")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50)
    descricao = models.TextField()
    
    class Meta: ordering = ['-data_hora']
    
    def save(self, *args, **kwargs):
        if self.estoque: self.lote_ref = f"{self.estoque.lote} ({self.estoque.endereco})"
        super().save(*args, **kwargs)