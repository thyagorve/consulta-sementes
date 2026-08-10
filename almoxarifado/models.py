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


# ============================================
# MODELOS DE NOTA FISCAL
# ============================================

class EntradaNotaFiscal(models.Model):
    """Registro de notas fiscais importadas"""
    chave_acesso = models.CharField(max_length=44, unique=True, verbose_name='Chave de Acesso')
    numero_nota = models.CharField(max_length=20, verbose_name='Número da Nota')
    fornecedor_nome = models.CharField(max_length=200, verbose_name='Fornecedor')
    cnpj_fornecedor = models.CharField(max_length=18, blank=True, null=True, verbose_name='CNPJ')
    data_emissao = models.DateField(blank=True, null=True, verbose_name='Data de Emissão')
    data_recebimento = models.DateTimeField(auto_now_add=True, verbose_name='Data de Recebimento')
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Valor Total')
    xml_arquivo = models.FileField(upload_to='nfe_xmls/', blank=True, null=True, verbose_name='XML da Nota')

    class Meta:
        verbose_name = 'Entrada de Nota Fiscal'
        verbose_name_plural = 'Entradas de Notas Fiscais'
        ordering = ['-data_recebimento']

    def __str__(self):
        return f"NF {self.numero_nota} - {self.fornecedor_nome}"


class ItemEntrada(models.Model):
    """Itens de uma nota fiscal importada"""
    nota_fiscal = models.ForeignKey(EntradaNotaFiscal, on_delete=models.CASCADE, related_name='itens_nota', verbose_name='Nota Fiscal')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='entradas_nota', verbose_name='Item')
    quantidade_nota = models.DecimalField(max_digits=12, decimal_places=3, verbose_name='Quantidade na Nota')
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Preço Unitário')

    class Meta:
        verbose_name = 'Item da Nota Fiscal'
        verbose_name_plural = 'Itens da Nota Fiscal'

    def __str__(self):
        return f"{self.nota_fiscal.numero_nota} - {self.item.nome} - {self.quantidade_nota}"


# ============================================
# MODELOS WHATSAPP
# ============================================

class ConfiguracaoWhatsApp(models.Model):
    api_url = models.CharField(max_length=255, default='', blank=True, null=True)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    instance_name = models.CharField(max_length=100, blank=True, null=True)
    
    numeros_por_departamento = models.JSONField(default=dict, blank=True, null=True)
    numeros_padrao = models.TextField(blank=True, null=True, help_text="Números padrão separados por vírgula")
    
    notificar_estoque_baixo = models.BooleanField(default=True)
    notificar_estoque_zerado = models.BooleanField(default=True)
    notificar_reposicao = models.BooleanField(default=True)
    
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
    
    notificar_baixo = models.BooleanField(default=True, verbose_name='Notificar Estoque Baixo')
    notificar_zerado = models.BooleanField(default=True, verbose_name='Notificar Estoque Zerado')
    notificar_reposicao = models.BooleanField(default=True, verbose_name='Notificar Reposição')
    repetir_notificacoes = models.BooleanField(default=False, verbose_name='Repetir Notificações')
    intervalo_repeticao = models.IntegerField(default=24, verbose_name='Intervalo de Repetição (horas)')
    departamentos_ativos = models.JSONField(default=list, blank=True, null=True, verbose_name='Departamentos Ativos')
    horario_agendado = models.TimeField(null=True, blank=True, default='08:00')
    dias_semana = models.JSONField(default=list, blank=True, null=True)
    ultima_verificacao = models.DateTimeField(blank=True, null=True)


    template_resumo = models.TextField(
        default="""📊 *RESUMO DIÁRIO DE ESTOQUE*

📅 Data: {data}
🏢 Departamento: {departamento}

📦 *ITENS COM ESTOQUE BAIXO:* ({total_baixo})
{lista_baixo}

⚠️ *ITENS ZERADOS:* ({total_zerado})
{lista_zerado}

🔔 Este é um resumo automático do sistema de Almoxarifado.""",
        verbose_name='Template de Resumo'
    )
    
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

⚠️ *URGENTE - Necessário compra imediata!""")

    template_reposicao = models.TextField(default="""✅ *ITEM REPOSTO!*

📦 *Item:* {nome}
🏷️ *Código:* {codigo}
📍 *Localização:* {localizacao}

📊 *Novo estoque:* {nova_quantidade} {unidade}
➕ *Quantidade adicionada:* {adicionado} {unidade}
📈 *Status:* {status}""")
    
    ativo = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now_add=True)
    
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
    
    def get_agendamentos_ativos(self):
        return self.agendamentos.filter(ativo=True)
    
    def get_numeros_por_departamento(self, departamento):
        if self.numeros_por_departamento and departamento in self.numeros_por_departamento:
            numeros = self.numeros_por_departamento[departamento]
            if isinstance(numeros, str):
                return [n.strip() for n in numeros.split(',') if n.strip()]
            return numeros
        return []
    
    def get_numeros_padrao_lista(self):
        if not self.numeros_padrao:
            return []
        return [n.strip() for n in self.numeros_padrao.split(',') if n.strip()]
    
    def get_numeros_destino(self, departamento=None):
        if departamento:
            numeros_dept = self.get_numeros_por_departamento(departamento)
            if numeros_dept:
                return numeros_dept
        return self.get_numeros_padrao_lista()


class AgendamentoNotificacao(models.Model):
    """Modelo para agendamentos múltiplos de notificações"""
    
    config = models.ForeignKey(
        ConfiguracaoWhatsApp, 
        on_delete=models.CASCADE, 
        related_name='agendamentos'
    )
    horario = models.TimeField(verbose_name='Horário')
    dias_semana = models.JSONField(
        default=list, 
        blank=True, 
        null=True,
        verbose_name='Dias da Semana (0=domingo a 6=sábado)'
    )
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    descricao = models.CharField(max_length=100, blank=True, null=True, verbose_name='Descrição')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Agendamento de Notificação'
        verbose_name_plural = 'Agendamentos de Notificações'
        ordering = ['horario']
    
    def __str__(self):
        if self.dias_semana:
            dias_map = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
            dias_str = ', '.join([dias_map[d] for d in self.dias_semana if 0 <= d <= 6])
        else:
            dias_str = 'Todos os dias'
        return f"{self.horario} - {dias_str} ({'Ativo' if self.ativo else 'Inativo'})"


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
# MODELOS DE SAÍDA E CARRINHO
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
    



class InstanciaWhatsApp(models.Model):
    """Modelo para armazenar instâncias criadas pelo sistema"""
    nome = models.CharField(max_length=100, unique=True, verbose_name='Nome da Instância')
    status = models.CharField(max_length=20, default='disconnected', verbose_name='Status')
    api_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Instância WhatsApp'
        verbose_name_plural = 'Instâncias WhatsApp'
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.nome} - {self.status}"




# ADICIONAR AO FINAL DE almoxarifado/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class DadosValidadeItem(models.Model):
    item = models.OneToOneField(
        'Item',
        on_delete=models.CASCADE,
        related_name='dados_validade',
    )
    data_fabricacao = models.DateField(null=True, blank=True)
    data_vencimento = models.DateField(null=True, blank=True, db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['data_vencimento', 'item__nome']

    @property
    def dias_para_vencer(self):
        if not self.data_vencimento:
            return None
        return (self.data_vencimento - timezone.localdate()).days

    @property
    def status_vencimento(self):
        dias = self.dias_para_vencer
        if dias is None:
            return 'sem_data'
        if dias < 0:
            return 'vencido'
        if dias <= 30:
            return 'proximo'
        return 'em_dia'

    def __str__(self):
        return f'{self.item} - {self.data_vencimento or "sem vencimento"}'


class ImportacaoInventario(models.Model):
    TIPO_CHOICES = [
        ('PLANILHA', 'Planilha'),
        ('NFE_XML', 'NF-e XML'),
    ]
    MODO_CHOICES = [
        ('COM_LOTE', 'Código + lote'),
        ('SEM_LOTE', 'Somente código'),
    ]
    STATUS_CHOICES = [
        ('PROCESSANDO', 'Processando'),
        ('PRONTA', 'Pronta'),
        ('APLICADA', 'Aplicada'),
        ('CANCELADA', 'Cancelada'),
        ('ERRO', 'Erro'),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    modo_comparacao = models.CharField(
        max_length=20,
        choices=MODO_CHOICES,
        default='COM_LOTE',
    )
    nome_arquivo = models.CharField(max_length=255, blank=True, default='')
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    aplicado_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PROCESSANDO',
    )
    total_linhas = models.PositiveIntegerField(default=0)
    resumo = models.JSONField(default=dict, blank=True)
    erro = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-criado_em']


class LinhaComparacaoInventario(models.Model):
    STATUS_CHOICES = [
        ('IGUAL', 'Sistema = arquivo'),
        ('SALDO_DIVERGENTE', 'Saldo divergente'),
        ('UNIDADE_DIVERGENTE', 'Unidade divergente'),
        ('DADOS_DIVERGENTES', 'Dados divergentes'),
        ('SO_SISTEMA', 'Somente no sistema'),
        ('SO_ARQUIVO', 'Somente no arquivo'),
        ('AMBIGUO', 'Ambíguo'),
    ]
    ACAO_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('MANTER_SISTEMA', 'Manter sistema'),
        ('USAR_ARQUIVO', 'Usar arquivo'),
        ('CRIAR_ITEM', 'Criar item'),
        ('IGNORAR', 'Ignorar'),
    ]

    importacao = models.ForeignKey(
        ImportacaoInventario,
        on_delete=models.CASCADE,
        related_name='linhas',
    )
    item = models.ForeignKey(
        'Item',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    chave = models.CharField(max_length=500, db_index=True)
    codigo = models.CharField(max_length=100, blank=True, default='')
    lote = models.CharField(max_length=200, blank=True, default='')
    nome_arquivo = models.CharField(max_length=500, blank=True, default='')
    quantidade_sistema = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    quantidade_arquivo = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    unidade_sistema = models.CharField(max_length=50, blank=True, default='')
    unidade_arquivo = models.CharField(max_length=50, blank=True, default='')
    dados_arquivo = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    acao = models.CharField(
        max_length=30,
        choices=ACAO_CHOICES,
        default='PENDENTE',
    )
    aplicado = models.BooleanField(default=False)
    mensagem = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['status', 'codigo', 'lote', 'id']


class RegraNotificacaoAlmoxarifado(models.Model):
    TIPO_CHOICES = [
        ('ESTOQUE_BAIXO', 'Estoque abaixo do mínimo'),
        ('ESTOQUE_ABAIXO_X', 'Estoque abaixo de X'),
        ('ESTOQUE_ZERADO', 'Estoque zerado'),
        ('ESTOQUE_REPOSTO', 'Estoque reposto'),
        ('VENCE_EM', 'Vencimento antecipado'),
        ('VENCE_HOJE', 'Vence hoje'),
        ('VENCIDO', 'Produto vencido'),
    ]

    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    ativo = models.BooleanField(default=True)
    quantidade_limite = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True
    )
    dias_antes_vencimento = models.JSONField(default=list, blank=True)
    departamentos = models.JSONField(default=list, blank=True)
    repetir = models.BooleanField(default=False)
    intervalo_repeticao_horas = models.PositiveIntegerField(default=24)
    template_mensagem = models.TextField(
        blank=True,
        default=(
            '🔔 *ALMOXARIFADO*\n'
            '{evento}\n\n'
            '📦 {nome}\n'
            '🔢 Código: {codigo}\n'
            '🏷️ Lote: {lote}\n'
            '📊 Saldo: {quantidade} {unidade}\n'
            '📅 Vencimento: {vencimento}\n'
            '⏳ Dias: {dias}\n'
        ),
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)


class EstadoNotificacaoItem(models.Model):
    item = models.OneToOneField(
        'Item',
        on_delete=models.CASCADE,
        related_name='estado_notificacao',
    )
    quantidade_anterior = models.DecimalField(
        max_digits=18, decimal_places=4, default=0
    )
    atualizado_em = models.DateTimeField(auto_now=True)


class DisparoRegraNotificacao(models.Model):
    regra = models.ForeignKey(
        RegraNotificacaoAlmoxarifado,
        on_delete=models.CASCADE,
        related_name='disparos',
    )
    item = models.ForeignKey(
        'Item',
        on_delete=models.CASCADE,
        related_name='disparos_regras',
    )
    chave_evento = models.CharField(max_length=255, db_index=True)
    destinatario = models.CharField(max_length=40, blank=True, default='')
    enviado_em = models.DateTimeField(auto_now_add=True)
    sucesso = models.BooleanField(default=False)
    resposta = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-enviado_em']
