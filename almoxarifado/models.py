# Adicione no topo do arquivo
import re
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
    # ... (mantenha seu modelo Item existente)
    codigo = models.CharField(max_length=20, blank=True, null=True, verbose_name='Código')
    tamanho = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tamanho/Medida')
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    departamento = models.CharField(max_length=4, choices=Departamento.choices, default=Departamento.OUTROS)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    lote = models.CharField(max_length=100, blank=True, null=True)
    ca = models.CharField(max_length=100, blank=True, null=True)
    validade_ca = models.DateField(blank=True, null=True)
    quantidade = models.DecimalField(max_digits=12, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    unidade = models.CharField(max_length=3, choices=UnidadeMedida.choices, default=UnidadeMedida.UNIDADE)
    localizacao = models.CharField(max_length=100, blank=True, null=True)
    estoque_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=5, validators=[MinValueValidator(0)])
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fornecedor = models.CharField(max_length=200, blank=True, null=True)
    marca = models.CharField(max_length=100, blank=True, null=True)
    foto = models.ImageField(upload_to='itens_fotos/', blank=True, null=True)
    data_aquisicao = models.DateField(blank=True, null=True)
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


class ConfiguracaoWhatsApp(models.Model):
    # Configuração da API
    api_url = models.CharField(max_length=255, default='', blank=True, null=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    instance_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Números por departamento (formato JSON)
    numeros_por_departamento = models.JSONField(default=dict, blank=True, null=True)
    
    # Números padrão (caso o departamento não tenha específico)
    numeros_padrao = models.TextField(blank=True, null=True, help_text="Números padrão separados por vírgula")
    
    # Notificações
    notificar_estoque_baixo = models.BooleanField(default=True)
    notificar_estoque_zerado = models.BooleanField(default=True)
    notificar_reposicao = models.BooleanField(default=True)
    
    # ========== NOVOS CAMPOS DE AGENDAMENTO ==========
    tipo_envio = models.CharField(
        max_length=20, 
        default='tempo-real',
        choices=[
            ('tempo-real', '🚀 Tempo Real'),
            ('agendado', '📅 Agendado'),
            ('ambos', '🔄 Ambos'),
        ],
        verbose_name='Tipo de Envio'
    )
    horario_agendado = models.TimeField(default='08:00', verbose_name='Horário do Envio Agendado')
    dias_semana = models.JSONField(default=list, blank=True, null=True, verbose_name='Dias da Semana')
    notificar_baixo = models.BooleanField(default=True, verbose_name='Notificar Estoque Baixo')
    notificar_zerado = models.BooleanField(default=True, verbose_name='Notificar Estoque Zerado')
    notificar_reposicao = models.BooleanField(default=True, verbose_name='Notificar Reposição')
    repetir_notificacoes = models.BooleanField(default=False, verbose_name='Repetir Notificações')
    intervalo_repeticao = models.IntegerField(default=24, verbose_name='Intervalo de Repetição (horas)')
    departamentos_ativos = models.JSONField(default=list, blank=True, null=True, verbose_name='Departamentos Ativos')
    # Adicione no final dos campos
    ultima_notificacao_agendada = models.DateTimeField(blank=True, null=True, verbose_name='Última Notificação Agendada')
    
    # ========== TEMPLATE DE RESUMO ==========
    template_resumo = models.TextField(
        default="""📊 *RESUMO DIÁRIO*

📅 Data: {data}
🏢 Departamento: {departamento}

📦 *ESTOQUE BAIXO:* ({total_baixo})
{lista_baixo}

⚠️ *ITENS ZERADOS:* ({total_zerado})
{lista_zerado}

🔔 Este é um resumo automático do sistema de Almoxarifado.""",
        verbose_name='Template de Resumo'
    )
    
    # Templates individuais
    template_estoque_baixo = models.TextField(default="""🔴 *ESTOQUE BAIXO!*

📦 *Item:* {nome}
🏷️ *Código:* {codigo}
📍 *Localização:* {localizacao}
🏢 *Departamento:* {departamento}

📊 *Estoque atual:* {quantidade} {unidade}
⚠️ *Estoque mínimo:* {minimo} {unidade}

📌 *Sugestão de compra:* {sugestao} {unidade}""")

    template_estoque_zerado = models.TextField(default="""🔴 *ESTOQUE ZERADO!* 🚨

📦 *Item:* {nome}
🏷️ *Código:* {codigo}
📍 *Localização:* {localizacao}
🏢 *Departamento:* {departamento}

⚠️ *URGENTE - Necessário compra imediata!*""")

    template_reposicao = models.TextField(default="""✅ *ITEM REPOSTO!*

📦 *Item:* {nome}
🏷️ *Código:* {codigo}
📍 *Localização:* {localizacao}

📊 *Novo estoque:* {nova_quantidade} {unidade}
➕ *Quantidade adicionada:* {adicionado} {unidade}
📈 *Status:* {status}""")
    
    # Controle
    ativo = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuração WhatsApp'
        verbose_name_plural = 'Configurações WhatsApp'
    
    def __str__(self):
        return f"WhatsApp - {'Ativo' if self.ativo else 'Inativo'}"
    
    @classmethod
    def get_config(cls):
        config = cls.objects.first()
        if not config:
            config = cls.objects.create()
        return config
    
    def get_numeros_por_departamento(self, departamento):
        """Retorna números para um departamento específico"""
        if self.numeros_por_departamento and departamento in self.numeros_por_departamento:
            numeros = self.numeros_por_departamento[departamento]
            if isinstance(numeros, str):
                return [n.strip() for n in numeros.split(',') if n.strip()]
            return numeros
        return []
    
    def get_numeros_padrao_lista(self):
        """Retorna lista de números padrão"""
        if not self.numeros_padrao:
            return []
        return [n.strip() for n in self.numeros_padrao.split(',') if n.strip()]
    
    def get_numeros_destino(self, departamento=None):
        """Retorna números para um departamento ou os padrão"""
        if departamento:
            numeros_dept = self.get_numeros_por_departamento(departamento)
            if numeros_dept:
                return numeros_dept
        return self.get_numeros_padrao_lista()

class HistoricoNotificacaoAlmoxarifado(models.Model):
    TIPO_CHOICES = [
        ('baixo', 'Estoque Baixo'),
        ('zerado', 'Estoque Zerado'),
        ('reposicao', 'Reposição'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('enviado', 'Enviado'),
        ('erro', 'Erro'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='notificacoes_whatsapp')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    destinatario = models.CharField(max_length=50)
    mensagem = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    erro = models.TextField(blank=True, null=True)
    api_response = models.TextField(blank=True, null=True)
    enviado_em = models.DateTimeField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Histórico de Notificação'
        verbose_name_plural = 'Históricos de Notificações'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.item.nome} - {self.status}"


# ============================================
# OUTROS MODELOS (Saida, Carrinho, etc)
# ============================================

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
    cnpj_fornecedor = models.CharField(max_length=18, blank=True, null=True)
    data_emissao = models.DateField()
    data_recebimento = models.DateTimeField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    xml_arquivo = models.FileField(upload_to='nfe_xmls/', blank=True, null=True)

    def __str__(self):
        return f"NF {self.numero_nota} - {self.fornecedor_nome}"


class ItemEntrada(models.Model):
    nota_fiscal = models.ForeignKey(EntradaNotaFiscal, related_name='itens_nota', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='entradas_nota')
    quantidade_nota = models.DecimalField(max_digits=12, decimal_places=3)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.nota_fiscal.numero_nota} - {self.item.nome} - {self.quantidade_nota}"