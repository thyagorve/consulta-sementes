from django.db import models
from django.core.validators import MinValueValidator


class Departamento(models.TextChoices):
    ADMINISTRATIVO = 'ADM', 'Administrativo'
    PRODUCAO = 'PROD', 'Produção'
    MANUTENCAO = 'MAN', 'Manutenção'
    TI = 'TI', 'Tecnologia'
    FACILITES = 'FAC', 'Facilities'
    LABORATORIO = 'LAB', 'Laboratório'
    LOGISTICA = 'LOG', 'Logística'
    EPI = 'EPI', 'Seguranca'
    OUTROS = 'OUT', 'Outros'


class UnidadeMedida(models.TextChoices):
    UNIDADE = 'UN', 'UN'
    CAIXA = 'CX', 'CX'
    PACOTE = 'PCT', 'PCT'
    KILO = 'KG', 'KG'
    GRAMA = 'G', 'G'
    LITRO = 'L', 'L'
    MILILITRO = 'ML', 'ML'
    METRO = 'M', 'M'
    CENTIMETRO = 'CM', 'CM'
    PAR = 'PAR', 'Par'
    DUZIA = 'DZ', 'DZ'
    ROLO = 'RL', 'RL'
    FOLHA = 'FL', 'FL'


class Item(models.Model):
    # Identificação
    codigo = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name='Código'
    )

    tamanho = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name='Tamanho/Medida',
        help_text='Ex: P, M, G, GG, 10x15cm, Único'
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
    
    # Estoque
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
    foto = models.ImageField(
        upload_to='itens_fotos/', 
        blank=True, 
        null=True,
        verbose_name='Foto'
    )
    
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
        permissions = [
            ("pode_ver_almoxarifado", "Pode visualizar itens do almoxarifado"),
            ("pode_gerenciar_almoxarifado", "Pode gerenciar almoxarifado (CRUD)"),
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


class EntradaNotaFiscal(models.Model):
    chave_acesso = models.CharField(max_length=44, unique=True)
    numero_nota = models.CharField(max_length=20)
    fornecedor_nome = models.CharField(max_length=200)
    cnpj_fornecedor = models.CharField(max_length=18, blank=True, null=True)  # Permitir nulo
    data_emissao = models.DateField()
    data_recebimento = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    xml_arquivo = models.FileField(upload_to='nfe_xmls/', blank=True, null=True)

    def __str__(self):
        return f"NF {self.numero_nota} - {self.fornecedor_nome}"


class ItemEntrada(models.Model):
    nota_fiscal = models.ForeignKey(EntradaNotaFiscal, related_name='itens_nota', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='entradas_nota')  # Adicionado related_name
    quantidade_nota = models.DecimalField(max_digits=12, decimal_places=3)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.nota_fiscal.numero_nota} - {self.item.nome} - {self.quantidade_nota}"