from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db import models
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db import models
from datetime import datetime 
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date
import logging
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from django.conf import settings
from django.db import models



import logging 
logger = logging.getLogger(__name__) 



# clientes/models.py

class RelatorioFinanceiro(models.Model):
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2)
    valor_servico = models.DecimalField(max_digits=10, decimal_places=2)
    valor_liquido = models.DecimalField(max_digits=10, decimal_places=2)
    servidor = models.CharField(max_length=100, blank=True, null=True)
    data_geracao = models.DateTimeField(default=timezone.now)
    is_manual = models.BooleanField(default=False)
    
    # 🔴 NOVO: Controle de rodadas
    grupo_renovacao = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Grupo de Renovação"
    )
    numero_rodada = models.IntegerField(
        default=0,
        db_index=True,
        verbose_name="Número da Rodada",
        help_text="Identifica a rodada de renovação do grupo"
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['grupo_renovacao', 'numero_rodada']),
        ]


# clientes/models.py

class CustomUser(AbstractUser):
    TIPO_USUARIO_CHOICES = [
        ('cliente', 'Cliente'),
        ('revenda', 'Revenda'),
        ('admin', 'Admin'),
    ]

    tipo_usuario = models.CharField(max_length=10, choices=TIPO_USUARIO_CHOICES, default='cliente')
    nome = models.CharField(max_length=100, blank=True, null=True)
    
    # 🔴 NOVO: Login do serviço (IPTV) - NÃO é único, pode repetir
    login_externo = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Login do Serviço (IPTV)",
        help_text="Login usado para acessar o serviço. Pode ser compartilhado entre vários clientes."
    )

    data_vencimento = models.DateField(null=True, blank=True)
    plano = models.ForeignKey('Servico', on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes')
    valor_servico = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    valor_a_pagar = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField('Tag', related_name='users', blank=True)
    data_criacao = models.DateTimeField(default=timezone.now)
    dono = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinados')
    senha_leitura = models.CharField(max_length=128, null=True, blank=True, verbose_name="Senha do Serviço (IPTV)")
    saldo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    pix_code = models.CharField(max_length=255, blank=True, null=True)
    pix_code_base64 = models.TextField(blank=True, null=True)
    pix_code_created_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    link_acesso = models.UUIDField(unique=True, null=True, blank=True, editable=False)
    
    # NOVOS CAMPOS PARA AVATAR DO WHATSAPP
    whatsapp_avatar_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        verbose_name="URL do Avatar do WhatsApp",
        help_text="URL da foto de perfil do WhatsApp"
    )
    
    whatsapp_avatar_base64 = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Avatar Base64",
        help_text="Dados base64 da foto para cache local"
    )
    
    whatsapp_avatar_updated = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Última atualização do avatar",
        help_text="Data da última atualização da foto"
    )
    
    whatsapp_avatar_status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', 'Pendente'),
            ('found', 'Encontrada'),
            ('not_found', 'Não encontrada'),
            ('error', 'Erro'),
            ('no_whatsapp', 'Sem WhatsApp'),
        ],
        verbose_name="Status do Avatar",
        help_text="Status da última busca de foto"
    )
    
    whatsapp_avatar_error = models.TextField(
        blank=True,
        null=True,
        verbose_name="Erro do Avatar",
        help_text="Mensagem de erro da última tentativa"
    )
    
    whatsapp_avatar_expires = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Avatar expira em",
        help_text="Data em que o cache do avatar expira"
    )

    data_cadastro = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data de Cadastro"
    )

    cadastro_online = models.BooleanField(
        default=False,
        verbose_name="Cadastro Online",
        help_text="Indica se o usuário se cadastrou pelo site"
    )
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['login_externo', 'plano', 'dono']),
        ]
    
    def __str__(self):
        return f"{self.nome or self.username} ({self.get_tipo_usuario_display()})"
    
    def save(self, *args, **kwargs):
        # 🔴 Gera username único automaticamente se estiver vazio
        if not self.username:
            import uuid
            self.username = f"user_{uuid.uuid4().hex[:10]}"
        
        # Garante link_acesso
        if not self.link_acesso:
            import uuid
            self.link_acesso = uuid.uuid4()

        # Garante que whatsapp_avatar_expires NUNCA seja naive
        if hasattr(self, 'whatsapp_avatar_expires') and self.whatsapp_avatar_expires:
            if timezone.is_naive(self.whatsapp_avatar_expires):
                self.whatsapp_avatar_expires = timezone.make_aware(self.whatsapp_avatar_expires)

        super().save(*args, **kwargs)
    
    def is_avatar_valid(self):
        """Verifica se o avatar está válido (não expirou)"""
        if not self.whatsapp_avatar_updated or not self.whatsapp_avatar_expires:
            return False
        expires = self.whatsapp_avatar_expires
        if timezone.is_naive(expires):
            expires = timezone.make_aware(expires)
        return timezone.now() < expires

    def get_avatar_display(self):
        """Retorna a URL do avatar para exibição"""
        if self.is_avatar_found():
            return self.whatsapp_avatar_url
        return None

    def is_avatar_found(self):
        """Verifica se tem avatar encontrado e válido"""
        return (
            self.whatsapp_avatar_status == 'found' and
            self.is_avatar_valid() and
            self.whatsapp_avatar_url
        )

    def update_avatar_expiry(self, days=7):
        """Atualiza a data de expiração do avatar"""
        self.whatsapp_avatar_expires = timezone.now() + timedelta(days=7)

    def clear_avatar(self):
        """Limpa os dados do avatar"""
        self.whatsapp_avatar_url = None
        self.whatsapp_avatar_base64 = None
        self.whatsapp_avatar_status = 'pending'
        self.whatsapp_avatar_error = None
        self.whatsapp_avatar_expires = None
    
    def is_pix_code_valid(self):
        """Verifica se o código PIX ainda é válido (10 minutos)"""
        if self.pix_code_created_at:
            return (timezone.now() - self.pix_code_created_at).total_seconds() < 600
        return False
    
    @property
    def is_expired(self):
        """Verifica se a assinatura está expirada"""
        from django.utils import timezone
        if self.data_vencimento:
            return timezone.now().date() > self.data_vencimento
        return True

    @property
    def days_until_expiry(self):
        """Dias até o vencimento"""
        from django.utils import timezone
        if self.data_vencimento and not self.is_expired:
            delta = self.data_vencimento - timezone.now().date()
            return delta.days
        return 0
    
    


class Indicacao(models.Model):
    """Modelo para gerenciar indicações de clientes"""
    cliente_indicador = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='indicacoes_feitas',
        verbose_name="Cliente que indicou"
    )
    cliente_indicado = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='indicacoes_recebidas',
        verbose_name="Cliente indicado"
    )
    data_indicacao = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data da indicação"
    )
    observacao = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Observação"
    )
    
    class Meta:
        verbose_name = "Indicação"
        verbose_name_plural = "Indicações"
        unique_together = ['cliente_indicador', 'cliente_indicado']  # Evita duplicatas
        ordering = ['-data_indicacao']
    
    def __str__(self):
        return f"{self.cliente_indicador.nome} indicou {self.cliente_indicado.nome}"


class Tag(models.Model):
    """Modelo de Tags (atualizado)"""
    nome = models.CharField(max_length=100)
    cor = models.CharField(
        max_length=7, 
        default='#6c757d',
        help_text="Cor em hexadecimal (ex: #FF5733)"
    )
    descricao = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tags_criadas',
        null=True,
        blank=True
    )
    data_criacao = models.DateTimeField(auto_now_add=True, null=True)
    
    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['nome']
    
    def __str__(self):
        return self.nome

class Mensagem(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='mensagens')
    numero = models.CharField(max_length=15, blank=True, null=True, default="000000000")
    conteudo = models.TextField()  # Conteúdo da mensagem
    status = models.CharField(max_length=20)  # Status da mensagem (ex.: 'Enviada', 'Erro')
    data_envio = models.DateTimeField(default=timezone.now)  # Data e hora do envio

    def __str__(self):
        return f"Mensagem para {self.numero} - Status: {self.status}"


class ConfiguracaoMensagem(models.Model):
    usuario = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    
    # 🔥 NOVOS CAMPOS
    mensagem_bem_vindo = models.TextField(
        blank=True, null=True,
        verbose_name="Mensagem de Boas-vindas",
        help_text="Enviada automaticamente ao cadastrar um novo cliente"
    )
    mensagem_confirmacao_pagamento = models.TextField(
        blank=True, null=True,
        verbose_name="Mensagem de Confirmação de Pagamento",
        help_text="Enviada após confirmar renovação/pagamento"
    )
    
    def __str__(self):
        return f"Configuração de {self.usuario}"



logger = logging.getLogger(__name__)

class MensagemConfigurada(models.Model):
    configuracao = models.ForeignKey(
        'ConfiguracaoMensagem',
        on_delete=models.CASCADE,
        related_name="mensagens"
    )
    criterio_dias = models.IntegerField(help_text="Dias antes ou após o vencimento (ex: -1 para vencido, 5 para antes)")
    mensagem_texto = models.TextField(default='')
    horario_envio = models.TimeField()

    def substituir_variaveis(self, cliente):
        now = timezone.now()
        hora_atual = now.hour

        if 5 <= hora_atual < 12:
            saudacao = "Bom dia"
        elif 12 <= hora_atual < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"

        valor_parcela = getattr(cliente, 'valor_a_pagar', Decimal('0.00')) or Decimal('0.00')
        saldo_atual = getattr(cliente, 'saldo', Decimal('0.00')) or Decimal('0.00')

        if saldo_atual < 0:
            valor_total_a_pagar_decimal = abs(saldo_atual) + valor_parcela
        elif saldo_atual >= valor_parcela:
            valor_total_a_pagar_decimal = Decimal('0.00')
        else:
            valor_total_a_pagar_decimal = valor_parcela - saldo_atual

        try:
            valor_total_a_pagar_formatado = f"{valor_total_a_pagar_decimal:.2f}".replace('.', ',')
        except Exception as e:
            # 🔴 CORRIGIDO: Usar login_externo no log
            cliente_nome = getattr(cliente, 'login_externo', '') or getattr(cliente, 'nome', 'N/A')
            logger.error(f"Erro ao formatar valor_total_a_pagar para cliente {cliente_nome}: {e}")
            valor_total_a_pagar_formatado = "N/A"

        context = {
            'nome': getattr(cliente, 'nome', 'Cliente') or '',
            'data_vencimento': getattr(cliente, 'data_vencimento', None),
            'plano': getattr(getattr(cliente, 'plano', None), 'nome', 'Plano') or '',
            'valor_servico': getattr(cliente, 'valor_servico', Decimal('0.00')),
            'whatsapp': getattr(cliente, 'whatsapp', 'N/A') or '',
            'observacao': getattr(cliente, 'observacao', '') or '',
            'saldo': saldo_atual,
            'debitos': abs(saldo_atual) if saldo_atual < 0 else Decimal('0.00'),
            'saudacao': saudacao,
            # 🔴 CORRIGIDO: login_externo primeiro, fallback para username
            'usuario': getattr(cliente, 'login_externo', '') or getattr(cliente, 'username', 'Usuario') or '',
            # 🔴 CORRIGIDO: senha_leitura (já estava certo)
            'senha': getattr(cliente, 'senha_leitura', 'N/A') or '',
            'valor_total_a_pagar': valor_total_a_pagar_formatado,
        }

        for key, value in context.items():
            if key == 'valor_total_a_pagar':
                continue
            if isinstance(value, (datetime, date)):
                context[key] = value.strftime('%d/%m/%Y') if value else ''
            elif isinstance(value, Decimal):
                context[key] = f"{value:.2f}".replace('.', ',')
            elif isinstance(value, (int, float)):
                context[key] = str(value)

        try:
            return self.mensagem_texto.format(**context)
        except KeyError as e:
            missing_variable = e.args[0]
            logger.error(f"KeyError: Variável '{missing_variable}' usada no template de mensagem config ID {self.id} não encontrada no contexto. Contexto disponível: {context.keys()}", exc_info=True)
            raise KeyError(f"Variável '{missing_variable}' não encontrada no contexto para formatação da mensagem config ID {self.id}. Contexto disponível: {context.keys()}") from e
        except Exception as e:
            # 🔴 CORRIGIDO: Usar login_externo no log
            cliente_nome = getattr(cliente, 'login_externo', '') or getattr(cliente, 'nome', 'N/A')
            logger.error(f"Erro inesperado durante a formatação da mensagem config ID {self.id} para cliente {cliente_nome}: {e}", exc_info=True)
            raise Exception(f"Erro inesperado ao formatar mensagem config ID {self.id}: {e}") from e

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # Adicione o valor padrão




class Configuracao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    mercado_pago_access_token = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    token_telegram = models.CharField(max_length=255, blank=True, null=True)
    chave_telegram = models.CharField(max_length=255, blank=True, null=True)
    numero_celular = models.CharField(max_length=20, blank=True, null=True)
    senha = models.CharField(max_length=255, blank=True, null=True)
    device_key_padrao = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Device Key padrão",
        help_text="Key usada automaticamente em novos cadastros de aplicativos quando nenhuma Key for informada.",
    )
    codigo_protecao_playlist = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Código de proteção das listas",
        help_text="Código/PIN aplicado automaticamente às novas listas para protegê-las no aplicativo.",
    )
    
    def __str__(self):
        if self.usuario:
            nome = self.usuario.login_externo or self.usuario.nome or self.usuario.username
            return f"Configuração de {nome}"
        return "Configuração Global"


class Atualizacao(models.Model):
    VERSAO_CHOICES = [
        ('novidades', 'Novidades'),
        ('correcao_bugs', 'Correção de Bugs'),
    ]
    
    versao = models.CharField(max_length=10, blank=True, null=True)
    titulo = models.CharField(max_length=200, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=VERSAO_CHOICES, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)
    data_criacao = models.DateTimeField(default=timezone.now, blank=True, null=True)
    imagem = models.ImageField(upload_to='atualizacoes/', blank=True, null=True)  # Campo para upload de imagem

    def __str__(self):
        return f"{self.versao} - {self.titulo}" if self.titulo else "Atualização Sem Título"


from django.db import models
import re

class Tutorial(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    ordem = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['ordem', 'data_criacao']
        verbose_name = 'Tutorial'
        verbose_name_plural = 'Tutoriais'
    
    def __str__(self):
        return f"{self.ordem} - {self.titulo}"
    
    def get_video_id(self):
        if not self.video_url:
            return None
        url = self.video_url.strip()
        match = re.search(r'(?:watch\?v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})', url)
        if match:
            return match.group(1)
        return None
    

    

class HistoricoMensagem(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_mensagem"
    )
    mensagem_configurada = models.ForeignKey(
        'MensagemConfigurada',  # Está no mesmo app, então pode usar diretamente
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    mensagem_final_enviada = models.TextField(null=True, blank=True)
    data_tentativa = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=100, null=True, blank=True)
    detalhes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Histórico de {self.cliente} em {self.data_tentativa.strftime('%d/%m/%Y %H:%M')}"
    
    


from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

CustomUser = get_user_model()

class MovimentacaoCaixa(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]
    
    CATEGORIA_CHOICES = [
        ('venda', 'Venda'),
        ('servico', 'Serviço'),
        ('investimento', 'Investimento'),
        ('despesa', 'Despesa'),
        ('outros', 'Outros'),
    ]
    
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    descricao = models.CharField(max_length=200)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outros')
    data = models.DateTimeField('Data', default=timezone.now)
    
    class Meta:
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - R$ {self.valor} - {self.descricao[:20]}"
    
    def save(self, *args, **kwargs):
        # Garante que o valor seja positivo
        if self.valor < Decimal('0'):
            self.valor = abs(self.valor)
        super().save(*args, **kwargs)
        
        
        
# ==========================================
# LOG DE ATIVIDADE DO SISTEMA
# ==========================================
class LogAtividade(models.Model):
    """
    Registro completo de todas as ações no sistema
    """
    TIPO_ACAO_CHOICES = [
        ('login', 'Login no Sistema'),
        ('logout', 'Logout do Sistema'),
        ('create', 'Criação de Registro'),
        ('update', 'Edição de Registro'),
        ('delete', 'Exclusão de Registro'),
        ('view', 'Visualização de Página'),
        ('acesso', 'Acesso ao Sistema'),
        ('pagamento', 'Pagamento Realizado'),
        ('renovacao', 'Renovação de Cliente'),
        ('importacao', 'Importação de Dados'),
        ('exportacao', 'Exportação de Dados'),
        ('envio_msg', 'Envio de Mensagem'),
        ('agendamento_msg', 'Agendamento de Mensagem'),
    ]
    
    # Usuário que realizou a ação
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='logs_atividade',
        null=True,  # Permite logs de usuários não autenticados
        blank=True
    )
    
    # Tipo da ação
    tipo_acao = models.CharField(
        max_length=50,
        choices=TIPO_ACAO_CHOICES,
        verbose_name='Tipo de Ação'
    )
    
    # Descrição detalhada
    descricao = models.TextField(
        verbose_name='Descrição da Ação'
    )
    
    # Modelo afetado (opcional)
    modelo_afetado = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Modelo Afetado'
    )
    
    # ID do objeto afetado (opcional)
    objeto_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='ID do Objeto'
    )
    
    # Dados antes e depois da alteração (JSON)
    dados_antes = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Dados Antes da Ação'
    )
    
    dados_depois = models.JSONField(
        blank=True,
        null=True,
        verbose_name='Dados Depois da Ação'
    )
    
    # Informações de rede e navegador
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='Endereço IP'
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name='User Agent'
    )
    
    # Metadados
    data_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Data/Hora'
    )
    
    duracao = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Duração (segundos)'
    )
    
    status = models.CharField(
        max_length=20,
        default='sucesso',
        choices=[
            ('sucesso', 'Sucesso'),
            ('falha', 'Falha'),
            ('erro', 'Erro')
        ]
    )
    
    # Contexto adicional
    url_acessada = models.URLField(
        blank=True,
        null=True,
        verbose_name='URL Acessada'
    )
    
    metodo_http = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name='Método HTTP'
    )
    
    class Meta:
        ordering = ['-data_hora']
        verbose_name = 'Log de Atividade'
        verbose_name_plural = 'Logs de Atividade'
        indexes = [
            models.Index(fields=['usuario', 'data_hora']),
            models.Index(fields=['tipo_acao', 'data_hora']),
        ]
    
    def __str__(self):
        if self.usuario:
            nome = self.usuario.login_externo or self.usuario.nome or self.usuario.username
        else:
            nome = 'Sistema'
        return f"{nome} - {self.get_tipo_acao_display()} - {self.data_hora.strftime('%d/%m/%Y %H:%M')}"

    
    @classmethod
    def registrar(cls, **kwargs):
        """
        Método para registrar logs de forma simplificada
        """
        try:
            # Adiciona IP automaticamente se disponível
            from django.http import HttpRequest
            request = kwargs.pop('request', None)
            
            if request and isinstance(request, HttpRequest):
                if 'ip_address' not in kwargs:
                    # Tenta pegar o IP real (funciona com proxies)
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip = x_forwarded_for.split(',')[0]
                    else:
                        ip = request.META.get('REMOTE_ADDR')
                    kwargs['ip_address'] = ip
                
                if 'user_agent' not in kwargs:
                    kwargs['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
                
                if 'url_acessada' not in kwargs:
                    kwargs['url_acessada'] = request.build_absolute_uri()
                
                if 'metodo_http' not in kwargs:
                    kwargs['metodo_http'] = request.method
            
            # Garante que usuário seja pego do request
            if 'usuario' not in kwargs and request and hasattr(request, 'user'):
                kwargs['usuario'] = request.user if request.user.is_authenticated else None
            
            # Cria o log
            return cls.objects.create(**kwargs)
            
        except Exception as e:
            # Log no console em caso de erro (não quebrar o sistema)
            import logging
            logging.error(f"Erro ao registrar log: {e}")
            return None
        




class HistoricoJogo(models.Model):
    cliente = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    time_casa = models.CharField(max_length=100)
    time_fora = models.CharField(max_length=100)
    campeonato = models.CharField(max_length=150)
    horario = models.CharField(max_length=10)
    data_acesso = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.time_casa} vs {self.time_fora}"
    
class JogoFavorito(models.Model):
    cliente = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    jogo_id = models.CharField(max_length=200)  # ID único do jogo
    time_casa = models.CharField(max_length=100)
    time_fora = models.CharField(max_length=100)
    campeonato = models.CharField(max_length=150)
    criado_em = models.DateTimeField(auto_now_add=True)


class ConfiguracaoIndicacao(models.Model):
    """Configuração de comissão por indicação - POR CLIENTE"""
    TIPO_COMISSAO_CHOICES = [
        ('indicacao', 'Por Indicação'),
        ('renovacao', 'Por Renovação'),
        ('ambos', 'Ambos (Indicação + Renovação)'),
    ]
    
    # 🔄 AGORA POR CLIENTE, não por usuário
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='config_indicacao',
        default=1,  # ← Adicione temporariamente
        verbose_name="Cliente indicador"
    )
    
    tipo_comissao = models.CharField(
        max_length=20,
        choices=TIPO_COMISSAO_CHOICES,
        default='indicacao'
    )
    
    valor_por_indicacao = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Valor que o indicador ganha por cada indicação"
    )
    
    valor_por_renovacao = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Valor que o indicador ganha quando o indicado renova"
    )
    
    ativar_meta = models.BooleanField(default=False)
    quantidade_meta = models.IntegerField(default=3)
    bonus_meta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    validade_meses = models.IntegerField(default=1, help_text="0 = sem validade")
    
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuração de Indicação"
        verbose_name_plural = "Configurações de Indicação"
    
    def __str__(self):
        return f"Comissão de {self.cliente.nome} - {self.get_tipo_comissao_display()}"
    
# models.py (adicione ao seu arquivo existente)
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets

class VerificationCode(models.Model):
    """
    Modelo para códigos de verificação (Login e WhatsApp)
    """
    TYPE_CHOICES = [
        ('login', 'Login'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    code = models.CharField(max_length=6)
    code_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='login')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Código de Verificação'
        verbose_name_plural = 'Códigos de Verificação'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_code_type_display()}: {self.code} - {'Válido' if self.is_valid() else 'Expirado'}"
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    @classmethod
    def generate_code(cls, code_type='login', session_key=None, whatsapp_number=None, length=4):
        """
        Gera um novo código de verificação único
        """
        # Limpa códigos expirados
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
        
        # Gera código único
        while True:
            code = ''.join(secrets.choice('0123456789') for _ in range(length))
            if not cls.objects.filter(code=code, code_type=code_type, is_used=False).exists():
                break
        
        verification_code = cls.objects.create(
            code=code,
            code_type=code_type,
            expires_at=timezone.now() + timedelta(minutes=5),
            session_key=session_key,
            whatsapp_number=whatsapp_number
        )
        
        return verification_code
    
    def mark_as_used(self):
        self.is_used = True
        self.save()



# clientes/models.py - Adicione ao final

class BackupSchedule(models.Model):
    """Agendamento de backups automáticos"""
    FREQUENCIA_CHOICES = [
        ('1h', 'A cada 1 hora'),
        ('3h', 'A cada 3 horas'),
        ('6h', 'A cada 6 horas'),
        ('12h', 'A cada 12 horas'),
        ('24h', 'A cada 24 horas'),
        ('48h', 'A cada 48 horas'),
        ('7d', 'A cada 7 dias'),
        ('30d', 'A cada 30 dias'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='backup_schedules'
    )
    frequencia = models.CharField(
        max_length=10,
        choices=FREQUENCIA_CHOICES,
        default='24h'
    )
    manter_ultimos = models.IntegerField(
        default=7,
        help_text="Quantos backups manter"
    )
    ativo = models.BooleanField(default=True)
    ultimo_backup = models.DateTimeField(null=True, blank=True)
    proximo_backup = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Agendamento de Backup'
        verbose_name_plural = 'Agendamentos de Backup'
    
    def __str__(self):
        return f"Backup {self.get_frequencia_display()} - {'Ativo' if self.ativo else 'Pausado'}"
    
    def calcular_proximo_backup(self):
        """Calcula quando será o próximo backup"""
        from datetime import timedelta
        
        frequencia_map = {
            '1h': timedelta(hours=1),
            '3h': timedelta(hours=3),
            '6h': timedelta(hours=6),
            '12h': timedelta(hours=12),
            '24h': timedelta(hours=24),
            '48h': timedelta(hours=48),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
        }
        
        delta = frequencia_map.get(self.frequencia, timedelta(hours=24))
        base = self.ultimo_backup or timezone.now()
        return base + delta


# clientes/models.py - Atualize o BackupHistory

class BackupHistory(models.Model):
    """Histórico de backups realizados"""
    STATUS_CHOICES = [
        ('success', 'Sucesso'),
        ('error', 'Erro'),
        ('running', 'Executando'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='backup_history'
    )
    arquivo = models.CharField(max_length=255)
    tamanho = models.BigIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    erro = models.TextField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    
    # 🔴 REMOVIDO: google_drive_file_id (não usa mais Google Drive)
    # 🔴 ADICIONADO: ID da mensagem no Telegram
    telegram_message_id = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Histórico de Backup'
        verbose_name_plural = 'Históricos de Backup'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Backup {self.data_criacao.strftime('%d/%m/%Y %H:%M')} - {self.get_status_display()}"
    
    def tamanho_formatado(self):
        if self.tamanho < 1024:
            return f"{self.tamanho} B"
        elif self.tamanho < 1024 * 1024:
            return f"{self.tamanho / 1024:.2f} KB"
        else:
            return f"{self.tamanho / (1024 * 1024):.2f} MB"
        
    

# clientes/models.py

class Servico(models.Model):
    """Modelo de Serviço/Plano com configurações avançadas e controle de lotes"""
    
    TIPO_PLANO_CHOICES = [
        ('assinatura', 'Assinatura'),
        ('venda_vista', 'Venda à Vista'),
        ('venda_prazo', 'Venda a Prazo'),
    ]
    
    TIPO_ESTOQUE_CHOICES = [
        ('unidades', 'Unidades (Produto Físico)'),
        ('creditos', 'Créditos (Assinatura/Recarga)'),
        ('ambos', 'Ambos (Unidades + Créditos)'),
    ]
    
    # ==========================================
    # DADOS BÁSICOS
    # ==========================================
    nome = models.CharField(max_length=100, verbose_name="Nome do Plano")
    custos = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Custos")
    valor = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Valor de Venda")
    cor = models.CharField(max_length=7, blank=True, null=True, verbose_name="Cor do Plano")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    revenda = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    
    # ==========================================
    # TIPO DE PLANO
    # ==========================================
    tipo_plano = models.CharField(
        max_length=20,
        choices=TIPO_PLANO_CHOICES,
        default='assinatura',
        verbose_name="Tipo de Plano"
    )
    
    # ==========================================
    # CONTROLE DE ESTOQUE AVANÇADO
    # ==========================================
    controlar_estoque = models.BooleanField(
        default=False,
        verbose_name="Controlar Estoque"
    )
    tipo_estoque = models.CharField(
        max_length=20,
        choices=TIPO_ESTOQUE_CHOICES,
        default='creditos',
        verbose_name="Tipo de Estoque",
        help_text="Unidades = produto físico | Créditos = assinatura/recarga"
    )
    estoque = models.IntegerField(
        default=0,
        blank=True,
        verbose_name="Quantidade em Estoque (Unidades)"
    )
    multiplicador = models.IntegerField(
        default=1,
        blank=True,
        verbose_name="Multiplicador",
        help_text="Quantas vendas cada unidade permite (ex: 1 unidade = 2 vendas)"
    )
    codigo_produto = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Código do Produto (SKU)",
        help_text="Código único para identificar o produto"
    )
    
    # ==========================================
    # CONFIGURAÇÕES DE CAMPOS OBRIGATÓRIOS
    # ==========================================
    exigir_usuario = models.BooleanField(default=False, verbose_name="Exigir Usuário")
    exigir_senha = models.BooleanField(default=False, verbose_name="Exigir Senha")
    usuario_unico = models.BooleanField(
        default=True,
        verbose_name="Usuário Único",
        help_text="Se marcado, não permite usuários duplicados"
    )
    exigir_nome = models.BooleanField(default=True, verbose_name="Exigir Nome")
    exigir_email = models.BooleanField(default=False, verbose_name="Exigir E-mail")
    exigir_cpf = models.BooleanField(default=False, verbose_name="Exigir CPF")
    
    # ==========================================
    # DATAS
    # ==========================================
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")

    # ==========================================
    # INTEGRAÇÃO COM PAINÉIS EXTERNOS
    # ==========================================
    INTEGRACAO_TIPO_CHOICES = [
        ('nenhuma', 'Sem integração'),
        ('sigman', 'SIGMAN'),
        ('unitv', 'UniTV / Resell Media'),
    ]
    INTEGRACAO_POLITICA_CHOICES = [
        ('manual', 'Somente manual'),
        ('facultativa', 'Manual ou automático'),
        ('obrigatoria', 'Automático obrigatório'),
    ]
    MANUAL_CREDITO_CHOICES = [
        ('sempre', 'Sempre consumir crédito'),
        ('nunca', 'Nunca consumir crédito'),
        ('perguntar', 'Perguntar na renovação'),
    ]

    integracao_ativa = models.BooleanField(default=False, verbose_name='Integração ativa')
    integracao_tipo = models.CharField(
        max_length=20, choices=INTEGRACAO_TIPO_CHOICES, default='nenhuma',
        verbose_name='Tipo de painel'
    )
    integracao_politica = models.CharField(
        max_length=20, choices=INTEGRACAO_POLITICA_CHOICES, default='manual',
        verbose_name='Política de renovação'
    )
    integracao_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='URL do painel/API')
    integracao_token = models.CharField(max_length=500, blank=True, null=True, verbose_name='Token')
    integracao_api_key = models.CharField(max_length=500, blank=True, null=True, verbose_name='API Key')
    integracao_usuario = models.CharField(max_length=255, blank=True, null=True, verbose_name='Usuário/identificador do painel')
    integracao_senha = models.CharField(max_length=500, blank=True, null=True, verbose_name='Senha do painel')
    integracao_servidor_externo_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='ID do servidor externo')
    integracao_pacote_1_mes = models.CharField(max_length=255, blank=True, null=True, verbose_name='Pacote externo de 1 mês')
    integracao_pacote_teste = models.CharField(max_length=255, blank=True, null=True, verbose_name='Pacote externo para teste')
    integracao_conexoes = models.PositiveIntegerField(default=1, verbose_name='Conexões/telas padrão')
    renovacao_manual_credito = models.CharField(
        max_length=20, choices=MANUAL_CREDITO_CHOICES, default='sempre',
        verbose_name='Crédito na renovação manual'
    )
    integracao_config = models.JSONField(default=dict, blank=True, verbose_name='Configuração avançada da integração')
    integracao_status = models.CharField(max_length=20, blank=True, default='', verbose_name='Status da integração')
    integracao_erro = models.TextField(blank=True, default='', verbose_name='Último erro da integração')
    integracao_ultima_verificacao = models.DateTimeField(null=True, blank=True, verbose_name='Última verificação')
    
    class Meta:
        verbose_name = 'Serviço/Plano'
        verbose_name_plural = 'Serviços/Planos'
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_plano_display()})"
    
    # ==========================================
    # PROPRIEDADES DE ESTOQUE (UNIDADES)
    # ==========================================
    @property
    def estoque_disponivel(self):
        """Calcula estoque disponível considerando o multiplicador"""
        if not self.controlar_estoque:
            return None
        if self.tipo_estoque in ['creditos']:
            return self.creditos_disponiveis
        return self.estoque * self.multiplicador
    
    @property
    def vendas_realizadas(self):
        """Conta quantos clientes já usam este plano"""
        return self.clientes.count()
    
    @property
    def vagas_restantes(self):
        """Calcula vagas restantes"""
        if not self.controlar_estoque:
            return None
        if self.tipo_estoque in ['creditos']:
            return self.creditos_disponiveis
        return max(0, (self.estoque * self.multiplicador) - self.vendas_realizadas)
    
    @property
    def tem_vagas(self):
        """Verifica se ainda há vagas disponíveis"""
        if not self.controlar_estoque:
            return True
        if self.tipo_estoque in ['creditos']:
            return self.creditos_disponiveis > 0
        return self.vagas_restantes > 0
    
    # ==========================================
    # SISTEMA DE CRÉDITOS (LOTES)
    # ==========================================
    @property
    def creditos_disponiveis(self):
        """Total de créditos disponíveis somando todos os lotes"""
        return sum(lote.quantidade_restante for lote in self.lotes.all())
    
    @property
    def custo_medio_creditos(self):
        """Custo médio dos créditos disponíveis"""
        lotes = self.lotes.filter(quantidade_restante__gt=0)
        if not lotes:
            return Decimal('0.00')
        total_creditos = sum(l.quantidade_restante for l in lotes)
        total_custo = sum(l.quantidade_restante * l.custo_unitario for l in lotes)
        return (total_custo / Decimal(str(total_creditos))).quantize(Decimal('0.01')) if total_creditos > 0 else Decimal('0.00')
    
    def consumir_credito(self, cliente, quantidade=1):
        """
        Consome créditos seguindo FIFO (primeiro lote que entrou, primeiro que sai)
        Retorna: (sucesso, mensagem, custo_total)
        """
        if self.tipo_estoque not in ['creditos', 'ambos']:
            return False, "Este plano não usa sistema de créditos", Decimal('0.00')
        
        if self.creditos_disponiveis < quantidade:
            return False, f"Créditos insuficientes. Disponível: {self.creditos_disponiveis}", Decimal('0.00')
        
        lotes_disponiveis = self.lotes.filter(quantidade_restante__gt=0).order_by('ordem')
        
        restante = quantidade
        custo_total = Decimal('0.00')
        lotes_usados = []
        
        for lote in lotes_disponiveis:
            if restante <= 0:
                break
            
            consumir = min(restante, lote.quantidade_restante)
            
            # Registra venda
            venda = VendaCredito.objects.create(
                cliente=cliente,
                servico=self,
                lote=lote,
                quantidade=consumir,
                custo_unitario_aplicado=lote.custo_unitario
            )
            
            # Atualiza lote
            lote.quantidade_restante -= consumir
            lote.save(update_fields=['quantidade_restante'])
            
            custo_total += Decimal(str(consumir)) * lote.custo_unitario
            restante -= consumir
            lotes_usados.append(lote)
        
        return True, f"{quantidade} créditos consumidos de {len(lotes_usados)} lote(s)", custo_total
    
    def get_proximo_lote_disponivel(self):
        """Retorna o próximo lote disponível (FIFO)"""
        return self.lotes.filter(quantidade_restante__gt=0).order_by('ordem').first()


# ==========================================
# MODELO DE LOTE DE ESTOQUE
# ==========================================
class LoteEstoque(models.Model):
    """
    Lote de compra de créditos/estoque
    Cada lote tem seu próprio custo unitário
    Sistema FIFO: primeiro que entra, primeiro que sai
    """
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='lotes',
        verbose_name="Serviço/Plano"
    )
    quantidade = models.IntegerField(verbose_name="Quantidade de Créditos")
    custo_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Custo Unitário (R$)"
    )
    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor Total do Lote (R$)"
    )
    quantidade_restante = models.IntegerField(
        default=0,
        verbose_name="Créditos Restantes"
    )
    data_compra = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data da Compra"
    )
    observacao = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Observação"
    )
    ordem = models.IntegerField(
        default=0,
        verbose_name="Ordem (FIFO)",
        help_text="Ordem de consumo: menor número = consumido primeiro"
    )
    
    class Meta:
        verbose_name = 'Lote de Estoque'
        verbose_name_plural = 'Lotes de Estoque'
        ordering = ['ordem', 'data_compra']
    
    def __str__(self):
        return f"Lote #{self.ordem} - {self.servico.nome} - {self.quantidade_restante}/{self.quantidade} créditos a R${self.custo_unitario}"
    
    def save(self, *args, **kwargs):
        if not self.valor_total:
            self.valor_total = self.quantidade * self.custo_unitario
        if not self.quantidade_restante and not self.pk:
            self.quantidade_restante = self.quantidade
        if not self.ordem:
            ultimo = LoteEstoque.objects.filter(servico=self.servico).order_by('-ordem').first()
            self.ordem = (ultimo.ordem + 1) if ultimo else 1
        super().save(*args, **kwargs)
    
    @property
    def esgotado(self):
        return self.quantidade_restante <= 0
    
    @property
    def valor_restante(self):
        """Valor total dos créditos restantes neste lote"""
        return self.quantidade_restante * self.custo_unitario
    
    @property
    def percentual_consumido(self):
        """Percentual do lote que já foi consumido"""
        if self.quantidade == 0:
            return 0
        return ((self.quantidade - self.quantidade_restante) / self.quantidade) * 100


# ==========================================
# MODELO DE VENDA DE CRÉDITO
# ==========================================
class VendaCredito(models.Model):
    """
    Registro de consumo de créditos
    Rastreia qual lote foi usado em cada venda
    """
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='consumo_creditos',
        verbose_name="Cliente"
    )
    servico = models.ForeignKey(
        Servico,
        on_delete=models.CASCADE,
        related_name='vendas_creditos',
        verbose_name="Serviço/Plano"
    )
    lote = models.ForeignKey(
        LoteEstoque,
        on_delete=models.CASCADE,
        related_name='consumos',
        verbose_name="Lote Utilizado"
    )
    quantidade = models.IntegerField(
        default=1,
        verbose_name="Quantidade de Créditos"
    )
    custo_unitario_aplicado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Custo Unitário Aplicado (R$)"
    )
    data_venda = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Data da Venda"
    )
    
    class Meta:
        verbose_name = 'Venda de Crédito'
        verbose_name_plural = 'Vendas de Créditos'
        ordering = ['-data_venda']
    
    def __str__(self):
        return f"{self.cliente.nome} - {self.quantidade} crédito(s) de {self.servico.nome} (Lote #{self.lote.ordem})"
    
    @property
    def valor_total(self):
        return self.quantidade * self.custo_unitario_aplicado
    


class AvisoSistema(models.Model):
    TIPO_CHOICES = [
        ('info', 'ℹ️ Informativo'),
        ('success', '✅ Sucesso'),
        ('warning', '⚠️ Alerta'),
        ('danger', '❌ Urgente'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avisos',
        verbose_name="Usuário"
    )
    titulo = models.CharField(max_length=200, verbose_name="Título do Aviso")
    mensagem = models.TextField(verbose_name="Mensagem")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='info', verbose_name="Tipo")
    icone = models.CharField(max_length=50, default='fa-bell', verbose_name="Ícone Font Awesome")
    cor_destaque = models.CharField(max_length=7, default='#667eea', verbose_name="Cor de Destaque")
    
    # Ordenação
    ordem = models.IntegerField(default=0, verbose_name="Ordem de Exibição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Regras de exibição
    mostrar_a_cada_login = models.BooleanField(
        default=False,
        verbose_name="Mostrar a cada login"
    )
    mostrar_primeiro_login = models.BooleanField(
        default=False,
        verbose_name="Mostrar no primeiro login",
        help_text="Mostra apenas nas primeiras X vezes que o usuário logar"
    )
    repeticoes = models.IntegerField(
        default=1,
        verbose_name="Quantidade de repetições",
        help_text="Quantas vezes mostrar (para primeiro login ou intervalo)"
    )
    permitir_ocultar = models.BooleanField(
        default=True,
        verbose_name="Permitir cliente ocultar",
        help_text="Se marcado, o cliente pode marcar 'Não mostrar novamente'"
    )
    mostrar_intervalo_horas = models.IntegerField(
        null=True, blank=True,
        verbose_name="Mostrar a cada X horas"
    )
    mostrar_antes_vencimento = models.IntegerField(
        null=True, blank=True,
        verbose_name="Mostrar X dias antes do vencimento"
    )
    mostrar_no_vencimento = models.BooleanField(
        default=False,
        verbose_name="Mostrar no dia do vencimento"
    )
    
    # Período de validade
    data_inicio = models.DateTimeField(default=timezone.now, verbose_name="Data de Início")
    data_fim = models.DateTimeField(null=True, blank=True, verbose_name="Data de Fim")
    
    # Datas
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Aviso do Sistema'
        verbose_name_plural = 'Avisos do Sistema'
        ordering = ['ordem', '-data_criacao']
    
    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo}"


# NOVO MODELO: Controle de avisos vistos pelo cliente
class AvisoVisto(models.Model):
    aviso = models.ForeignKey(AvisoSistema, on_delete=models.CASCADE, related_name='visualizacoes')
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avisos_vistos')
    data_visto = models.DateTimeField(auto_now_add=True)
    oculto_permanentemente = models.BooleanField(default=False)
    contador = models.IntegerField(default=1)
    
    class Meta:
        unique_together = ['aviso', 'cliente']
        verbose_name = 'Aviso Visualizado'
        verbose_name_plural = 'Avisos Visualizados'
    
    def __str__(self):
        return f"{self.cliente} - {self.aviso.titulo} ({self.contador}x)"









############################# integração ibo fun e outro ####

from django.conf import settings
from django.db import models


class ProvedorPlaylist(models.TextChoices):
    IBO_PLAYER = "ibo_player", "IBO Player"
    FUN_PLAYS = "fun_plays", "Fun Plays"
    FOCOX_PLAYER = "focox_player", "FocoX Player"
    LAZER_PLAYER = "lazer_player", "Lazer Player"
   

class IntegracaoPlaylistCliente(models.Model):
    STATUS_CHOICES = [
        ("nao_configurado", "Não configurado"),
        ("configurado", "Configurado"),
        ("aguardando_captcha", "Aguardando CAPTCHA"),
        ("processando", "Processando"),
        ("ativo", "Ativo"),
        ("confirmacao_pendente", "Confirmação pendente"),
        ("erro", "Erro"),
        ("excluido", "Excluído"),
    ]

    dono = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integracoes_playlist_criadas",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="integracoes_playlist",
        null=True,
        blank=True,
    )

    # Nome do dispositivo/cadastro. Ex.: João, Sala, Mercado.
    nome_avulso = models.CharField(max_length=150, blank=True, default="")

    # Credencial padrão opcional para novas playlists.
    usuario_iptv = models.CharField(max_length=255, blank=True, default="")
    senha_iptv = models.CharField(max_length=255, blank=True, default="")

    provedor = models.CharField(max_length=40, choices=ProvedorPlaylist.choices)
    mac_address = models.CharField(max_length=50, blank=True)
    device_key = models.CharField(max_length=150, blank=True)
    dns = models.URLField(max_length=500, blank=True)
    codigo = models.CharField(max_length=150, blank=True)
    url_template = models.TextField(blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="nao_configurado",
    )
    ultima_mensagem = models.TextField(blank=True)
    dados_remotos = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)

    # CAMPOS LEGADOS: mantenha nesta primeira implantação.
    # As novas views não dependem deles.
    nome_playlist = models.CharField(max_length=150, default="Minha lista")
    usuario_template = models.CharField(max_length=255, default="{usuario}")
    senha_template = models.CharField(max_length=255, default="{senha}")
    proteger = models.BooleanField(default=False)
    pin_protecao = models.CharField(max_length=255, blank=True)
    playlist_remote_id = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dono", "provedor", "mac_address"],
                name="integracao_playlist_dono_provedor_mac_unica",
            )
        ]
        ordering = ["nome_avulso", "-criado_em"]

    def __str__(self):
        if self.cliente_id:
            nome = (
                getattr(self.cliente, "nome", "")
                or getattr(self.cliente, "username", "")
            )
        else:
            nome = self.nome_avulso or self.usuario_iptv
        return f"{nome or 'Dispositivo'} - {self.get_provedor_display()}"

    @property
    def nome_exibicao(self):
        # O nome visível no Gerenciador de playlists é sempre o "Nome do cadastro".
        # O cliente vinculado serve para preencher/relacionar credenciais, mas não
        # deve substituir o nome escolhido para o dispositivo/cadastro.
        if self.nome_avulso:
            return self.nome_avulso
        if self.cliente_id:
            return (
                getattr(self.cliente, "nome", "")
                or getattr(self.cliente, "username", "")
                or f"Cliente #{self.cliente_id}"
            )
        return self.usuario_iptv or f"Dispositivo #{self.pk}"


class PlaylistRemota(models.Model):
    STATUS_CHOICES = [
        ("rascunho", "Rascunho"),
        ("processando", "Processando"),
        ("ativo", "Ativa"),
        ("confirmacao_pendente", "Confirmação pendente"),
        ("nao_encontrada", "Não encontrada"),
        ("erro", "Erro"),
        ("excluida", "Excluída"),
    ]

    integracao = models.ForeignKey(
        IntegracaoPlaylistCliente,
        on_delete=models.CASCADE,
        related_name="playlists",
    )
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="playlists_remotas",
        null=True,
        blank=True,
    )

    nome = models.CharField(max_length=150, default="Minha lista")
    nome_remoto = models.CharField(max_length=150, blank=True, default="")
    remote_id = models.CharField(max_length=255, blank=True, default="")

    # Dados usados para criar/substituir a lista.
    usuario_iptv = models.CharField(max_length=255, blank=True, default="")
    senha_iptv = models.CharField(max_length=255, blank=True, default="")
    dns = models.URLField(max_length=500, blank=True)
    codigo = models.CharField(max_length=150, blank=True)
    url_playlist = models.TextField(blank=True)
    modo_envio = models.CharField(max_length=20, blank=True, default="url")

    protegida = models.BooleanField(default=False)
    pin_protecao = models.CharField(max_length=255, blank=True, default="")
    pin_conhecido = models.BooleanField(default=False)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="rascunho",
    )
    encontrada_na_ultima_sync = models.BooleanField(default=True)
    ultima_mensagem = models.TextField(blank=True)
    dados_remotos = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["nome", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["integracao", "remote_id"],
                condition=~models.Q(remote_id=""),
                name="playlist_integracao_remote_id_unico",
            )
        ]
        indexes = [
            models.Index(fields=["integracao", "status"]),
            models.Index(fields=["remote_id"]),
            models.Index(fields=["nome"]),
        ]

    def __str__(self):
        return f"{self.nome} - {self.integracao.nome_exibicao}"

    def credenciais(self):
        if self.cliente_id:
            return {
                "usuario": getattr(self.cliente, "login_externo", "") or "",
                "senha": getattr(self.cliente, "senha_leitura", "") or "",
            }
        return {
            "usuario": self.usuario_iptv or self.integracao.usuario_iptv or "",
            "senha": self.senha_iptv or self.integracao.senha_iptv or "",
        }


class HistoricoIntegracaoPlaylist(models.Model):
    ACAO_CHOICES = [
        ("pesquisar", "Pesquisar dispositivo"),
        ("sincronizar", "Sincronizar playlists"),
        ("adicionar", "Adicionar playlist"),
        ("editar", "Editar playlist"),
        ("substituir", "Substituir playlist"),
        ("excluir", "Excluir playlist"),
        ("pin", "Alterar proteção/PIN"),
        ("consultar", "Consultar playlist"),
    ]
    STATUS_CHOICES = [
        ("processando", "Processando"),
        ("sucesso", "Sucesso"),
        ("erro", "Erro"),
        ("parcial", "Parcial"),
    ]

    integracao = models.ForeignKey(
        IntegracaoPlaylistCliente,
        on_delete=models.CASCADE,
        related_name="historico",
    )
    playlist = models.ForeignKey(
        PlaylistRemota,
        on_delete=models.SET_NULL,
        related_name="historico",
        null=True,
        blank=True,
    )
    acao = models.CharField(max_length=30, choices=ACAO_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    mensagem = models.TextField(blank=True)
    http_status = models.PositiveIntegerField(null=True, blank=True)
    requisicao_resumo = models.JSONField(default=dict, blank=True)
    resposta_api = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]


# ==========================================
# TESTES E OPERAÇÕES DE PAINEL EXTERNO
# ==========================================
class TestePainel(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('vencido', 'Vencido'),
        ('convertido', 'Convertido em cliente'),
        ('falha', 'Falha'),
    ]

    revenda = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='testes_painel_criados')
    servico = models.ForeignKey('Servico', on_delete=models.PROTECT, related_name='testes_painel')
    nome = models.CharField(max_length=150)
    whatsapp = models.CharField(max_length=30, blank=True, default='')
    login_externo = models.CharField(max_length=255, blank=True, default='')
    senha_leitura = models.CharField(max_length=255, blank=True, default='')
    external_id = models.CharField(max_length=255, blank=True, default='')
    data_vencimento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo', db_index=True)
    cliente_convertido = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='testes_convertidos'
    )
    dados_externos = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    convertido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        indexes = [models.Index(fields=['revenda', 'status']), models.Index(fields=['login_externo'])]

    def __str__(self):
        return f'{self.nome} - {self.login_externo or "teste"}'


class OperacaoIntegracaoPainel(models.Model):
    TIPO_CHOICES = [
        ('consulta', 'Consulta'),
        ('renovacao', 'Renovação'),
        ('teste', 'Criação de teste'),
        ('conversao_teste', 'Conversão de teste'),
        ('verificacao', 'Verificação'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('consultando', 'Consultando'),
        ('aceita', 'Aceita pelo painel'),
        ('concluida', 'Concluída'),
        ('verificar', 'Requer verificação'),
        ('falhou', 'Falhou'),
    ]

    revenda = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='operacoes_integracao')
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='operacoes_painel')
    servico = models.ForeignKey('Servico', on_delete=models.PROTECT, related_name='operacoes_integracao')
    teste = models.ForeignKey('TestePainel', on_delete=models.SET_NULL, null=True, blank=True, related_name='operacoes')
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', db_index=True)
    chave_idempotencia = models.CharField(max_length=120, unique=True, db_index=True)
    login_externo = models.CharField(max_length=255, blank=True, default='')
    external_id = models.CharField(max_length=255, blank=True, default='')
    meses = models.PositiveIntegerField(default=1)
    creditos_externos = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    creditos_locais = models.PositiveIntegerField(default=0)
    custo_local = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    vencimento_anterior = models.DateTimeField(null=True, blank=True)
    vencimento_novo = models.DateTimeField(null=True, blank=True)
    requisicao_resumo = models.JSONField(default=dict, blank=True)
    resposta_resumo = models.JSONField(default=dict, blank=True)
    erro = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['revenda', 'status']),
            models.Index(fields=['servico', 'login_externo', 'criado_em']),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.login_externo} - {self.get_status_display()}'
