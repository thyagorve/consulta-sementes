from django.db import models
from django.core.validators import MinValueValidator


class Departamento(models.TextChoices):
    ADMINISTRATIVO = 'ADM', 'Administrativo'
    PRODUCAO = 'PROD', 'Produção'
    MANUTENCAO = 'MAN', 'Manutenção'
    TI = 'TI', 'Tecnologia'
    MARKETING = 'MKT', 'Marketing'
    VENDAS = 'VEND', 'Vendas'
    RH = 'RH', 'Recursos Humanos'
    FINANCEIRO = 'FIN', 'Financeiro'
    JURIDICO = 'JUR', 'Jurídico'
    LOGISTICA = 'LOG', 'Logística'
    QUALIDADE = 'QUAL', 'Qualidade'
    PESQUISA = 'PESQ', 'Pesquisa'
    OUTROS = 'OUT', 'Outros'


class UnidadeMedida(models.TextChoices):
    UNIDADE = 'UN', 'Unidade'
    CAIXA = 'CX', 'Caixa'
    PACOTE = 'PCT', 'Pacote'
    KILO = 'KG', 'Quilograma'
    GRAMA = 'G', 'Grama'
    LITRO = 'L', 'Litro'
    MILILITRO = 'ML', 'Mililitro'
    METRO = 'M', 'Metro'
    CENTIMETRO = 'CM', 'Centímetro'
    PAR = 'PAR', 'Par'
    DUZIA = 'DZ', 'Dúzia'
    ROLO = 'RL', 'Rolo'
    FOLHA = 'FL', 'Folha'


class Item(models.Model):
    # Identificação
    codigo = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name='Código'
        # REMOVIDO: unique=True
    )
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    
    # Classificação
    departamento = models.CharField(max_length=4, choices=Departamento.choices, default=Departamento.OUTROS)
    categoria = models.CharField(max_length=100, blank=True, null=True, verbose_name='Categoria')
    
    # Certificação e Rastreabilidade
    lote = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nº do Lote')
    ca = models.CharField(max_length=100, blank=True, null=True, verbose_name='CA (Certificado de Aprovação)')
    validade_ca = models.DateField(blank=True, null=True, verbose_name='Validade do CA')
    
    # Estoque - AGORA DECIMAL
    quantidade = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name='Quantidade'
    )
    unidade = models.CharField(max_length=3, choices=UnidadeMedida.choices, default=UnidadeMedida.UNIDADE)
    localizacao = models.CharField(max_length=100, blank=True, null=True)
    estoque_minimo = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=5,
        validators=[MinValueValidator(0)]
    )
    
    # Valores
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fornecedor = models.CharField(max_length=200, blank=True, null=True)
    marca = models.CharField(max_length=100, blank=True, null=True, verbose_name='Marca/Fabricante')
    
    # Mídia
    foto = models.ImageField(upload_to='itens_fotos/', blank=True, null=True)
    
    # Datas e Status
    data_aquisicao = models.DateField(blank=True, null=True, verbose_name='Data de Aquisição')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Item'
        verbose_name_plural = 'Itens'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['departamento']),
            models.Index(fields=['lote']),
            models.Index(fields=['ca']),
        ]

    def __str__(self):
        return f"{self.codigo or 'S/N'} - {self.nome}"
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._gerar_codigo()
        super().save(*args, **kwargs)
    
    def _gerar_codigo(self):
        ultimo = Item.objects.all().order_by('-id').first()
        proximo = (int(ultimo.codigo) + 1) if (ultimo and ultimo.codigo and ultimo.codigo.isdigit()) else 1
        codigo = str(proximo).zfill(3)
        while Item.objects.filter(codigo=codigo).exists():
            proximo += 1
            codigo = str(proximo).zfill(3)
        return codigo
    
    @property
    def status_estoque(self):
        if self.quantidade <= 0:
            return 'zerado'
        elif self.quantidade <= self.estoque_minimo:
            return 'baixo'
        elif self.quantidade <= self.estoque_minimo * 3:
            return 'medio'
        return 'alto'
    
    @property
    def valor_total(self):
        if self.valor_unitario:
            return float(self.quantidade) * float(self.valor_unitario)
        return None


class Saida(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='saidas')
    item_nome = models.CharField(max_length=200)
    item_codigo = models.CharField(max_length=20, blank=True, null=True)
    solicitante = models.CharField(max_length=200)
    departamento = models.CharField(max_length=4, choices=Departamento.choices, blank=True, null=True)
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    data = models.DateField()
    hora = models.TimeField()
    observacao = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-hora']
        verbose_name = 'Saída'
        verbose_name_plural = 'Saídas'

    def __str__(self):
        return f"{self.solicitante} - {self.item_nome} - {self.quantidade}"


class CarrinhoSolicitacao(models.Model):
    """Carrinho para múltiplas solicitações"""
    usuario = models.CharField(max_length=200)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantidade = models.DecimalField(max_digits=12, decimal_places=3)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['usuario', 'item']
        verbose_name = 'Item no Carrinho'
        verbose_name_plural = 'Itens no Carrinho'

    def __str__(self):
        return f"{self.usuario} - {self.item.nome} x{self.quantidade}"