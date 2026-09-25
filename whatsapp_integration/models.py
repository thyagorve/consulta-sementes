# whatsapp_integration/models.py - VERSÃO CORRIGIDA
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
import logging
from django.contrib.auth import get_user_model
User = get_user_model()  # Isso pega o modelo de usuário correto

logger = logging.getLogger(__name__)



class HistoricoMensagemAutomatica(models.Model):
    """
    Modelo para histórico de mensagens automáticas (já existente no seu sistema)
    Mantenha este se já existir, ou ajuste conforme necessário
    """
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historicos_mensagem_automatica"
    )
    mensagem_configurada = models.ForeignKey(
        'clientes.MensagemConfigurada',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    mensagem_final_enviada = models.TextField(null=True, blank=True)
    data_tentativa = models.DateTimeField(default=timezone.now)
    data_envio = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    detalhes = models.TextField(null=True, blank=True)
    api_message_id = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        db_table = 'historico_mensagem_automatica'
        ordering = ['-data_tentativa']
    
    def __str__(self):
        return f"Histórico automático de {self.cliente} em {self.data_tentativa.strftime('%d/%m/%Y %H:%M')}"

# ===== MODELOS EXISTENTES DO SEU SISTEMA =====

class UserInstance(models.Model):
    STATUS_CHOICES = [
        ('created', 'Criada'),
        ('scanning_qr', 'Aguardando QR'),
        ('connected', 'Conectada'),
        ('disconnected', 'Desconectada'),
        ('error', 'Erro'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='whatsapp_instances'
    )
    
    instance_name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    profile_name = models.CharField(max_length=200, blank=True, null=True)
    profile_pic_url = models.TextField(blank=True, null=True)
    owner_jid = models.CharField(max_length=200, blank=True, null=True)
    last_check = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    instance_token = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    qr_code_data = models.TextField(blank=True, null=True)
    qr_generated_at = models.DateTimeField(blank=True, null=True)
    wid = models.CharField(max_length=200, blank=True, null=True)
    pushname = models.CharField(max_length=200, blank=True, null=True)
    qr_code = models.TextField(blank=True, null=True)
    
    # NOVOS CAMPOS PARA ENVIO EM MASSA (APENAS ADICIONE ESTES DOIS)
    api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key")
    base_url = models.URLField(
        default='http://localhost:8080',
        verbose_name="URL Base da API",
        help_text="URL da API Evolution (ex: http://localhost:8080)"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Instância WhatsApp'
        verbose_name_plural = 'Instâncias WhatsApp'
    
    def __str__(self):
        return f"{self.user.username} - {self.instance_name} ({self.status})"
    
    def clean(self):
        """Validação do nome da instância"""
        if not self.instance_name:
            raise ValidationError("Nome da instância é obrigatório")
        
        if not all(c.isalnum() or c == '_' for c in self.instance_name):
            raise ValidationError("Use apenas letras, números e underscore (_)")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def is_owner(self, user):
        """Verifica se o usuário é dono da instância"""
        return self.user == user
    
    def can_connect(self, user):
        """Verifica se o usuário pode conectar"""
        return self.user == user and self.is_active
    
    def can_delete(self, user):
        """Verifica se o usuário pode deletar"""
        return self.user == user
    
    def mark_as_scanning(self):
        """Marca instância como aguardando QR"""
        self.status = 'scanning_qr'
        self.qr_generated_at = timezone.now()
        self.save()
    
    def mark_as_connected(self, profile_name=None, profile_pic_url=None, owner_jid=None):
        """Marca instância como conectada"""
        self.status = 'connected'
        self.profile_name = profile_name
        self.profile_pic_url = profile_pic_url
        self.owner_jid = owner_jid
        self.last_check = timezone.now()
        self.save()
    
    def mark_as_disconnected(self):
        """Marca instância como desconectada"""
        self.status = 'disconnected'
        self.profile_name = None
        self.profile_pic_url = None
        self.owner_jid = None
        self.last_check = timezone.now()
        self.save()
    
    def qr_expired(self):
        """Verifica se o QR Code expirou (5 minutos)"""
        if not self.qr_generated_at:
            return True
        
        expiration_time = self.qr_generated_at + timezone.timedelta(minutes=5)
        return timezone.now() > expiration_time
    
    @property
    def display_status(self):
        """Status para exibição"""
        status_map = {
            'created': 'Criada',
            'scanning_qr': 'Aguardando QR',
            'connected': 'Conectada',
            'disconnected': 'Desconectada',
            'error': 'Erro'
        }
        return status_map.get(self.status, self.status)
    
    # NOVOS MÉTODOS PARA ENVIO EM MASSA (ADICIONE APENAS ESTES)
    @property
    def esta_conectado(self):
        """Verifica se a instância está conectada (para compatibilidade com envio em massa)"""
        return self.status == 'connected'
    
    def get_connection_url(self):
        """Retorna URL para verificar conexão"""
        return f"{self.base_url}/instance/connectionState/{self.instance_name}"
    
    def get_send_message_url(self):
        """Retorna URL para enviar mensagem"""
        return f"{self.base_url}/message/sendText/{self.instance_name}"
    
    @property
    def pode_enviar_mensagens(self):
        """Verifica se pode enviar mensagens"""
        return self.status == 'connected' and self.is_active
    
    @classmethod
    def get_connected_instance_for_user(cls, user):
        """Retorna instância conectada do usuário"""
        return cls.objects.filter(
            user=user,
            status='connected',
            is_active=True
        ).first()





from django.db import models
from django.conf import settings
from django.utils import timezone
from clientes.models import CustomUser, Servico, Tag


from django.conf import settings
from django.db import models

from clientes.models import CustomUser, Servico, Tag


class MensagemMassa(models.Model):
    STATUS_CHOICES = [
        ('rascunho', '📝 Rascunho'),
        ('agendada', '⏰ Agendada'),
        ('enviando', '🔄 Enviando'),
        ('concluida', '✅ Concluída'),
        ('cancelada', '❌ Cancelada'),
        ('falha', '⚠️ Falha'),
    ]

    MODO_DESTINATARIOS_CHOICES = [
        ('clientes', 'Clientes cadastrados'),
        ('avulsos', 'Somente números avulsos'),
        ('ambos', 'Clientes e números avulsos'),
    ]

    remetente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mensagens_massa',
    )
    mensagem = models.TextField()

    modo_destinatarios = models.CharField(
        max_length=20,
        choices=MODO_DESTINATARIOS_CHOICES,
        default='clientes',
    )

    plano_filtro = models.ForeignKey(
        Servico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status_filtro = models.CharField(max_length=20, blank=True)
    dias_vencido_filtro = models.IntegerField(null=True, blank=True)
    tags_filtro = models.ManyToManyField(Tag, blank=True)

    clientes = models.ManyToManyField(
        CustomUser,
        related_name='mensagens_massa_recebidas',
        blank=True,
        help_text='Clientes selecionados pelos filtros.',
    )

    numeros_avulsos = models.TextField(
        blank=True,
        default='',
        help_text='Um número por linha, ou separados por vírgula/ponto e vírgula.',
    )

    data_agendamento = models.DateTimeField(null=True, blank=True)
    agendada = models.BooleanField(default=False)
    midia = models.FileField(upload_to='mensagens_massa/', null=True, blank=True)
    tipo_midia = models.CharField(max_length=50, blank=True)

    total_destinatarios = models.IntegerField(default=0)
    enviados_com_sucesso = models.IntegerField(default=0)
    enviados_com_falha = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='rascunho',
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_envio_inicio = models.DateTimeField(null=True, blank=True)
    data_envio_fim = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Mensagem em Massa'
        verbose_name_plural = 'Mensagens em Massa'

    def __str__(self):
        return f'Massa #{self.pk} - {self.remetente}'


class HistoricoEnvioMassa(models.Model):
    STATUS_CHOICES = [
        ('pendente', '⏳ Pendente'),
        ('enviado', '✅ Enviado'),
        ('falha', '❌ Falha'),
        ('entregue', '📲 Entregue'),
        ('lido', '👁️ Lido'),
    ]

    mensagem_massa = models.ForeignKey(
        MensagemMassa,
        on_delete=models.CASCADE,
        related_name='historicos',
    )
    cliente = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    whatsapp = models.CharField(max_length=20, blank=True, default='')
    mensagem_final = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    mensagem_erro = models.TextField(blank=True)
    message_id = models.CharField(max_length=255, blank=True)
    data_envio = models.DateTimeField(auto_now_add=True)
    data_confirmacao = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-data_envio']

    def __str__(self):
        nome = self.cliente.nome if self.cliente else self.whatsapp
        return f'{nome} - {self.status}'


#################################### IA ###########################

# ==========================================
# MODELOS DE IA (whatsapp_integration/models.py)
# ==========================================

# whatsapp_integration/models.py

class AIConfig(models.Model):
    admin = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='ai_global_configs',
        null=True,
        blank=True
    )
    
    # ⚠️ FALTAVA ESTE CAMPO!
    revenda = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='ai_config',
        null=True, 
        blank=True,
        help_text='Deixe vazio para config global. Preencha para config por revenda.'
    )
    
    def save(self, *args, **kwargs):
        if not self.admin_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                self.admin = admin_user
        super().save(*args, **kwargs)


    # whatsapp_integration/models.py - dentro da classe AIConfig

    def can_send_message(self):
        """Verifica se ainda pode enviar mensagens hoje"""
        today = timezone.now().date()
        if self.last_reset_date < today:
            self.messages_sent_today = 0
            self.last_reset_date = today
            self.save(update_fields=['messages_sent_today', 'last_reset_date'])
        return self.messages_sent_today < self.max_messages_per_day
    
    nome = models.CharField(max_length=100, default='Configuração Padrão')
    
    PROVIDER_CHOICES = [
        ('groq', 'Groq (Grátis)'),
        ('openai', 'OpenAI'),
        ('deepseek', 'DeepSeek'),
    ]
    
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='groq')
    use_system_key = models.BooleanField(default=True)
    api_key = models.CharField(max_length=255, blank=True)
    
    system_prompt = models.TextField(
        default="""Você é um assistente virtual profissional.
Responda de forma educada e objetiva em português.
Não invente informações. Se não souber, diga que não sabe."""
    )
    
    max_messages_per_day = models.IntegerField(default=200)
    messages_sent_today = models.IntegerField(default=0)
    last_reset_date = models.DateField(auto_now_add=True)
    max_history_messages = models.IntegerField(default=10)
    response_delay = models.IntegerField(default=2)
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    responder_privado = models.BooleanField(default=True)
    responder_grupos = models.BooleanField(default=False)
    precisa_marcacao = models.BooleanField(default=True)
    bot_marcacao = models.CharField(max_length=50, default='@bot')
    palavras_ativacao = models.TextField(blank=True, default='')
    
    class Meta:
        verbose_name = 'Configuração Global de IA'
        verbose_name_plural = 'Configurações Globais de IA'
    
    def __str__(self):
        if self.revenda:
            return f"IA: {self.revenda.nome or self.revenda.username}"
        return f"IA Global (Padrão)"
    
    @classmethod
    def get_config(cls, revenda=None):
        """Obtém a config específica da revenda ou a global"""
        if revenda:
            config = cls.objects.filter(revenda=revenda).first()
            if config:
                return config
        return cls.objects.filter(revenda__isnull=True).first()

class AIRevendaSettings(models.Model):
    """Configuração PESSOAL da revenda (ela mesma configura)"""
    revenda = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_personal_settings')
    
    # Ativação (a revenda decide se quer usar)
    ia_ativada = models.BooleanField(default=False, verbose_name='Ativar Assistente IA')
    
    # Prompt PERSONALIZADO da revenda
    prompt_personalizado = models.TextField(
        blank=True,
        verbose_name='Seu Prompt Personalizado',
        help_text='Personalize como o assistente responde para SEUS clientes'
    )
    
    # Nome do bot (personalizado)
    bot_name = models.CharField(max_length=100, default='Assistente Virtual')
    
    # Mensagem de saudação personalizada
    mensagem_saudacao = models.TextField(
        blank=True,
        default='Olá! Sou o assistente virtual. Como posso ajudar?'
    )
    
    # Horário de funcionamento (a revenda define)
    horario_inicio = models.TimeField(null=True, blank=True)
    horario_fim = models.TimeField(null=True, blank=True)
    responder_fora_horario = models.BooleanField(default=False)
    
    # Status
    pausado_ate = models.DateTimeField(null=True, blank=True)
    
    # Datas
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    responder_privado = models.BooleanField(default=True, verbose_name='Responder no Privado')
    
    # Responder em GRUPOS?
    responder_grupos = models.BooleanField(default=False, verbose_name='Responder em Grupos')
    
    # Se responder em grupos, precisa ser MARCADO?
    precisa_marcacao = models.BooleanField(default=True, verbose_name='Precisa marcar @bot no grupo')
    
    # Nome do bot para marcação (ex: @assistente)
    bot_marcacao = models.CharField(max_length=50, default='@bot', verbose_name='Marcação do Bot')
    
    # Palavras-chave que ativam a IA (se vazio, responde tudo)
    palavras_ativacao = models.TextField(
        blank=True, 
        default='',
        help_text='Palavras que ativam a IA (separadas por vírgula). Vazio = responde tudo.'
    )
    
    # Ignorar mensagens de outros bots/automáticas
    ignorar_bots = models.BooleanField(default=True)
    
    # Responder apenas quando mencionar nome da empresa/produto
    palavras_chave_empresa = models.TextField(
        blank=True,
        help_text='Nomes que ativam a IA (ex: nome da loja, produto). Vazio = qualquer mensagem.'
    )
    class Meta:
        verbose_name = 'Configuração Pessoal de IA'
        verbose_name_plural = 'Configurações Pessoais de IA'
    
    def __str__(self):
        return f"IA Pessoal: {self.revenda.nome or self.revenda.username}"


class AIClientSettings(models.Model):
    """Controle por cliente (a revenda gerencia)"""
    revenda = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ia_client_settings_revenda')
    cliente = models.ForeignKey('clientes.CustomUser', on_delete=models.CASCADE, related_name='ia_client_settings_cliente')
    
    # Status
    is_enabled = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    ignore_client = models.BooleanField(default=False)
    
    # Notas
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['revenda', 'cliente']



class AIConversation(models.Model):
    revenda = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ia_conversations_revenda')  # ← Nome ÚNICO
    cliente = models.ForeignKey('clientes.CustomUser', on_delete=models.CASCADE, related_name='ia_conversations_cliente')  # ← Nome ÚNICO
    instance = models.ForeignKey('UserInstance', on_delete=models.CASCADE)
    
    STATUS_CHOICES = [
        ('active', 'Ativa'),
        ('paused', 'Pausada'),
        ('closed', 'Encerrada'),
        ('waiting_human', 'Aguardando Humano'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    messages = models.JSONField(default=list)
    total_messages = models.IntegerField(default=0)
    ai_messages = models.IntegerField(default=0)
    human_messages = models.IntegerField(default=0)
    first_message_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)
    
    class Meta:
        unique_together = ['revenda', 'cliente']
        ordering = ['-last_message_at']

class AIQuickReply(models.Model):
   
    revenda = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_quick_replies')
    trigger = models.CharField(max_length=200)
    reply = models.TextField()
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-priority']