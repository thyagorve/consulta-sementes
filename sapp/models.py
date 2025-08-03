# sapp/models.py

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone # Importe o timezone

# Modelo de Produto (Cadastro)
class ProdutoCadastro(models.Model):
    codigo = models.CharField(max_length=100, unique=True, verbose_name="Código")
    descricao = models.CharField(max_length=255, default='', verbose_name="Descrição")
    cultivar = models.CharField(max_length=100, default='', blank=True, verbose_name="Cultivar")
    tecnologia = models.CharField(max_length=100, default='', blank=True, verbose_name="Tecnologia")
    tratamento = models.CharField(max_length=100, default='', blank=True, verbose_name="Tratamento")
    obtentor_mapa = models.CharField(max_length=100, default='', blank=True, verbose_name="Obtentor MAPA")
    marca = models.CharField(max_length=100, default='', blank=True, verbose_name="Marca")
    embalagem = models.CharField(max_length=100, default='', blank=True, verbose_name="Embalagem")
    tipo = models.CharField(max_length=100, default='', blank=True, verbose_name="Tipo")

    class Meta:
        verbose_name = "Produto (Cadastro)"
        verbose_name_plural = "Produtos (Cadastros)"

    def __str__(self):
        return f"{self.codigo} - {self.descricao}"

# Modelo de Lote (Estoque)
class EstoqueLote(models.Model):
    lote = models.CharField(max_length=100, verbose_name="Lote")
    codigo = models.CharField(max_length=100, verbose_name="Código do Produto")
    produto = models.CharField(max_length=255, default='', blank=True, verbose_name="Produto (Descrição)")
    qnte = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Qnte")
    pme = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="PME")
    volume = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Volume")
    filial = models.CharField(max_length=50, default='', blank=True, verbose_name="FILIAL")
    az = models.CharField(max_length=50, default='', blank=True, verbose_name="Az")
    rua = models.CharField(max_length=50, default='', blank=True, verbose_name="Rua")
    bloco = models.CharField(max_length=50, default='', blank=True, verbose_name="Bloco")
    quadra = models.CharField(max_length=50, default='', blank=True, verbose_name="Quadra")
    lote_endereco = models.CharField(max_length=50, default='', blank=True, verbose_name="Lote Endereço")
    categoria = models.CharField(max_length=100, default='', blank=True, verbose_name="Categoria")
    peneira = models.CharField(max_length=100, default='', blank=True, verbose_name="Peneira")
    embalagem = models.CharField(max_length=100, default='', blank=True, verbose_name="Embalagem")
    quantsc = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Quant SC")
    quantbg = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Quant Bg")
    variedade = models.CharField(max_length=100, default='', blank=True, verbose_name="Variedade")
    tipo = models.CharField(max_length=100, default='', blank=True, verbose_name="Tipo")
    dtfabricacao = models.DateField(null=True, blank=True, verbose_name="Dt.Fabricação") # Para datas, null=True é melhor que um default
    dtvalidade = models.DateField(null=True, blank=True, verbose_name="Dt.Validade") # Para datas, null=True é melhor que um default
    tecnologia = models.CharField(max_length=100, default='', blank=True, verbose_name="Tecnologia")
    tratamento = models.CharField(max_length=100, default='', blank=True, verbose_name="Tratamento")
    obtentora = models.CharField(max_length=100, default='', blank=True, verbose_name="Obtentora")
    umidade = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, verbose_name="Umidade")
    qntebloq = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Qnte Bloq.")
    volumebloq = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Volume Bloq.")
    um = models.CharField(max_length=50, default='', blank=True, verbose_name="Um")
    motivo_bloq = models.CharField(max_length=255, default='', blank=True, verbose_name="Motivo Bloq.")
    lassg = models.CharField(max_length=100, default='', blank=True, verbose_name="Lassg")
    cultura = models.CharField(max_length=100, default='', blank=True, verbose_name="Cultura")
    obs_bloqueio = models.TextField(default='', blank=True, verbose_name="Obs_bloqueio")
    numero_reserva = models.CharField(max_length=100, default='', blank=True, verbose_name="NUMERO_RESERVA")
    quantidade_reserva = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="QUANTIDADE_RESERVA")
    germinacao = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, verbose_name="GERMINACAO")
    vigor = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, verbose_name="VIGOR")
    class_lote = models.CharField(max_length=100, default='', blank=True, verbose_name="CLASS_LOTE")
    saldoliberado = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, verbose_name="Saldo_Liberado")
    chave = models.CharField(max_length=255, default='', blank=True, verbose_name="CHAVE")
    chave2 = models.CharField(max_length=255, default='', blank=True, verbose_name="Chave2")
    endereco = models.CharField(max_length=255, default='', blank=True, verbose_name="ENDEREÇO")

    class Meta:
        unique_together = ('lote', 'codigo')
        verbose_name = "Lote de Estoque"
        verbose_name_plural = "Lotes de Estoque"

    def __str__(self):
        return f"Lote: {self.lote} - Produto: {self.codigo}"

# Modelo para guardar as configurações de exibição
class ConfiguracaoExibicao(models.Model):
    campos_visiveis_produto = models.TextField(default='', blank=True, help_text="Campos do produto a serem exibidos na consulta, separados por vírgula.")
    campos_visiveis_lote = models.TextField(default='', blank=True, help_text="Campos do lote a serem exibidos na consulta, separados por vírgula.")

    def __str__(self):
        return "Configurações de Exibição da Consulta"

    class Meta:
        verbose_name_plural = "Configurações de Exibição"

# Modelo de Histórico de Consultas
class HistoricoConsulta(models.Model):
    termo_buscado = models.CharField(max_length=255)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    # AQUI ESTÁ A MUDANÇA PRINCIPAL PARA O PROBLEMA DO auto_now_add
    data_consulta = models.DateTimeField(default=timezone.now, verbose_name="Data da Consulta")
    resultados_encontrados = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Histórico de Consulta"
        verbose_name_plural = "Históricos de Consultas"
        ordering = ['-data_consulta']

    def __str__(self):
        return f"Consulta '{self.termo_buscado}' por {self.usuario or 'Anônimo'} em {self.data_consulta.strftime('%Y-%m-%d %H:%M')}"