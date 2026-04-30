from django.db import models
from django.core.validators import MinValueValidator


class Departamento(models.TextChoices):
    ADMINISTRATIVO = 'ADM', 'Administrativo'
    PRODUCAO = 'PROD', 'Produção'
    MANUTENCAO = 'MAN', 'Manutenção'
    TI = 'TI', 'Tecnologia'
    MARKETING = 'fAC', 'Facilit'
    LOGISTICA = 'LOG', 'Logística'
    QUALIDADE = 'QUAL', 'Qualidade'
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
    # Código - opcional, se não informado gera automático
    codigo = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True, 
        null=True,
        verbose_name='Código'
    )
    
    nome = models.CharField(max_length=200, verbose_name='Nome do Item')
    descricao = models.TextField(blank=True, null=True, verbose_name='Descrição')
    
    # Departamento
    departamento = models.CharField(
        max_length=4,
        choices=Departamento.choices,
        default=Departamento.OUTROS,
        verbose_name='Departamento'
    )
    
    # Quantidade e unidade
    quantidade = models.IntegerField(
        default=0, 
        validators=[MinValueValidator(0)],
        verbose_name='Quantidade'
    )
    unidade = models.CharField(
        max_length=3,
        choices=UnidadeMedida.choices,
        default=UnidadeMedida.UNIDADE,
        verbose_name='Unidade de Medida'
    )
    
    # Localização
    localizacao = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name='Localização'
    )
    
    # Controle de estoque
    estoque_minimo = models.IntegerField(
        default=5,
        validators=[MinValueValidator(0)],
        verbose_name='Estoque Mínimo'
    )
    
    # Valores (opcionais)
    valor_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name='Valor Unitário (R$)'
    )
    
    # Fornecedor
    fornecedor = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        verbose_name='Fornecedor'
    )
    
    # Foto
    foto = models.ImageField(
        upload_to='itens_fotos/', 
        blank=True, 
        null=True,
        verbose_name='Foto'
    )
    
    # Datas
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    # Status
    ativo = models.BooleanField(default=True, verbose_name='Ativo')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Item'
        verbose_name_plural = 'Itens'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['departamento']),
            models.Index(fields=['ativo']),
        ]

    def __str__(self):
        return f"{self.codigo or 'S/N'} - {self.nome}"
    
    def save(self, *args, **kwargs):
        # Gera código automático se não informado
        if not self.codigo:
            self.codigo = self._gerar_codigo()
        super().save(*args, **kwargs)
    
    def _gerar_codigo(self):
        """Gera código único de 3 dígitos"""
        ultimo = Item.objects.all().order_by('-id').first()
        if ultimo and ultimo.codigo and ultimo.codigo.isdigit():
            proximo = int(ultimo.codigo) + 1
        else:
            proximo = 1
        
        codigo = str(proximo).zfill(3)
        
        # Garante que não existe duplicado
        while Item.objects.filter(codigo=codigo).exists():
            proximo += 1
            codigo = str(proximo).zfill(3)
        
        return codigo
    
    @property
    def status_estoque(self):
        """Retorna o status do estoque"""
        if self.quantidade == 0:
            return 'zerado'
        elif self.quantidade <= self.estoque_minimo:
            return 'baixo'
        elif self.quantidade <= self.estoque_minimo * 3:
            return 'medio'
        else:
            return 'alto'
    
    @property
    def valor_total(self):
        """Calcula valor total em estoque"""
        if self.valor_unitario:
            return self.quantidade * self.valor_unitario
        return None


class Saida(models.Model):
    item = models.ForeignKey(
        Item, 
        on_delete=models.CASCADE, 
        related_name='saidas',
        verbose_name='Item'
    )
    item_nome = models.CharField(max_length=200, verbose_name='Nome do Item')
    item_codigo = models.CharField(max_length=20, blank=True, null=True, verbose_name='Código')
    solicitante = models.CharField(max_length=200, verbose_name='Solicitante')
    departamento = models.CharField(
        max_length=4,
        choices=Departamento.choices,
        blank=True,
        null=True,
        verbose_name='Departamento'
    )
    quantidade = models.IntegerField(verbose_name='Quantidade')
    data = models.DateField(verbose_name='Data')
    hora = models.TimeField(verbose_name='Hora')
    observacao = models.TextField(blank=True, null=True, verbose_name='Observação')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Registrado em')

    class Meta:
        ordering = ['-data', '-hora']
        verbose_name = 'Saída'
        verbose_name_plural = 'Saídas'
        indexes = [
            models.Index(fields=['data']),
            models.Index(fields=['solicitante']),
        ]

    def __str__(self):
        return f"{self.solicitante} - {self.item_nome} - {self.quantidade} em {self.data}"