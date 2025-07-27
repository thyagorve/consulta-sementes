# sapp/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class ProdutoCadastro(models.Model):
    codigo = models.CharField(max_length=100, primary_key=True, verbose_name="Código")
    cultivar = models.CharField(max_length=200, blank=True, null=True, verbose_name="Cultivar")
    tecnologia = models.CharField(max_length=200, blank=True, null=True, verbose_name="Tecnologia")
    tratamento = models.CharField(max_length=200, blank=True, null=True, verbose_name="Tratamento")
    obtentor = models.CharField(max_length=200, blank=True, null=True, verbose_name="Obtentor")
    mapa = models.CharField(max_length=100, blank=True, null=True, verbose_name="MAPA")
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    embalagem = models.CharField(max_length=100, blank=True, null=True, verbose_name="Embalagem")
    tipo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")

    def __str__(self):
        return f"Cadastro {self.codigo} - {self.descricao or self.cultivar}"

class EstoqueLote(models.Model):
    # --- MUDANÇA PRINCIPAL: SEM FOREIGN KEY ---
    codigo = models.CharField(max_length=100, db_index=True, verbose_name="Código")
    lote = models.CharField(max_length=100, db_index=True, verbose_name="Lote")
    
    # Quantidades e Volumes
    qnte = models.FloatField(blank=True, null=True, verbose_name="Qnte")
    pme = models.FloatField(blank=True, null=True, verbose_name="PME")
    volume = models.FloatField(blank=True, null=True, verbose_name="Volume")
    quant_sc = models.FloatField(blank=True, null=True, verbose_name="Quant SC")
    quant_bg = models.FloatField(blank=True, null=True, verbose_name="Quant Bg")
    um = models.CharField(max_length=50, blank=True, null=True, verbose_name="Um")
    saldo_liberado = models.FloatField(blank=True, null=True, verbose_name="Saldo Liberado")

    # Localização
    filial = models.CharField(max_length=100, blank=True, null=True, verbose_name="Filial")
    az = models.CharField(max_length=50, blank=True, null=True, verbose_name="Az")
    rua = models.CharField(max_length=50, blank=True, null=True, verbose_name="Rua")
    bloco = models.CharField(max_length=50, blank=True, null=True, verbose_name="Bloco")
    quadra = models.CharField(max_length=50, blank=True, null=True, verbose_name="Quadra")
    endereco = models.CharField(max_length=255, blank=True, null=True, verbose_name="Endereço")

    # Descrições e Categorias
    produto_descricao_planilha = models.CharField(max_length=255, blank=True, null=True, verbose_name="Produto")
    categoria = models.CharField(max_length=100, blank=True, null=True, verbose_name="Categoria")
    peneira = models.CharField(max_length=100, blank=True, null=True, verbose_name="Peneira")
    embalagem = models.CharField(max_length=100, blank=True, null=True, verbose_name="Embalagem")
    variedade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Variedade")
    tipo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo")
    tecnologia = models.CharField(max_length=200, blank=True, null=True, verbose_name="Tecnologia")
    tratamento = models.CharField(max_length=200, blank=True, null=True, verbose_name="Tratamento")
    obtentora = models.CharField(max_length=200, blank=True, null=True, verbose_name="Obtentora")
    cultura = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cultura")

    # Datas e Qualidade
    data_fabricacao = models.DateField(blank=True, null=True, verbose_name="Dt.Fabricação")
    data_validade = models.DateField(blank=True, null=True, verbose_name="Dt.Validade")
    umidade = models.CharField(max_length=50, blank=True, null=True, verbose_name="Umidade")
    germinacao = models.IntegerField(blank=True, null=True, verbose_name="Germinação")
    vigor = models.IntegerField(blank=True, null=True, verbose_name="Vigor")
    class_lote = models.CharField(max_length=100, blank=True, null=True, verbose_name="Class Lote")

    # Bloqueio e Reserva
    qnte_bloq = models.FloatField(blank=True, null=True, verbose_name="Qnte Bloq")
    volume_bloq = models.FloatField(blank=True, null=True, verbose_name="Volume Bloq.")
    motivo_bloqueio = models.CharField(max_length=255, blank=True, null=True, verbose_name="Motivo Bloq.")
    obs_bloqueio = models.TextField(blank=True, null=True, verbose_name="Obs_bloqueio")
    numero_reserva = models.CharField(max_length=100, blank=True, null=True, verbose_name="Numero Reserva")
    quantidade_reserva = models.FloatField(blank=True, null=True, verbose_name="Quantidade Reserva")

    # Outros
    lassg = models.CharField(max_length=100, blank=True, null=True, verbose_name="Lassg")
    chave = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chave")
    chave2 = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chave2")

    class Meta:
        verbose_name = "Lote de Estoque"
        verbose_name_plural = "Lotes de Estoque"
        unique_together = ('lote', 'endereco', 'codigo')

    def __str__(self):
        return f"Lote {self.lote} (Cod: {self.codigo}) @ {self.endereco or 'N/A'}"

class ConfiguracaoExibicao(models.Model):
    nome = models.CharField(max_length=100, default="Configuração Padrão")
    campos_visiveis_produto = models.TextField(default="cultivar,tecnologia,tratamento,descricao")
    campos_visiveis_lote = models.TextField(default="lote,codigo,endereco,qnte,data_validade,saldo_liberado")

    def __str__(self): return self.nome
    def save(self, *args, **kwargs): self.pk = 1; super(ConfiguracaoExibicao, self).save(*args, **kwargs)

class HistoricoConsulta(models.Model):
    termo_buscado = models.CharField(max_length=255)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    data_hora = models.DateTimeField(default=timezone.now)
    resultados_encontrados = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-data_hora']; verbose_name = "Histórico de Consulta"; verbose_name_plural = "Históricos de Consulta"
    def __str__(self): return f"'{self.termo_buscado}' por {self.usuario.username if self.usuario else 'N/A'} em {self.data_hora.strftime('%d/%m/%Y %H:%M')}"