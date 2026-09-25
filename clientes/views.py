# -*- coding: utf-8 -*-
# ============================================
# IMPORTS PADRÃO PYTHON
# ============================================
import hashlib
import json
import logging
import math
import re
import sys
import uuid
from datetime import date, datetime, timedelta, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required


from django.db.models.functions import TruncMonth, TruncDate
from .integrations.playlists.factory import (
    get_playlist_provider,
    get_providers,
)


from clientes.message_variables import (
    substituir_variaveis_mensagem,
)

from .integrations.playlists.factory import (
    get_playlist_provider,
    get_providers,
    listar_provedores,
)
# ============================================
# IMPORTS TERCEIROS (COM VERIFICAÇÃO)
# ============================================
import pandas as pd
import qrcode
import requests
from dateutil.relativedelta import relativedelta

# ============================================
# IMPORTS DJANGO CORE
# ============================================
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate, get_user_model, login, logout
)
from django.contrib.auth.hashers import make_password

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import FieldError, PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import models, transaction
from django.db.models import (
    Avg, Count, F, Max, Min, OuterRef, Q, Subquery, Sum, Value
)
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.http import (
    HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_response_headers
from django.utils.timezone import localdate, make_aware, now
from django.views import View
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# ============================================
# IMPORTS DO PROJETO (MODELS)
# ============================================
from clientes.models import LogAtividade
from .models import (
    Atualizacao,
    AvisoSistema,
    AvisoVisto,
    BackupHistory,
    BackupSchedule,
    Configuracao,
    ConfiguracaoIndicacao,
    ConfiguracaoMensagem,
    CustomUser,
    HistoricoMensagem,
    Indicacao,
    JogoFavorito,
    LoteEstoque,
    Mensagem,
    MensagemConfigurada,
    MovimentacaoCaixa,
    RelatorioFinanceiro,
    Servico,
    Tag,
    Tutorial,
    VendaCredito,
    VerificationCode,
    IntegracaoPlaylistCliente,
    HistoricoIntegracaoPlaylist,
    TestePainel,
    OperacaoIntegracaoPainel,
)
from whatsapp_integration.models import (
    HistoricoMensagemAutomatica, UserInstance
)



from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .integrations.playlists.factory import get_playlist_provider


# ============================================
# IMPORTS DO PROJETO (FORMS)
# ============================================
from .forms import (
    AtualizacaoForm,
    ClienteForm,
    ConfiguracaoForm,
    ConfiguracaoMensagemForm,
    MensagemConfiguradaForm,
    ServicoForm,
    TagForm,
    TutorialForm,
    UploadFileForm,
)

# ============================================
# IMPORTS DO PROJETO (SERVIÇOS/HELPERS)
# ============================================
from .helpers import get_whatsapp_api_and_headers
from .services import CreditoService, buscar_jogos_do_dia
from .tasks import enviar_mensagem
from .utils import gerar_relatorio_financeiro, get_grupo_renovacao
from .integracoes_paineis import (
    get_painel_adapter, IntegracaoPainelErro, ContaNaoEncontrada, ContaAmbigua,
)






logger = logging.getLogger(__name__)
User = get_user_model()

def login_view(request):
    """
    View de login com verificação de código
    """
    if request.user.is_authenticated:
        return redirect(get_redirect_url(request.user))
    
    if request.method == 'GET':
        # Gera código de verificação para login
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        verification_code = VerificationCode.generate_code(
            code_type='login',
            session_key=session_key
        )
        
        next_param = request.GET.get('next', '')
        
        return render(request, 'registration/login.html', {
            'login_verification_code': verification_code.code,
            'next': next_param
        })
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        verification_code = request.POST.get('verification_code', '').strip()
        next_url = request.POST.get('next', '')
        
        # Validações
        if not username or not password:
            messages.error(request, "Preencha usuário e senha.")
            return render_login_with_code(request, next_url)
        
        if not verification_code:
            messages.error(request, "Digite o código de verificação.")
            return render_login_with_code(request, next_url)
        
        # Verifica código
        try:
            code_obj = VerificationCode.objects.get(
                code=verification_code,
                code_type='login',
                is_used=False,
                expires_at__gt=timezone.now()
            )
        except VerificationCode.DoesNotExist:
            messages.error(request, "Código de verificação inválido ou expirado.")
            return render_login_with_code(request, next_url)
        
        # Autentica usuário
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            messages.error(request, "Usuário ou senha incorretos.")
            return render_login_with_code(request, next_url)
        
        if not user.is_active:
            messages.error(request, "Usuário desativado.")
            return render_login_with_code(request, next_url)
        
        # Verifica tipo de usuário
        if user.tipo_usuario not in ['admin', 'revenda'] and not user.is_superuser:
            messages.error(request, "Acesso restrito a revendedores e administradores.")
            return render_login_with_code(request, next_url)
        
        # Login bem-sucedido
        code_obj.mark_as_used()
        login(request, user)
        request.session['user_tipo'] = user.tipo_usuario
        
        return redirect(get_redirect_url(user, next_url))
# clientes/views_backup.py

@login_required
def pagina_backup(request):
    """Página principal de gerenciamento de backup"""
    # Verifica permissão
    if request.user.tipo_usuario not in ['admin', 'revenda'] and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('dashboard')
    
    # Backup schedule do usuário
    schedule, created = BackupSchedule.objects.get_or_create(
        usuario=request.user,
        defaults={
            'frequencia': '24h',
            'manter_ultimos': 7,
            'ativo': False
        }
    )
    
    # Lista de backups realizados
    backups_list = BackupHistory.objects.filter(usuario=request.user).order_by('-data_criacao')
    
    # Paginação
    paginator = Paginator(backups_list, 20)
    page = request.GET.get('page', 1)
    backups = paginator.get_page(page)
    
    # Espaço em disco
    backup_dir = settings.BASE_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    total_size = sum(f.stat().st_size for f in backup_dir.glob('*.gz'))
    total_backups = len(list(backup_dir.glob('*.gz')))
    
    context = {
        'schedule': schedule,
        'backups': backups,
        'total_backups': total_backups,
        'total_size': total_size,
        'total_size_mb': total_size / (1024 * 1024),
        'frequencias': BackupSchedule.FREQUENCIA_CHOICES,
    }
    
    return render(request, 'clientes/backup.html', context)



def register_view(request):
    """
    View de cadastro ONLINE (pelo site)
    Apenas estes recebem mensagem de boas-vindas
    """
    if request.method == 'POST':
        fullname = request.POST.get('fullname', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        whatsapp = request.POST.get('whatsapp', '').strip()
        verification_code = request.POST.get('whatsapp_verification_code', '').strip()
        
        # Validações...
        if not all([fullname, username, password, email, whatsapp]):
            messages.error(request, "Preencha todos os campos.")
            return redirect('login')
        
        whatsapp_number = re.sub(r'\D', '', whatsapp)
        
        # Verifica código...
        try:
            code_obj = VerificationCode.objects.get(
                code=verification_code,
                code_type='whatsapp',
                is_used=False,
                expires_at__gt=timezone.now(),
                whatsapp_number=whatsapp_number
            )
        except VerificationCode.DoesNotExist:
            messages.error(request, "Código de verificação inválido ou expirado.")
            return redirect('login')
        
        # Verifica se usuário já existe...
        if User.objects.filter(username=username).exists():
            messages.error(request, "Nome de usuário já existe.")
            return redirect('login')
        
        try:
            # 🔴 CRIA USUÁRIO MARCADO COMO CADASTRO ONLINE
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                nome=fullname,
                whatsapp=whatsapp,
                tipo_usuario='cliente',
                is_active=True,
                cadastro_online=True  # ← MARCA COMO CADASTRO ONLINE
            )
            
            code_obj.mark_as_used()
            
            # 🔴 ENVIA BOAS-VINDAS APENAS PARA CADASTRO ONLINE
            welcome_sent = send_welcome_message_online(user, whatsapp_number)
            
            if welcome_sent:
                messages.success(request, 
                    "✅ Conta criada com sucesso! Enviamos uma mensagem de boas-vindas para seu WhatsApp.")
            else:
                messages.success(request, 
                    "✅ Conta criada com sucesso! Faça login para acessar o sistema.")
            
            # Registra atividade
            LogAtividade.registrar(
                request=request,
                usuario=user,
                tipo_acao='cadastro_online',
                descricao=f"Novo usuário cadastrado ONLINE: {user.username}",
                status='sucesso'
            )
            
            logger.info("✅ Cadastro online concluído para usuário %s", username)
            
            return redirect('login')
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar usuário: {e}")
            messages.error(request, "Erro ao criar conta. Tente novamente.")
            return redirect('login')
    
    return redirect('login')


@require_POST
def send_whatsapp_code(request):
    """
    Envia código de verificação via WhatsApp
    Usa a Evolution API configurada por variáveis de ambiente.
    Instância: gestor (conectada)
    """
    whatsapp_number = request.POST.get('whatsapp', '').strip()
    whatsapp_number = re.sub(r'\D', '', whatsapp_number)
    
    if len(whatsapp_number) < 10:
        return JsonResponse({
            'success': False,
            'message': 'Número de WhatsApp inválido'
        })
    
    # Vincula o desafio de cadastro à sessão atual. Assim o front-end não
    # consegue liberar um cadastro apenas alterando JavaScript no navegador.
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    VerificationCode.objects.filter(
        code_type='whatsapp',
        session_key=session_key,
        is_used=False,
    ).update(is_used=True)
    request.session['registration_whatsapp_number'] = whatsapp_number
    request.session.pop('registration_whatsapp_verified_at', None)
    request.session.modified = True

    # Gera código de verificação
    verification_code = VerificationCode.generate_code(
        code_type='whatsapp',
        session_key=session_key,
        whatsapp_number=whatsapp_number,
        length=6
    )
    
    BASE_URL = getattr(settings, 'EVOLUTION_API_BASE_URL', '').rstrip('/')
    API_KEY = getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', '')
    INSTANCE_NAME = getattr(settings, 'EVOLUTION_RECOVERY_INSTANCE', 'gestor')
    if not BASE_URL or not API_KEY:
        logger.error('Evolution API não configurada para envio de código de verificação.')
        return JsonResponse({
            'success': False,
            'message': 'Serviço de WhatsApp temporariamente indisponível.'
        }, status=503)
    
    logger.info("📤 Enviando código de verificação para final %s", whatsapp_number[-4:])
    
    try:
        # Formata o número (Brasil = 55 + DDD + número)
        if len(whatsapp_number) == 11:  # 11 dígitos = DDD + 9 + número
            formatted_number = f"55{whatsapp_number}"
        elif len(whatsapp_number) == 10:  # 10 dígitos = DDD + número
            formatted_number = f"55{whatsapp_number}"
        elif whatsapp_number.startswith('55'):
            formatted_number = whatsapp_number
        else:
            formatted_number = f"55{whatsapp_number}"
        
        # Mensagem personalizada
        message = (
            f"🔐 *CÓDIGO DE VERIFICAÇÃO*\n\n"
            f"Olá! Seu código de verificação é:\n\n"
            f"*{verification_code.code}*\n\n"
            f"⚠️ Não compartilhe este código com ninguém.\n"
            f"⏰ Este código expira em 5 minutos.\n\n"
            f"Se você não solicitou este código, ignore esta mensagem."
        )
        
        # Headers da API
        headers = {
            'apikey': API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Payload
        payload = {
            "number": formatted_number,
            "options": {
                "delay": 500,
                "presence": "composing"
            },
            "text": message
        }
        
        # URL da API
        url = f"{BASE_URL}/message/sendText/{INSTANCE_NAME}"
        
        logger.debug("Preparando envio do código de verificação pela Evolution API.")
        
        # Envia a mensagem
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📥 Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            logger.info("✅ Código de verificação enviado com sucesso.")
            
            # Registra no histórico
            try:
                HistoricoMensagemAutomatica.objects.create(
                    cliente=None,
                    data_tentativa=timezone.now(),
                    data_envio=timezone.now(),
                    status='ENVIADO',
                    mensagem_final_enviada=message,
                    detalhes='Código de verificação WhatsApp enviado'
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar histórico: {e}")
            
            return JsonResponse({
                'success': True,
                'message': 'Código enviado com sucesso! Verifique seu WhatsApp.'
            })
        else:
            logger.error("❌ Evolution API recusou a solicitação: HTTP %s", response.status_code)
            return JsonResponse({
                'success': False,
                'message': f'Erro ao enviar código (Status: {response.status_code}). Tente novamente.'
            })
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Erro de conexão: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Serviço de mensagens indisponível. Tente novamente mais tarde.'
        })
        
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout na requisição")
        return JsonResponse({
            'success': False,
            'message': 'Tempo de conexão esgotado. Tente novamente.'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': 'Erro ao enviar código. Tente novamente.'
        })
    


    
@require_POST
def verify_whatsapp_code(request):
    """Valida o código de cadastro exclusivamente para a sessão e número solicitados."""
    code = request.POST.get('code', '').strip()
    whatsapp_number = request.session.get('registration_whatsapp_number', '')
    session_key = request.session.session_key or ''

    if not code or not whatsapp_number or not session_key:
        return JsonResponse({
            'success': False,
            'message': 'Sessão de verificação expirada. Solicite outro código.'
        }, status=400)

    code_obj = VerificationCode.objects.filter(
        code=code,
        code_type='whatsapp',
        is_used=False,
        expires_at__gt=timezone.now(),
        session_key=session_key,
        whatsapp_number=whatsapp_number,
    ).first()

    if not code_obj:
        return JsonResponse({
            'success': False,
            'message': 'Código inválido ou expirado'
        }, status=400)

    code_obj.mark_as_used()
    request.session['registration_whatsapp_verified_at'] = timezone.now().timestamp()
    request.session.modified = True
    return JsonResponse({'success': True, 'message': 'Código válido'})

def render_login_with_code(request, next_url=None):
    """
    Renderiza login com novo código
    """
    verification_code = VerificationCode.generate_code(
        code_type='login',
        session_key=request.session.session_key
    )
    
    return render(request, 'registration/login.html', {
        'login_verification_code': verification_code.code,
        'next': next_url or ''
    })

def get_redirect_url(user, next_url=None):
    """
    Determina para onde redirecionar
    """
    if next_url and next_url.strip() and next_url != 'None':
        if next_url.startswith('/') and not next_url.startswith('//'):
            return next_url
    
    if user.is_superuser or user.tipo_usuario in ['admin', 'revenda']:
        return 'dashboard'
    elif user.tipo_usuario == 'cliente':
        return 'cliente'
    
    return 'dashboard'


@login_required
@require_GET
def get_mensagem_cliente(request, cliente_id):
    clientes = CustomUser.objects.all()
    if not request.user.is_superuser:
        clientes = clientes.filter(dono=request.user)
    cliente = get_object_or_404(clientes, id=cliente_id)
    usuario_logado = request.user

    # Calcula o valor total a pagar (lógica do listar_clientes)
    if cliente.saldo < 0:
        valor_total_a_pagar = cliente.valor_a_pagar + abs(cliente.saldo)
    else:
        valor_total_a_pagar = max(0, cliente.valor_a_pagar - cliente.saldo)

    # Calcule a diferença de dias entre hoje e a data de vencimento
    dias_vencimento = (cliente.data_vencimento - timezone.now().date()).days

    # Busca APENAS a mensagem do REVENDEDOR LOGADO
    mensagem_configurada = MensagemConfigurada.objects.filter(
        criterio_dias=dias_vencimento,
        configuracao__usuario=usuario_logado  # Filtra direto pelo usuário da configuração
    ).first()

    if mensagem_configurada:
        mensagem = mensagem_configurada.substituir_variaveis(cliente)
    else:
        mensagem = ""

    return JsonResponse({
        "whatsapp": cliente.whatsapp,
        "mensagem_texto": mensagem,
        "criterio_dias": dias_vencimento,
    })







def render_login_with_new_code(request, next_url=None):
    """
    Renderiza o template de login com um novo código de verificação
    """
    verification_code = VerificationCode.generate_code(request.session.session_key)
    
    context = {
        'verification_code': verification_code.code,
        'next': next_url or ''
    }
    
    return render(request, 'registration/login.html', context)






@login_required
def cliente_view(request):
    """
    View simplificada para clientes
    """
    cliente = request.user
    
    # Redireciona se não for cliente
    if cliente.tipo_usuario != 'cliente':
        return redirect('dashboard')
    
    # Calcula valores
    valor_a_pagar = cliente.valor_a_pagar or Decimal('0.00')
    saldo = cliente.saldo or Decimal('0.00')
    
    if saldo < 0:
        valor_total_a_pagar = valor_a_pagar + abs(saldo)
    else:
        valor_total_a_pagar = max(Decimal('0.00'), valor_a_pagar - saldo)
    
    # Relatórios
    relatorio_financeiro = RelatorioFinanceiro.objects.filter(
        cliente=cliente
    ).order_by('-data_geracao')[:10]
    
    return render(request, 'clientes/cliente.html', {
        'cliente': cliente,
        'relatorio_financeiro': relatorio_financeiro,
        'valor_total_a_pagar': valor_total_a_pagar,
    })





@never_cache
@login_required
def listar_clientes(request):
    termo_pesquisa = request.GET.get("termo", "").strip()
    filtro_plano = request.GET.get("plano", "").strip()
    filtro_status = request.GET.get("status", "active")
    
    clientes = CustomUser.objects.filter(dono=request.user)\
        .select_related('plano')\
        .prefetch_related('tags')
    
    config_usuario = Configuracao.objects.filter(usuario=request.user).first()
    
    if filtro_status == 'inactive':
        clientes = clientes.filter(is_active=False)
    else:
        clientes = clientes.filter(is_active=True)
    
    if termo_pesquisa:
        clientes = clientes.filter(
            Q(nome__icontains=termo_pesquisa) |
            Q(username__icontains=termo_pesquisa) |
            Q(whatsapp__icontains=termo_pesquisa) |
            Q(login_externo__icontains=termo_pesquisa)
        )
    
    if filtro_plano:
        clientes = clientes.filter(plano__nome=filtro_plano)
    
    clientes = clientes.order_by('data_vencimento', 'nome')
    
    page_size = min(int(request.GET.get('page_size', 100)), 500)
    paginator = Paginator(clientes, page_size)
    page_number = request.GET.get('page', 1)
    
    try:
        clientes_paginados = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        clientes_paginados = paginator.page(1)
    
    cliente_ids = [c.id for c in clientes_paginados]

    clientes_com_playlist = set()
    if cliente_ids:
        clientes_com_playlist = set(
            IntegracaoPlaylistCliente.objects.filter(
                dono=request.user, cliente_id__in=cliente_ids
            ).values_list("cliente_id", flat=True)
        )
    
    # RELATÓRIOS
    relatorios_dict = {}
    if cliente_ids:
        relatorios = RelatorioFinanceiro.objects.filter(
            cliente_id__in=cliente_ids
        ).order_by('-data_geracao')
        for r in relatorios:
            if r.cliente_id not in relatorios_dict:
                relatorios_dict[r.cliente_id] = []
            if len(relatorios_dict[r.cliente_id]) < 5:
                relatorios_dict[r.cliente_id].append(r)
    
    # INDICAÇÕES
    indicacoes_dict = {}
    if cliente_ids:
        indicacoes = Indicacao.objects.filter(
            cliente_indicador_id__in=cliente_ids
        ).select_related('cliente_indicado')
        for ind in indicacoes:
            if ind.cliente_indicador_id not in indicacoes_dict:
                indicacoes_dict[ind.cliente_indicador_id] = []
            indicacoes_dict[ind.cliente_indicador_id].append(ind)
    
    # DUPLICADOS
    duplicados_map = {}
    if cliente_ids:
        
        duplicados_query = CustomUser.objects.filter(
            dono=request.user,
            is_active=True,
            login_externo__isnull=False
        ).values('login_externo').annotate(total=Count('id')).filter(total__gt=1)
        for item in duplicados_query:
            duplicados_map[item['login_externo']] = item['total']
    
        # COMPARTILHADOS (clientes com mesmo login_externo)
    compartilhados_map = {}
    if cliente_ids:
        
        # Pega os logins que aparecem mais de uma vez
        logins_duplicados = CustomUser.objects.filter(
            dono=request.user,
            is_active=True,
            login_externo__isnull=False
        ).values('login_externo').annotate(total=Count('id')).filter(total__gt=1)
        
        for item in logins_duplicados:
            login = item['login_externo']
            # Busca todos os clientes com esse login
            comps = CustomUser.objects.filter(
                dono=request.user,
                login_externo=login,
                is_active=True
            ).values('id', 'nome', 'data_vencimento', 'whatsapp_avatar_url') 
            compartilhados_map[login] = list(comps)



    # PROCESSAR CLIENTES
    hoje = timezone.localdate()
    for cliente in clientes_paginados:
        cliente.duplicados_count = duplicados_map.get(cliente.login_externo, 1) if cliente.login_externo else 1
        cliente.tem_playlist_cadastrada = cliente.id in clientes_com_playlist
                # Compartilhados
        if cliente.login_externo and cliente.login_externo in compartilhados_map:
            cliente.compartilhados = compartilhados_map[cliente.login_externo]
        else:
            cliente.compartilhados = []
        valor_a_pagar = cliente.valor_a_pagar or Decimal('0.00')
        saldo = cliente.saldo or Decimal('0.00')
        if saldo < 0:
            cliente.valor_total_a_pagar = valor_a_pagar + abs(saldo)
        else:
            cliente.valor_total_a_pagar = max(Decimal('0.00'), valor_a_pagar - saldo)
        
        if not cliente.is_active:
            cliente.status_vencimento = "Inativo"
            cliente.porcentagem_vencimento = 10
        elif cliente.data_vencimento:
            dias = (cliente.data_vencimento - hoje).days
            if dias < 0:
                cliente.status_vencimento = "Vencido"
                cliente.porcentagem_vencimento = 100
            elif dias == 0:
                cliente.status_vencimento = "Vence Hoje"
                cliente.porcentagem_vencimento = 95
            elif dias <= 3:
                cliente.status_vencimento = "Vence em Breve"
                cliente.porcentagem_vencimento = 50
            elif dias <= 7:
                cliente.status_vencimento = "Vence em Breve"
                cliente.porcentagem_vencimento = 60
            elif dias <= 15:
                cliente.status_vencimento = "Em Dia"
                cliente.porcentagem_vencimento = 70
            elif dias <= 30:
                cliente.status_vencimento = "Em Dia"
                cliente.porcentagem_vencimento = 85
            else:
                cliente.status_vencimento = "Em Dia"
                cliente.porcentagem_vencimento = 100
        else:
            cliente.status_vencimento = "Em Dia"
            cliente.porcentagem_vencimento = 75
        
        cliente.has_avatar = bool(
            cliente.whatsapp_avatar_url and
            cliente.whatsapp_avatar_status == 'found' and
            cliente.is_avatar_valid()
        )
        
        cliente.relatorios_carregados = relatorios_dict.get(cliente.id, [])
        cliente.indicacoes_list = indicacoes_dict.get(cliente.id, [])
        cliente.valor_servico_exibicao = cliente.valor_servico or Decimal('0.00')
    
    # PLANOS
    # PLANOS - query CORRIGIDA (respeita o filtro de status)
    if filtro_status == 'inactive':
        # Mostrar APENAS planos dos clientes DESATIVADOS
        planos = Servico.objects.filter(
            clientes__dono=request.user,
            clientes__is_active=False
        ).annotate(
            clientes_count=Count('clientes', filter=Q(
                clientes__is_active=False,
                clientes__dono=request.user
            ))
        ).filter(clientes_count__gt=0).distinct().order_by('nome')
    else:
        # Mostrar APENAS planos dos clientes ATIVOS
        planos = Servico.objects.filter(
            clientes__dono=request.user,
            clientes__is_active=True
        ).annotate(
            clientes_count=Count('clientes', filter=Q(
                clientes__is_active=True,
                clientes__dono=request.user
            ))
        ).filter(clientes_count__gt=0).distinct().order_by('nome')
        
    total_clientes = clientes.count()
    total_clientes_ativos = CustomUser.objects.filter(dono=request.user, is_active=True).count()
    total_clientes_desativados = CustomUser.objects.filter(dono=request.user, is_active=False).count()
    
    context = {
        'clientes': clientes_paginados,
        'planos': planos,
        'termo_pesquisa': termo_pesquisa,
        'filtro_plano': filtro_plano,
        'filtro_status': filtro_status,
        'total_clientes': total_clientes,
        'total_clientes_ativos': total_clientes_ativos,
        'total_clientes_desativados': total_clientes_desativados,
        'page_size': page_size,
        'hoje': hoje,
        'config': config_usuario,
    }
    
    return render(request, 'clientes/listar_clientes.html', context)

# No views.py

def buscar_planos_ajax(request):
    """Retorna planos filtrados por status para AJAX"""
    filtro_status = request.GET.get('status', 'active')
    
    if filtro_status == 'inactive':
        planos = Servico.objects.filter(
            clientes__dono=request.user,
            clientes__is_active=False
        ).annotate(
            clientes_count=Count('clientes', filter=Q(
                clientes__is_active=False,
                clientes__dono=request.user
            ))
        ).filter(clientes_count__gt=0).distinct().order_by('nome')
    else:
        planos = Servico.objects.filter(
            clientes__dono=request.user,
            clientes__is_active=True
        ).annotate(
            clientes_count=Count('clientes', filter=Q(
                clientes__is_active=True,
                clientes__dono=request.user
            ))
        ).filter(clientes_count__gt=0).distinct().order_by('nome')
    
    data = {
        'planos': [
            {
                'nome': p.nome,
                'cor': p.cor or '#6c757d',
                'clientes_count': p.clientes_count
            } for p in planos
        ]
    }
    
    return JsonResponse(data)



@login_required
def obter_avatar_whatsapp(request, numero):
    """
    Busca avatar do WhatsApp com CACHE AGRESSIVO
    """
    from django.conf import settings
    
    # Limpa o número
    numero_limpo = ''.join(filter(str.isdigit, numero))
    
    # 🔴 Gera chave única para este número
    cache_key = f'avatar_wp_{numero_limpo}'
    
    # 🔴 VERIFICA CACHE DO DJANGO PRIMEIRO (mais rápido)
    cached_avatar = cache.get(cache_key)
    if cached_avatar:
        response = HttpResponse(cached_avatar, content_type='image/jpeg')
        # 🔴 Cache no navegador por 7 dias
        patch_response_headers(response, cache_timeout=7*24*60*60)
        return response
    
    try:
        # 🔴 CONFIGURAÇÕES DA API
        BASE_URL = settings.EVOLUTION_API_BASE_URL.rstrip('/')
        API_KEY = settings.EVOLUTION_GLOBAL_API_KEY
        
        headers = {
            'apikey': API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Formata o número
        if len(numero_limpo) == 11:
            formatted_number = f"55{numero_limpo}"
        elif len(numero_limpo) == 10:
            formatted_number = f"55{numero_limpo}"
        elif numero_limpo.startswith('55'):
            formatted_number = numero_limpo
        else:
            formatted_number = f"55{numero_limpo}"
        
        # Remove 55 duplicado
        if formatted_number.startswith('5555'):
            formatted_number = formatted_number[2:]
        
        # 🔴 Busca URL da foto
        url = f"{BASE_URL}/chat/fetchProfilePictureUrl/gestor"
        payload = {"number": formatted_number}
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            profile_pic_url = data.get('profilePictureUrl')
            
            if profile_pic_url:
                # 🔴 Busca a imagem real
                img_response = requests.get(profile_pic_url, timeout=10)
                
                if img_response.status_code == 200:
                    # 🔴 SALVA NO CACHE POR 30 DIAS
                    cache.set(cache_key, img_response.content, timeout=30*24*60*60)
                    
                    response = HttpResponse(img_response.content, content_type='image/jpeg')
                    # 🔴 Cache no navegador por 7 dias
                    patch_response_headers(response, cache_timeout=7*24*60*60)
                    return response
        
        # Fallback: retorna avatar com letra
        return gerar_avatar_fallback_nome(request.user)
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar avatar: {e}")
        return gerar_avatar_fallback_nome(request.user)


def gerar_avatar_fallback_nome(user):
    """
    Gera avatar padrão com a primeira letra do nome do usuário
    """
    # Pega a primeira letra do nome
    if user.nome:
        letra = user.nome[0].upper()
    elif user.first_name:
        letra = user.first_name[0].upper()
    elif user.get_full_name():
        letra = user.get_full_name()[0].upper()
    elif user.username:
        letra = user.username[0].upper()
    else:
        letra = '?'
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#667eea"/>
                <stop offset="100%" style="stop-color:#764ba2"/>
            </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#grad)"/>
        <text x="50" y="67" text-anchor="middle" fill="white" font-size="40" font-family="Arial, sans-serif" font-weight="bold">{letra}</text>
    </svg>'''
    
    return HttpResponse(svg.encode('utf-8'), content_type='image/svg+xml')


def gerar_avatar_fallback_numero(numero):
    """
    Gera avatar padrão com o último dígito do número (fallback antigo)
    Mantido para compatibilidade, mas não é mais usado
    """
    if numero and len(numero) > 0:
        letra = numero[-1].upper()
    else:
        letra = '?'
    
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#667eea"/>
                <stop offset="100%" style="stop-color:#764ba2"/>
            </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#grad)"/>
        <text x="50" y="67" text-anchor="middle" fill="white" font-size="40" font-family="Arial, sans-serif" font-weight="bold">{letra}</text>
    </svg>'''
    
    return HttpResponse(svg.encode('utf-8'), content_type='image/svg+xml')

# Nova view para ativar/desativar um cliente
@login_required
@require_POST # Garante que esta view só aceite requisições POST
def ativar_desativar_cliente(request, cliente_id):
    try:
        # Busca o cliente, garantindo que pertença ao usuário logado
        cliente = get_object_or_404(CustomUser, pk=cliente_id, dono=request.user)

        # Alterna o status is_active
        cliente.is_active = not cliente.is_active
        cliente.save()

        # Retorna uma resposta JSON de sucesso
        return JsonResponse({
            'status': 'success',
            'message': f'Cliente {cliente.nome} foi {"ativado" if cliente.is_active else "desativado"} com sucesso!',
            'is_active': cliente.is_active # Retorna o novo status
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Cliente não encontrado ou você não tem permissão.'}, status=404)
    except Exception as e:
        # Captura outros erros
        return JsonResponse({'status': 'error', 'message': f'Erro interno: {e}'}, status=500)




@login_required
@transaction.atomic
def cadastrar_cliente(request):
    """View para cadastrar novos clientes"""
    
    if request.user.tipo_usuario not in ['admin', 'revenda']:
        raise PermissionDenied("Você não tem permissão para cadastrar clientes.")
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, user=request.user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Cria a instância na memória
                    cliente = form.save(commit=False)
                    
                    # 2. Define dados básicos obrigatórios
                    tipo_usuario = form.cleaned_data.get('tipo_usuario', 'cliente')
                    if request.user.tipo_usuario == 'revenda':
                        tipo_usuario = 'cliente'
                    
                    cliente.dono = request.user
                    cliente.tipo_usuario = tipo_usuario
                    cliente.is_active = True
                    cliente.cadastro_online = False
                    
                    plano = form.cleaned_data.get('plano')

                    login_externo = request.POST.get(
                        'login_externo',
                        ''
                    ).strip()

                    senha_leitura = request.POST.get(
                        'senha_leitura',
                        ''
                    ).strip()

                    cliente.login_externo = login_externo
                    cliente.senha_leitura = senha_leitura

                    if not cliente.nome:
                        cliente.nome = login_externo or 'Cliente'

                    # 3. VERIFICA MULTIPLICADOR (ANTES DE SALVAR NO DB)
                    is_adicional, total_existentes, erro_msg = CreditoService.verificar_multiplicador(
                        plano=plano,
                        login_externo=login_externo,
                        senha_leitura=senha_leitura,
                        dono=request.user,
                        user_model=CustomUser
                    )
                    
                    if erro_msg:
                        messages.error(request, erro_msg)
                        return render(request, 'clientes/cadastrar_cliente.html', {'form': form, 'user_tipo': request.user.tipo_usuario})

                    # ==========================================
                    # 🔥 PRIMEIRO SAVE: GERAR O ID (PRIMARY KEY)
                    # ==========================================
                    # Precisamos do ID para associar tags, créditos e financeiro
                    cliente.save() 

                    # 4. DETERMINA SE FOI MARCADO COMO PAGO
                    processar_pagamento = request.POST.get('pago') == 'on'
                    
                    # Pega o valor que o usuário digitou, se não tiver, usa o valor do plano
                    valor_plano_str = form.cleaned_data.get('valor_a_pagar')
                    if valor_plano_str:
                        try:
                            valor_plano = Decimal(str(valor_plano_str))
                        except:
                            valor_plano = plano.valor if plano and plano.valor else Decimal('0.00')
                    else:
                        valor_plano = plano.valor if plano and plano.valor else Decimal('0.00')
                        
                    custo_final = Decimal('0.00')

                    if processar_pagamento:
                        # Se não for adicional, define custo base e tenta consumir crédito
                        if not is_adicional and plano:
                            custo_base = plano.custos if plano.custos else Decimal('0.00')
                            
                            # Agora o 'cliente' já tem ID, então o service funciona!
                            sucesso, msg, custo_real = CreditoService.consumir_credito_cliente(
                                plano=plano,
                                cliente=cliente,
                                quantidade=1,
                                is_renovacao=False
                            )
                            
                            if not sucesso:
                                # Força erro para dar rollback no 'cliente.save()' anterior
                                raise ValueError(msg)
                            
                            custo_final = custo_real if custo_real else custo_base
                        
                        # Atualiza o cliente com os valores finais
                        cliente.valor_servico = custo_final if not is_adicional else Decimal('0.00')
                        cliente.valor_a_pagar = valor_plano
                        cliente.save(update_fields=['valor_servico', 'valor_a_pagar'])
                        
                        # GERA FINANCEIRO
                        try:
                            grupo = get_grupo_renovacao(cliente)
                            gerar_relatorio_financeiro(
                                cliente=cliente,
                                valor_servico=cliente.valor_servico,
                                valor_pago=valor_plano,
                                is_manual_entry=False,
                                numero_renovacao=0,
                                grupo_renovacao=grupo
                            )
                        except Exception as e:
                            logger.error(f"Erro ao gerar financeiro: {e}")
                    else:
                        # SE NÃO FOI PAGO: Garante que o custo seja zero no sistema
                        cliente.valor_servico = Decimal('0.00')
                        cliente.valor_a_pagar = Decimal('0.00')
                        cliente.save(update_fields=['valor_servico', 'valor_a_pagar'])

                    # 5. ASSOCIA TAGS (Agora que temos ID)
                    tag_ids = request.POST.getlist('tags')
                    if tag_ids:
                        tags_validas = Tag.objects.filter(id__in=tag_ids, usuario=request.user)
                        cliente.tags.set(tags_validas)
                    
                    if not cliente.link_acesso:
                        cliente.link_acesso = uuid.uuid4()
                        cliente.save(update_fields=['link_acesso'])

                    # 6. LOGS E ACÇÕES FINAIS
                    if request.POST.get('enviar_mensagem') == 'on' and cliente.whatsapp:
                        try: enviar_mensagem_boas_vindas(cliente, user=request.user)
                        except: pass
                    
                    from clientes.utils_avatar import atualizar_avatar_rapido
                    atualizar_avatar_rapido(cliente, forcar=True)

                    LogAtividade.registrar(
                        request=request, usuario=request.user, tipo_acao='create',
                        descricao=f"Cadastrou: {cliente.nome} ({'Pago' if processar_pagamento else 'Não Pago'})",
                        modelo_afetado='CustomUser', objeto_id=cliente.id
                    )
                    
                    messages.success(request, f"✅ Cliente {'e financeiro' if processar_pagamento else ''} cadastrado com sucesso!")
                    return redirect('listar_clientes')

            except ValueError as ve:
                # Erro controlado (ex: falta de crédito)
                messages.error(request, f"❌ {str(ve)}")
            except Exception as e:
                # Erro inesperado
                logger.error(f"Erro no cadastro: {e}", exc_info=True)
                messages.error(request, f"❌ Erro interno: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors: messages.error(request, f"{field}: {error}")
    else:
        form = ClienteForm(user=request.user)
    
    return render(request, 'clientes/cadastrar_cliente.html', {'form': form, 'user_tipo': request.user.tipo_usuario})



#===============================
# VIEW DE CADASTRO ONLINE (REGISTER)
# ============================================================
def register_view(request):
    """
    View de cadastro ONLINE (pelo site)
    APENAS ESTA envia mensagem de boas-vindas via WhatsApp
    """
    if request.method == 'POST':
        fullname = request.POST.get('fullname', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        whatsapp = request.POST.get('whatsapp', '').strip()
        verification_code = request.POST.get('whatsapp_verification_code', '').strip()
        
        # Validações básicas
        if not all([fullname, username, password, email, whatsapp]):
            messages.error(request, "Preencha todos os campos.")
            return redirect('login')
        
        # Limpa número do WhatsApp
        whatsapp_number = re.sub(r'\D', '', whatsapp)
        
        # Verifica código de verificação
        try:
            code_obj = VerificationCode.objects.get(
                code=verification_code,
                code_type='whatsapp',
                is_used=False,
                expires_at__gt=timezone.now(),
                whatsapp_number=whatsapp_number
            )
        except VerificationCode.DoesNotExist:
            messages.error(request, "Código de verificação inválido ou expirado.")
            return redirect('login')
        
        # Verifica se usuário já existe
        if User.objects.filter(username=username).exists():
            messages.error(request, "Nome de usuário já existe.")
            return redirect('login')
        
        # Verifica se WhatsApp já está cadastrado
        if User.objects.filter(whatsapp=whatsapp).exists():
            messages.error(request, "Este WhatsApp já está cadastrado.")
            return redirect('login')
        
        try:
            # 🔴 CRIA USUÁRIO MARCADO COMO CADASTRO ONLINE
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                nome=fullname,
                whatsapp=whatsapp,
                tipo_usuario='cliente',
                is_active=True,
                cadastro_online=True  # ← MARCA COMO CADASTRO ONLINE
            )
            
            # Marca código como usado
            code_obj.mark_as_used()
            
            # 🔴 ENVIA MENSAGEM DE BOAS-VINDAS (APENAS PARA CADASTRO ONLINE)
            try:
                welcome_sent = send_welcome_message_online(user, whatsapp_number)
                
                if welcome_sent:
                    messages.success(request, 
                        "✅ Conta criada com sucesso! Enviamos uma mensagem de boas-vindas para seu WhatsApp.")
                else:
                    messages.success(request, 
                        "✅ Conta criada com sucesso! Faça login para acessar o sistema.")
            except Exception as e:
                logger.error(f"❌ Erro ao enviar boas-vindas: {e}")
                messages.success(request, "✅ Conta criada com sucesso! Faça login para acessar o sistema.")
            
            # Registra atividade
            try:
                LogAtividade.registrar(
                    request=request,
                    usuario=user,
                    tipo_acao='cadastro_online',
                    descricao=f"Novo usuário cadastrado ONLINE: {user.username}",
                    status='sucesso'
                )
            except:
                pass
            
            logger.info("✅ Cadastro online concluído para usuário %s", username)
            
            return redirect('login')
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar usuário: {e}")
            messages.error(request, "Erro ao criar conta. Tente novamente.")
            return redirect('login')
    
    return redirect('login')


# ============================================================
# FUNÇÃO DE BOAS-VINDAS (APENAS CADASTRO ONLINE)
# ============================================================
def send_welcome_message_online(user, whatsapp_number):
    """
    Envia mensagem de boas-vindas EXCLUSIVA para cadastro online
    
    Args:
        user: Usuário recém-criado (cadastro_online=True)
        whatsapp_number: Número do WhatsApp (apenas dígitos)
    
    Returns:
        bool: True se enviou com sucesso, False caso contrário
    """
    # 🔴 VERIFICAÇÃO DE SEGURANÇA: Apenas cadastro online
    if not user.cadastro_online:
        logger.info(f"ℹ️ Usuário {user.username} NÃO é cadastro online - pulando boas-vindas")
        return False
    
    try:
        # Configurações da API centralizadas no ambiente
        BASE_URL = getattr(settings, 'EVOLUTION_API_BASE_URL', '').rstrip('/')
        API_KEY = getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', '')
        INSTANCE_NAME = getattr(settings, 'EVOLUTION_RECOVERY_INSTANCE', 'gestor')
        if not BASE_URL or not API_KEY:
            logger.error('Evolution API não configurada para mensagem de boas-vindas.')
            return False
        
        # Formata o número
        if len(whatsapp_number) == 11:
            formatted_number = f"55{whatsapp_number}"
        elif len(whatsapp_number) == 10:
            formatted_number = f"55{whatsapp_number}"
        elif whatsapp_number.startswith('55') and len(whatsapp_number) >= 12:
            formatted_number = whatsapp_number
        else:
            formatted_number = f"55{whatsapp_number}"
        
        # Remove 55 duplicado
        if formatted_number.startswith('5555'):
            formatted_number = formatted_number[2:]
        
        # 🔴 MENSAGEM DE BOAS-VINDAS (CADASTRO ONLINE)
        welcome_message = (
            f"🎉 *BEM-VINDO(A) AO SISTEMA!*\n\n"
            f"Olá *{user.nome or user.username}*!\n\n"
            f"Seu cadastro foi realizado com sucesso! ✅\n\n"
            f"📋 *Dados da sua conta:*\n"
            f"👤 Usuário: *{user.username}*\n"
            f"📧 E-mail: *{user.email or 'Não informado'}*\n\n"
            f"🔐 Acesse o sistema em:\n"
            f"👉 https://gestor.tlsprimesolutions.com.br\n\n"
            f"Use seu usuário e senha para fazer login.\n\n"
            f"💡 *Dica:* Guarde seus dados de acesso em local seguro.\n\n"
            f"Se tiver dúvidas, entre em contato conosco.\n\n"
            f"Atenciosamente,\n"
            f"Equipe TLS Net Top 🚀"
        )
        
        # Headers
        headers = {
            'apikey': API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Payload
        payload = {
            "number": formatted_number,
            "options": {
                "delay": 1000,
                "presence": "composing"
            },
            "text": welcome_message
        }
        
        # URL
        url = f"{BASE_URL}/message/sendText/{INSTANCE_NAME}"
        
        logger.info(f"📤 Enviando boas-vindas (CADASTRO ONLINE) para {formatted_number}")
        
        # Envia
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Boas-vindas enviada para {user.username}")
            
            # Registra no histórico (se existir o modelo)
            try:
                from whatsapp_integration.models import HistoricoMensagemAutomatica
                HistoricoMensagemAutomatica.objects.create(
                    cliente=user,
                    data_tentativa=timezone.now(),
                    data_envio=timezone.now(),
                    status='ENVIADO',
                    mensagem_final_enviada=welcome_message,
                    detalhes=f'Boas-vindas CADASTRO ONLINE - {user.username}'
                )
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar histórico: {e}")
            
            return True
        else:
            logger.error("❌ Evolution API recusou a solicitação: HTTP %s", response.status_code)
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro ao enviar boas-vindas: {e}")
        return False


# ============================================================
# FUNÇÃO AUXILIAR (substitui a antiga enviar_mensagem_bem_vindo)
# ============================================================




@login_required
def adicionar_relatorio(request):
    if request.method == 'POST':
        # Cliente é sempre o usuário logado que está fazendo a ação
        cliente_para_relatorio = request.user

        valor_pago_str = request.POST.get('valor_pago')
        valor_servico_str = request.POST.get('valor_servico', '0')

        try:
            # Para entrada manual, valor_pago e valor_servico devem vir do form
            valor_pago = Decimal(valor_pago_str.replace(',', '.')) if valor_pago_str else Decimal('0') # Default 0 se vazio
            valor_servico = Decimal(valor_servico_str.replace(',', '.')) if valor_servico_str else Decimal('0')

            # Chama a função indicando que é MANUAL
            gerar_relatorio_financeiro(
                cliente=cliente_para_relatorio,
                valor_servico=valor_servico,
                valor_pago=valor_pago,
                is_manual_entry=True # <<< IMPORTANTE
            )

            # Redireciona para a view de relatório DO USUÁRIO LOGADO
            # Se for o admin, vai para a view do admin. Se for o filho, vai para a view do filho.
            return redirect('relatorio_financeiro') # Assumindo que esta URL existe e mostra o relatório do user logado

        except (ValueError, TypeError, InvalidOperation):
             # Adicionar mensagem de erro
             return redirect('relatorio_financeiro') # Ou renderizar com erro

    # Se GET, redirecionar para a página principal de relatórios
    return redirect('relatorio_financeiro')



@login_required
@require_POST
def excluir_relatorio(request, pk):
    try:
        relatorio = RelatorioFinanceiro.objects.get(pk=pk)
        
        # Verificar permissão
        usuario = request.user
        tipo_usuario = getattr(usuario, 'tipo_usuario', 'cliente')
        
        pode_excluir = False
        
        # Administrador pode excluir tudo
        if tipo_usuario == 'admin':
            pode_excluir = True
        
        # Revenda pode excluir:
        # 1. Seus próprios registros manuais
        # 2. Registros automáticos de seus clientes
        elif tipo_usuario == 'revenda':
            if relatorio.cliente == usuario and relatorio.is_manual:
                pode_excluir = True
            elif hasattr(relatorio.cliente, 'dono') and relatorio.cliente.dono == usuario and not relatorio.is_manual:
                pode_excluir = True
        
        # Cliente comum só pode excluir seus próprios registros
        else:
            pode_excluir = relatorio.cliente == usuario
        
        if not pode_excluir:
            return JsonResponse({
                'success': False,
                'error': 'Você não tem permissão para excluir este registro'
            })
        
        # Deletar o relatório
        relatorio.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Registro excluído com sucesso'
        })
        
    except RelatorioFinanceiro.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Registro não encontrado'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def tem_permissao_excluir(usuario, relatorio):
    """Verifica se o usuário tem permissão para excluir o relatório"""
    # Administrador pode excluir tudo
    if usuario.tipo_usuario == 'admin':
        return True
    
    # Revenda pode excluir seus próprios registros manuais
    # e registros automáticos de seus clientes
    if usuario.tipo_usuario == 'revenda':
        return (relatorio.cliente == usuario and relatorio.is_manual) or \
               (relatorio.cliente.dono == usuario and not relatorio.is_manual)
    
    # Cliente comum só pode excluir seus próprios registros
    return relatorio.cliente == usuario



def tem_permissao_editar(usuario, relatorio):
    """Verifica se o usuário tem permissão para editar o relatório"""
    # A mesma lógica da exclusão pode ser aplicada
    return tem_permissao_excluir(usuario, relatorio)



@login_required
def importar_usuarios(request):
    colunas_planilha = request.session.get('colunas_planilha', [])
    clientes_importados = request.session.get('clientes_importados', [])
    servidores = Servico.objects.filter(revenda=request.user)
    erro = None

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        
        if 'importar_planilha' in request.POST and form.is_valid():
            arquivo = request.FILES.get('arquivo', None)
            if not arquivo:
                erro = 'Nenhum arquivo foi enviado. Por favor, envie um arquivo válido.'
            else:
                try:
                    if arquivo.name.endswith('.csv'):
                        df = pd.read_csv(arquivo, dtype=str)
                    elif arquivo.name.endswith('.xlsx'):
                        df = pd.read_excel(arquivo, engine='openpyxl', dtype=str)
                    else:
                        erro = "Formato de arquivo não suportado. Use CSV ou Excel (.xlsx)."
                except Exception as e:
                    erro = f'Erro ao ler o arquivo: {e}'

                if not erro and not df.empty:
                    df.fillna('', inplace=True)
                    for col in df.columns:
                        if pd.api.types.is_datetime64_any_dtype(df[col]):
                            df[col] = df[col].dt.strftime('%Y-%m-%d')
                    
                    colunas_planilha = ['nome completo', 'username', 'senha_leitura', 'data_vencimento', 'plano', 'valor_servico', 'valor_a_pagar', 'whatsapp', 'tags', 'observacao']
                    clientes_importados = []
                    
                    for _, row in df.iterrows():
                        plano_nome = row.get('plano', '').strip()
                        try:
                            servidor = Servico.objects.get(nome=plano_nome, revenda=request.user)
                            custo_servico = servidor.custos if servidor.custos else 0.00
                            valor_plano = servidor.valor if servidor.valor else 0.00
                        except Servico.DoesNotExist:
                            erro = f"Erro: O plano '{plano_nome}' não existe ou não pertence a você."
                            break
                        
                        data_vencimento = row.get('vencimento', '').strip()
                        if data_vencimento:
                            try:
                                data_vencimento = datetime.strptime(data_vencimento.split()[0], '%Y-%m-%d').strftime('%Y-%m-%d')
                            except ValueError:
                                erro = f"Erro: Data de vencimento inválida na linha {_ + 1}."
                                break
                        else:
                            data_vencimento = None

                        clientes_importados.append({
                            'nome completo': row.get('nome completo', '').strip(),
                            'username': row.get('usuario', '').strip(),  # login_externo
                            'senha_leitura': row.get('senha', '').strip(),
                            'data_vencimento': data_vencimento,
                            'plano': plano_nome,
                            'valor_servico': custo_servico,
                            'valor_a_pagar': valor_plano,
                            'whatsapp': row.get('whatsapp', '').strip(),
                            'tags': row.get('tags', '').strip(),
                            'observacao': row.get('observacao', '').strip()
                        })
                    
                    if not erro:
                        request.session['clientes_importados'] = [{k: (float(v) if isinstance(v, Decimal) else v) for k, v in cliente.items()} for cliente in clientes_importados]
                        request.session['colunas_planilha'] = colunas_planilha

        elif 'salvar_linhas' in request.POST and clientes_importados:
            for index, cliente_data in enumerate(clientes_importados):
                try:
                    servidor = Servico.objects.get(nome=cliente_data.get('plano', '').strip(), revenda=request.user)
                except Servico.DoesNotExist:
                    erro = f"Erro: Servidor '{cliente_data.get('plano', '')}' não encontrado ou não pertence a você na linha {index + 1}."
                    break

                try:
                    cliente = CustomUser(
                        username=cliente_data.get('username', '').strip(),
                        nome=cliente_data.get('nome completo', '').strip(),
                        senha_leitura=cliente_data.get('senha_leitura', '').strip(),
                        login_externo=cliente_data.get('username', '').strip(),  # ✅ SALVA COMO LOGIN EXTERNO
                        tipo_usuario='cliente',  # ✅ FORÇA COMO CLIENTE
                        data_vencimento=datetime.strptime(cliente_data.get('data_vencimento', ''), '%Y-%m-%d').date() if cliente_data.get('data_vencimento', '') else None,
                        plano=servidor,
                        valor_servico=float(cliente_data.get('valor_servico', 0.00)),
                        valor_a_pagar=float(cliente_data.get('valor_a_pagar', 0.00)),
                        whatsapp=cliente_data.get('whatsapp', '').strip(),
                        observacao=cliente_data.get('observacao', '').strip(),
                        dono=request.user
                    )
                    cliente.set_password(cliente_data.get('senha_leitura', '').strip())
                    cliente.save()
                except Exception as e:
                    erro = f'Erro ao salvar o cliente na linha {index + 1}: {e}'
                    break

            if not erro:
                messages.success(request, 'Clientes importados com sucesso!')
                request.session.pop('clientes_importados', None)
                request.session.pop('colunas_planilha', None)
                return redirect('listar_clientes')

        elif 'limpar_dados' in request.POST:
            request.session.pop('clientes_importados', None)
            request.session.pop('colunas_planilha', None)
            messages.info(request, 'Dados da importação foram limpos.')
            return redirect('importar_usuarios')

    else:
        form = UploadFileForm()

    return render(request, 'clientes/importar_usuarios.html', {
        'form': form,
        'colunas_planilha': colunas_planilha,
        'clientes_importados': clientes_importados,
        'servidores': servidores,
        'erro': erro
    })


@login_required
def exportar_usuarios(request):
    # Define os campos a serem exportados
    colunas_planilha = [
        'nome completo', 'usuario', 'senha', 'vencimento', 'plano',
        'custo do serviço', 'valor do plano', 'whatsapp', 'tags', 'observacao'
    ]

    # ✅ FILTRA APENAS CLIENTES DO USUÁRIO LOGADO
    clientes = CustomUser.objects.filter(
        dono=request.user,
        tipo_usuario='cliente'
    )
    
    # Cria uma lista de dicionários com os dados dos clientes
    dados_clientes = []
    for cliente in clientes:
        dados_clientes.append({
            'nome completo': cliente.nome,
            'usuario': cliente.login_externo if cliente.login_externo else (cliente.username if cliente.username else ''),  # ✅ PRIORIZA LOGIN EXTERNO
            'senha': cliente.senha_leitura if cliente.senha_leitura else '',
            'vencimento': cliente.data_vencimento.strftime('%Y-%m-%d') if cliente.data_vencimento else '',
            'plano': cliente.plano.nome if cliente.plano else '',
            'custo do serviço': float(cliente.valor_servico) if cliente.valor_servico is not None else 0.00,
            'valor do plano': float(cliente.valor_a_pagar) if cliente.valor_a_pagar is not None else 0.00,
            'whatsapp': cliente.whatsapp if cliente.whatsapp else '',
            'tags': ', '.join(cliente.tags.values_list('nome', flat=True)) if cliente.tags.exists() else '',
            'observacao': cliente.observacao if cliente.observacao else ''
        })
    
    # Converte os dados para um DataFrame do Pandas
    df = pd.DataFrame(dados_clientes, columns=colunas_planilha)
    
    # Ajuste para garantir que os dados sejam interpretados corretamente na importação
    df.fillna('', inplace=True)
    
    # Cria a resposta HTTP com o arquivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=clientes_exportados.xlsx'
    
    # Salva o DataFrame como um arquivo Excel na resposta HTTP
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes')
    
    return response



@login_required
def adicionar_indicacao(request, cliente_id):
    """Adiciona uma indicação e processa comissão automaticamente"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            indicado_id = data.get('indicado_id')
            
            if not indicado_id:
                return JsonResponse({'status': 'error', 'message': 'Cliente indicado não especificado'}, status=400)
            
            cliente_indicador = get_object_or_404(CustomUser, id=cliente_id, dono=request.user)
            cliente_indicado = get_object_or_404(CustomUser, id=indicado_id, dono=request.user)
            
            # 🔒 Verifica se o cliente já foi indicado por alguém
            if Indicacao.objects.filter(cliente_indicado=cliente_indicado).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': f'{cliente_indicado.nome or cliente_indicado.username} já foi indicado!'
                })
            
            # Cria a indicação
            indicacao = Indicacao.objects.create(
                cliente_indicador=cliente_indicador,
                cliente_indicado=cliente_indicado
            )
            
            # 💰 Processa comissão automaticamente
            valor_comissao = _processar_comissao(cliente_indicador, cliente_indicado)
            
            mensagem = 'Indicação adicionada!'
            if valor_comissao > 0:
                mensagem += f' Comissão de R$ {valor_comissao:.2f} adicionada ao saldo.'
            
            return JsonResponse({
                'status': 'success',
                'message': mensagem,
                'comissao': float(valor_comissao)
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)



def _processar_comissao(indicador, indicado):
    """Processa comissão por indicação COM META E VALIDADE"""
    try:

        
        config = ConfiguracaoIndicacao.objects.filter(
            cliente=indicador,
            ativo=True
        ).first()
        
        if not config:

            return Decimal('0.00')
        

        
        if config.tipo_comissao not in ['indicacao', 'ambos']:

            return Decimal('0.00')
        
        valor = Decimal('0.00')
        
        # 1️⃣ Valor por indicação
        if config.valor_por_indicacao > 0:
            valor += config.valor_por_indicacao

        
        # 2️⃣ Verifica meta com validade
        if config.ativar_meta and config.quantidade_meta > 0:
            hoje = timezone.localdate()
            
            # Filtra indicações dentro da validade (se configurado)
            if config.validade_meses > 0:
                data_limite = hoje - relativedelta(months=config.validade_meses)
                total_indicacoes = Indicacao.objects.filter(
                    cliente_indicador=indicador,
                    data_indicacao__date__gte=data_limite
                ).count()

            else:
                # Sem validade = conta todas
                total_indicacoes = Indicacao.objects.filter(
                    cliente_indicador=indicador
                ).count()

            

            
            # 🎯 Verifica se atingiu um múltiplo exato da meta (2, 4, 6, 8...)
            if total_indicacoes > 0 and total_indicacoes % config.quantidade_meta == 0:
                # Calcula quantas vezes atingiu a meta
                vezes_meta = total_indicacoes // config.quantidade_meta
                
                # Verifica se JÁ recebeu bônus por esta meta
                # (evita pagar duplicado)
                bonus_ja_pago = _verificar_bonus_ja_pago(indicador, config, vezes_meta)
                
                if not bonus_ja_pago:
                    valor += config.bonus_meta

                    
                    # Registra que o bônus foi pago
                    _registrar_bonus_meta(indicador, config, vezes_meta, total_indicacoes)
                else:
                    pass  # bloco intencionalmente sem ação; debug removido

            else:
                faltam = config.quantidade_meta - (total_indicacoes % config.quantidade_meta)

        
        # 3️⃣ Adiciona saldo
        if valor > 0:
            saldo_antes = indicador.saldo
            indicador.saldo += valor
            indicador.save()

        
        return valor
        
    except Exception:
        logger.exception('Erro ao calcular indicadores de estoque do dashboard')
        return Decimal('0.00')


def _verificar_bonus_ja_pago(indicador, config, vezes_meta):
    """
    Verifica se o bônus desta meta já foi pago
    Usa o LogAtividade para registrar
    """
    descricao_busca = f"Bônus meta {vezes_meta}x ({config.quantidade_meta} indicações) para {indicador.nome}"
    
    ja_existe = LogAtividade.objects.filter(
        usuario=indicador.dono,
        tipo_acao='pagamento',
        descricao__icontains=descricao_busca,
        modelo_afetado='CustomUser',
        objeto_id=str(indicador.id)
    ).exists()
    
    return ja_existe

@never_cache
@login_required
def buscar_clientes_ajax(request):

   
    """View para busca AJAX - IDÊNTICA à listar_clientes"""
    try:
       
        termo_pesquisa = request.GET.get('termo', '').strip()
        filtro_plano = request.GET.get('plano', '').strip()
        filtro_status = request.GET.get('status', 'active')
        page_size = request.GET.get('page_size', 100)
        page_number = request.GET.get('page', 1)
        
        clientes = CustomUser.objects.filter(dono=request.user)\
            .select_related('plano')\
            .prefetch_related('tags')
        
        if filtro_status == 'inactive':
            clientes = clientes.filter(is_active=False)
        else:
            clientes = clientes.filter(is_active=True)
        
        if termo_pesquisa:
            clientes = clientes.filter(
                Q(nome__icontains=termo_pesquisa) |
                Q(username__icontains=termo_pesquisa) |
                Q(whatsapp__icontains=termo_pesquisa) |
                Q(login_externo__icontains=termo_pesquisa)
            )
        
        if filtro_plano:
            clientes = clientes.filter(plano__nome=filtro_plano)
        
        clientes = clientes.order_by('data_vencimento', 'nome')
        
        try:
            page_size = min(int(page_size), 500)
        except:
            page_size = 100
        
        paginator = Paginator(clientes, page_size)
        
        try:
            page_number = int(page_number)
        except:
            page_number = 1
        
        try:
            clientes_paginados = paginator.page(page_number)
        except:
            clientes_paginados = paginator.page(1)
        
        cliente_ids = [c.id for c in clientes_paginados]

        clientes_com_playlist = set()
        if cliente_ids:
            clientes_com_playlist = set(
                IntegracaoPlaylistCliente.objects.filter(
                    dono=request.user, cliente_id__in=cliente_ids
                ).values_list("cliente_id", flat=True)
            )
        
        # ============================================
        # RELATÓRIOS
        # ============================================
        relatorios_dict = {}
        if cliente_ids:
            relatorios = RelatorioFinanceiro.objects.filter(
                cliente_id__in=cliente_ids
            ).order_by('cliente_id', '-data_geracao')
            for r in relatorios:
                if r.cliente_id not in relatorios_dict:
                    relatorios_dict[r.cliente_id] = []
                if len(relatorios_dict[r.cliente_id]) < 5:
                    relatorios_dict[r.cliente_id].append(r)
        
        # ============================================
        # INDICAÇÕES
        # ============================================
        indicacoes_dict = {}
        if cliente_ids:
            indicacoes = Indicacao.objects.filter(
                cliente_indicador_id__in=cliente_ids
            ).select_related('cliente_indicado')
            for ind in indicacoes:
                if ind.cliente_indicador_id not in indicacoes_dict:
                    indicacoes_dict[ind.cliente_indicador_id] = []
                indicacoes_dict[ind.cliente_indicador_id].append(ind)
        
        # ============================================
        # DUPLICADOS
        # ============================================
# ============================================
# DUPLICADOS - CORRIGIDO (conta em todos os clientes do usuário)
# ============================================
        duplicados_map = {}
        if cliente_ids:
            
            
            # Pega os login_externo dos clientes da página atual
            logins_da_pagina = set()
            for c in clientes_paginados:
                if c.login_externo:
                    logins_da_pagina.add(c.login_externo)
            
            # Conta duplicados em TODOS os clientes do usuário (não só da página)
            if logins_da_pagina:
                duplicados_query = CustomUser.objects.filter(
                    dono=request.user,
                    is_active=True,
                    login_externo__in=logins_da_pagina  # Filtra pelos logins da página
                ).values('login_externo').annotate(total=Count('id')).filter(total__gt=1)
                
                for item in duplicados_query:
                    duplicados_map[item['login_externo']] = item['total']
        

            # COMPARTILHADOS (clientes com mesmo login_externo)
        compartilhados_map = {}
        if cliente_ids:
            
            # Pega os logins que aparecem mais de uma vez
            logins_duplicados = CustomUser.objects.filter(
                dono=request.user,
                is_active=True,
                login_externo__isnull=False
            ).values('login_externo').annotate(total=Count('id')).filter(total__gt=1)
            
            for item in logins_duplicados:
                login = item['login_externo']
                # Busca todos os clientes com esse login
                comps = CustomUser.objects.filter(
                    dono=request.user,
                    login_externo=login,
                    is_active=True
                ).values('id', 'nome', 'data_vencimento')
                compartilhados_map[login] = list(comps)


        # ============================================
        # PROCESSAR CLIENTES
        # ============================================
        hoje = timezone.localdate()
        for cliente in clientes_paginados:
            # Duplicados
            cliente.duplicados_count = duplicados_map.get(cliente.login_externo, 1) if cliente.login_externo else 1
            cliente.tem_playlist_cadastrada = cliente.id in clientes_com_playlist
            
            # Valores
            valor_a_pagar = cliente.valor_a_pagar or Decimal('0.00')
            saldo = cliente.saldo or Decimal('0.00')
            if saldo < 0:
                cliente.valor_total_a_pagar = valor_a_pagar + abs(saldo)
            else:
                cliente.valor_total_a_pagar = max(Decimal('0.00'), valor_a_pagar - saldo)


                    # Compartilhados
                    # Compartilhados
            if cliente.login_externo and cliente.login_externo in compartilhados_map:
                comps = compartilhados_map[cliente.login_externo]
                # Adiciona avatar_url para cada comp
                for comp in comps:
                    comp['avatar_url'] = comp.get('whatsapp_avatar_url') or ''
                cliente.compartilhados = comps
            else:
                cliente.compartilhados = []
            
            # Status e porcentagem
            if not cliente.is_active:
                cliente.status_vencimento = "Inativo"
                cliente.porcentagem_vencimento = 10
            elif cliente.data_vencimento:
                dias = (cliente.data_vencimento - hoje).days
                if dias < 0:
                    cliente.status_vencimento = "Vencido"
                    cliente.porcentagem_vencimento = 100
                elif dias == 0:
                    cliente.status_vencimento = "Vence Hoje"
                    cliente.porcentagem_vencimento = 95
                elif dias <= 3:
                    cliente.status_vencimento = "Vence em Breve"
                    cliente.porcentagem_vencimento = 50
                elif dias <= 7:
                    cliente.status_vencimento = "Vence em Breve"
                    cliente.porcentagem_vencimento = 60
                elif dias <= 15:
                    cliente.status_vencimento = "Em Dia"
                    cliente.porcentagem_vencimento = 70
                elif dias <= 30:
                    cliente.status_vencimento = "Em Dia"
                    cliente.porcentagem_vencimento = 85
                else:
                    cliente.status_vencimento = "Em Dia"
                    cliente.porcentagem_vencimento = 100
            else:
                cliente.status_vencimento = "Em Dia"
                cliente.porcentagem_vencimento = 75
            
            # Avatar
            cliente.has_avatar = bool(
                cliente.whatsapp_avatar_url and
                cliente.whatsapp_avatar_status == 'found' and
                cliente.is_avatar_valid()
            )
            
            # Relatórios e indicações
            cliente.relatorios_carregados = relatorios_dict.get(cliente.id, [])
            cliente.indicacoes_list = indicacoes_dict.get(cliente.id, [])
            cliente.valor_servico_exibicao = cliente.valor_servico or Decimal('0.00')
        
        # ============================================
        # RENDERIZAR
        # ============================================
        html = render_to_string('clientes/includes/tabela_clientes.html', {
            'clientes': clientes_paginados,
            'request': request,
        }, request=request)
        
        logger.info(
            f"🔍 AJAX - User: {request.user.username} | "
            f"Total: {paginator.count} | Status: {filtro_status} | "
            f"Plano: {filtro_plano or 'Todos'} | Termo: '{termo_pesquisa}' | "
            f"Pág: {page_number}/{paginator.num_pages} | "
            f"Duplicados map: {dict(duplicados_map)}"
        )
        
        return JsonResponse({
            'success': True, 'html': html,
            'total': paginator.count, 'page': clientes_paginados.number,
            'num_pages': paginator.num_pages,
            'has_previous': clientes_paginados.has_previous(),
            'has_next': clientes_paginados.has_next(),
            'start_index': clientes_paginados.start_index(),
            'end_index': clientes_paginados.end_index()
        })
        
    except Exception as e:
        logger.error(f"❌ Erro AJAX: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'html': '<tr><td colspan="7" style="padding:3rem;text-align:center;"><h3>Erro ao carregar</h3></td></tr>'
        }, status=500)
    

def _registrar_bonus_meta(indicador, config, vezes_meta, total_indicacoes):
    """Registra o pagamento do bônus da meta"""
    try:
        LogAtividade.registrar(
            usuario=indicador.dono,
            tipo_acao='pagamento',
            descricao=f"Bônus meta {vezes_meta}x ({config.quantidade_meta} indicações) para {indicador.nome} - Total: {total_indicacoes} indicações - R$ {config.bonus_meta}",
            modelo_afetado='CustomUser',
            objeto_id=str(indicador.id)
        )

    except Exception as e:
        pass  # bloco intencionalmente sem ação; debug removido



def _processar_comissao_renovacao(indicador, indicado):
    """Comissão por renovação"""
    try:


        
        config = ConfiguracaoIndicacao.objects.filter(
            cliente=indicador,
            ativo=True
        ).first()
        
        if not config:

            return 0
        

        
        if config.tipo_comissao not in ['renovacao', 'ambos']:

            return 0
        
        valor = config.valor_por_renovacao
        
        if valor <= 0:

            return 0
        
        saldo_antes = indicador.saldo
        indicador.saldo += valor
        indicador.save()

        
        return valor
            
    except Exception as e:

        import traceback
        traceback.print_exc()
        return 0


@login_required
def renovar_cliente(request, pk):
    """Renovação manual ou integrada.

    Manual mantém o comportamento antigo. Automático faz uma etapa de preview
    sem efeitos colaterais e só renova no painel quando o usuário confirma.
    O ID externo nunca fica preso ao cliente: a conta é localizada novamente
    pelo usuário/senha atuais a cada operação.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

    cliente = get_object_or_404(CustomUser, pk=pk, dono=request.user)
    plano = cliente.plano
    if not plano:
        return JsonResponse({'status': 'error', 'message': 'O cliente não possui plano/servidor definido.'}, status=400)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'JSON inválido'}, status=400)

    modo = str(data.get('modo') or 'manual').lower()
    acao = str(data.get('acao') or 'executar').lower()
    quem_paga = str(data.get('quem_paga') or 'auto').lower()
    enviar_mensagem = bool(data.get('enviar_mensagem', False))
    request_id = str(data.get('request_id') or uuid.uuid4().hex)[:80]
    hoje = timezone.localdate()

    # A política do servidor é soberana. Isso impede forçar modo manual pelo
    # navegador quando o plano foi marcado como integração obrigatória.
    if plano.integracao_politica == 'obrigatoria':
        modo = 'automatico'
    elif plano.integracao_politica == 'manual':
        modo = 'manual'

    if modo == 'automatico' and (not plano.integracao_ativa or plano.integracao_tipo in ('', 'nenhuma')):
        return JsonResponse({'status': 'error', 'message': 'A renovação automática não está configurada para este servidor.'}, status=400)

    # Grupo é calculado com as credenciais atuais, nunca por ID externo antigo.
    grupo_qs = CustomUser.objects.filter(
        login_externo=cliente.login_externo,
        plano=plano,
        dono=request.user,
        is_active=True,
    )
    if cliente.senha_leitura:
        grupo_qs = grupo_qs.filter(senha_leitura=cliente.senha_leitura)
    clientes_mesmo_grupo = grupo_qs.exclude(pk=cliente.pk)
    tem_compartilhamento = clientes_mesmo_grupo.exists()

    def _outros_payload():
        return [
            {
                'id': c.id,
                'nome': c.nome,
                'vencimento': c.data_vencimento.strftime('%d/%m/%Y') if c.data_vencimento else 'Sem data',
            }
            for c in clientes_mesmo_grupo
        ]

    def _valor_base():
        if cliente.valor_a_pagar and cliente.valor_a_pagar > 0:
            return Decimal(cliente.valor_a_pagar)
        return Decimal(plano.valor or 0)

    def _valor_pago_com_saldo(valor_base):
        saldo = Decimal(cliente.saldo or 0)
        if saldo < 0:
            valor_pago = valor_base + abs(saldo)
        elif saldo > 0:
            valor_pago = max(Decimal('0.00'), valor_base - saldo)
        else:
            valor_pago = valor_base
        return valor_pago, saldo

    def _registrar_finalizacao(nova_data, custo, consumiu, qtd_creditos, descricao_extra=''):
        valor_base = _valor_base()
        valor_pago, saldo_anterior = _valor_pago_com_saldo(valor_base)
        cliente.saldo = Decimal('0.00')
        grupo = get_grupo_renovacao(cliente)

        gerar_relatorio_financeiro(
            cliente=cliente,
            valor_pago=valor_pago,
            valor_servico=custo,
            is_manual_entry=False,
            numero_renovacao=0,
            grupo_renovacao=grupo,
        )
        cliente.data_vencimento = nova_data
        cliente.valor_servico = custo
        cliente.save(update_fields=['data_vencimento', 'valor_servico', 'saldo'])

        try:
            data_limite = timezone.now() - timedelta(days=30)
            indicacao = Indicacao.objects.filter(
                cliente_indicado=cliente,
                data_indicacao__gte=data_limite,
            ).select_related('cliente_indicador').first()
            if indicacao:
                _processar_comissao_renovacao(indicacao.cliente_indicador, cliente)
        except Exception as exc:
            logger.error('Erro ao processar comissão: %s', exc)

        if enviar_mensagem and cliente.whatsapp:
            try:
                enviar_mensagem_confirmacao_pagamento(cliente, user=request.user)
            except Exception as exc:
                logger.error('Erro ao enviar mensagem de renovação: %s', exc)

        LogAtividade.registrar(
            request=request,
            usuario=request.user,
            tipo_acao='renovacao',
            descricao=(
                f"Renovou {cliente.nome} | Modo: {modo} | "
                f"Valor base: R$ {valor_base:.2f} | Saldo anterior: R$ {saldo_anterior:.2f} | "
                f"Valor pago: R$ {valor_pago:.2f} | Créditos: {qtd_creditos if consumiu else 0} | "
                f"Custo: R$ {custo:.2f} | Vencimento: {nova_data.strftime('%d/%m/%Y')}"
                + (f" | {descricao_extra}" if descricao_extra else '')
            ),
            modelo_afetado='CustomUser',
            objeto_id=cliente.id,
        )
        return valor_base, valor_pago, saldo_anterior

    # ================================================================
    # RENOVAÇÃO MANUAL
    # ================================================================
    if modo != 'automatico':
        data_vencimento = data.get('data_vencimento')
        if data_vencimento not in ('', 'null', None):
            try:
                nova_data = datetime.strptime(str(data_vencimento), '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Data de vencimento inválida.'}, status=400)
        else:
            base = cliente.data_vencimento if cliente.data_vencimento and cliente.data_vencimento > hoje else hoje
            nova_data = base + timedelta(days=30)

        if tem_compartilhamento and quem_paga == 'auto':
            maior = grupo_qs.aggregate(max_vencimento=Max('data_vencimento'))['max_vencimento']
            return JsonResponse({
                'status': 'pergunta',
                'modo': 'manual',
                'message': 'Quem paga o custo desta renovação?',
                'cliente_nome': cliente.nome,
                'outros': _outros_payload(),
                'todos_vencimentos': maior.strftime('%d/%m/%Y') if maior else 'Sem data',
            })

        deve_consumir = quem_paga != 'outro'
        if plano.renovacao_manual_credito == 'nunca':
            deve_consumir = False
        elif plano.renovacao_manual_credito == 'perguntar' and quem_paga != 'outro':
            deve_consumir = bool(data.get('consumir_credito_manual', True))

        custo = Decimal('0.00')
        consumiu = False
        qtd = 0
        if deve_consumir:
            sucesso, msg, custo = CreditoService.consumir_credito_cliente(
                plano=plano, cliente=cliente, quantidade=1, is_renovacao=True
            )
            if not sucesso:
                return JsonResponse({'status': 'error', 'message': msg or 'Erro ao consumir crédito'}, status=400)
            qtd = 1
            consumiu = bool(plano.controlar_estoque and plano.tipo_estoque in ['creditos', 'ambos'])

        valor_base, valor_pago, saldo_anterior = _registrar_finalizacao(
            nova_data, custo, consumiu, qtd,
            'Renovação manual; outro já pagou' if quem_paga == 'outro' else 'Renovação manual'
        )
        return JsonResponse({
            'status': 'success', 'modo': 'manual',
            'proximo_vencimento': nova_data.strftime('%Y-%m-%d'),
            'consumiu_credito': consumiu, 'creditos': qtd if consumiu else 0,
            'custo': str(custo), 'valor_base': str(valor_base), 'valor_pago': str(valor_pago),
            'saldo_anterior': str(saldo_anterior), 'saldo_atual': '0.00',
            'mensagem_enviada': enviar_mensagem and bool(cliente.whatsapp),
        })

    # ================================================================
    # RENOVAÇÃO AUTOMÁTICA
    # ================================================================
    try:
        meses = int(data.get('meses') or 1)
    except (TypeError, ValueError):
        meses = 1
    if meses not in (1, 2, 3, 6, 12):
        return JsonResponse({'status': 'error', 'message': 'Período de renovação inválido.'}, status=400)

    try:
        adapter = get_painel_adapter(plano)
        preview = adapter.preview_renovacao(cliente.login_externo or '', cliente.senha_leitura or '', meses)
    except (IntegracaoPainelErro, ContaNaoEncontrada, ContaAmbigua) as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)
    except Exception as exc:
        logger.exception('Erro inesperado no preview da integração')
        return JsonResponse({'status': 'error', 'message': f'Falha ao consultar o painel: {exc}'}, status=500)

    preview_payload = {
        'usuario': preview.conta.usuario,
        'nome_externo': preview.conta.nome,
        'plano_externo': preview.conta.plano or preview.pacote_nome,
        'pacote_novo': preview.pacote_nome,
        'servidor_externo': preview.conta.servidor,
        'vencimento_atual': timezone.localtime(preview.conta.vencimento).strftime('%d/%m/%Y %H:%M') if preview.conta.vencimento else 'Não informado',
        'meses': meses,
        'creditos': str(preview.creditos),
        'conexoes': preview.conexoes,
        'tipo_integracao': plano.get_integracao_tipo_display(),
        'identificacao': (
            'Usuário + senha conferidos no painel'
            if preview.conta.senha
            else 'Usuário + servidor (a API não devolveu a senha para conferência)'
        ),
    }

    # Preview é sempre sem efeitos colaterais. Se houver compartilhamento,
    # a mesma tela já mostra quem está usando a conta atual.
    if acao == 'preview':
        return JsonResponse({
            'status': 'preview',
            'preview': preview_payload,
            'tem_compartilhamento': tem_compartilhamento,
            'outros': _outros_payload() if tem_compartilhamento else [],
            'message': 'Confira os dados do painel antes de confirmar.',
        })

    if tem_compartilhamento and quem_paga == 'auto':
        return JsonResponse({
            'status': 'pergunta', 'modo': 'automatico',
            'preview': preview_payload,
            'message': 'Quem paga esta renovação compartilhada?',
            'cliente_nome': cliente.nome, 'outros': _outros_payload(),
        })

    # "Outro já pagou" no automático NÃO renova o painel novamente. Apenas
    # sincroniza este cadastro local com a renovação já feita da conta compartilhada.
    if quem_paga == 'outro':
        venc_dt = None
        recente = OperacaoIntegracaoPainel.objects.filter(
            revenda=request.user,
            servico=plano,
            login_externo=cliente.login_externo or '',
            tipo='renovacao',
            status__in=['concluida', 'aceita'],
            vencimento_novo__isnull=False,
            criado_em__gte=timezone.now() - timedelta(minutes=15),
        ).order_by('-criado_em').first()
        if recente:
            venc_dt = recente.vencimento_novo
        elif preview.conta.vencimento:
            venc_dt = preview.conta.vencimento

        if venc_dt:
            nova_data = timezone.localtime(venc_dt).date()
        else:
            maior = grupo_qs.aggregate(max_vencimento=Max('data_vencimento'))['max_vencimento']
            nova_data = maior or cliente.data_vencimento or hoje

        valor_base, valor_pago, saldo_anterior = _registrar_finalizacao(
            nova_data, Decimal('0.00'), False, 0,
            'Conta compartilhada; painel não foi renovado novamente'
        )
        return JsonResponse({
            'status': 'success', 'modo': 'automatico', 'sincronizado': True,
            'proximo_vencimento': nova_data.strftime('%Y-%m-%d'),
            'consumiu_credito': False, 'creditos': 0, 'custo': '0.00',
            'valor_base': str(valor_base), 'valor_pago': str(valor_pago),
            'saldo_anterior': str(saldo_anterior), 'saldo_atual': '0.00',
            'message': 'Cadastro sincronizado sem renovar a conta externa novamente.',
        })

    # Quantidade local precisa ser inteira porque o estoque atual é inteiro.
    if preview.creditos != preview.creditos.to_integral_value():
        return JsonResponse({
            'status': 'error',
            'message': f'O painel exige {preview.creditos} crédito(s), mas o estoque local ainda aceita apenas créditos inteiros.'
        }, status=400)
    qtd_creditos = int(preview.creditos)

    if plano.controlar_estoque and plano.tipo_estoque in ['creditos', 'ambos'] and plano.creditos_disponiveis < qtd_creditos:
        return JsonResponse({
            'status': 'error',
            'message': f'Créditos insuficientes. O painel exige {qtd_creditos} e existem {plano.creditos_disponiveis} no gestor.'
        }, status=400)

    chave = f'renovacao:{request.user.id}:{cliente.id}:{request_id}'
    existente = OperacaoIntegracaoPainel.objects.filter(chave_idempotencia=chave).first()
    if existente:
        if existente.status in ('concluida', 'aceita'):
            nova = existente.vencimento_novo
            return JsonResponse({
                'status': 'success', 'modo': 'automatico', 'idempotente': True,
                'proximo_vencimento': timezone.localtime(nova).date().isoformat() if nova else (cliente.data_vencimento.isoformat() if cliente.data_vencimento else None),
                'consumiu_credito': existente.creditos_locais > 0,
                'creditos': existente.creditos_locais,
                'custo': str(existente.custo_local),
                'message': 'Esta renovação já havia sido processada. Nenhuma nova cobrança foi enviada ao painel.',
            })
        return JsonResponse({'status': 'error', 'message': 'Esta renovação já está em processamento/verificação.'}, status=409)

    operacao = OperacaoIntegracaoPainel.objects.create(
        revenda=request.user,
        cliente=cliente,
        servico=plano,
        tipo='renovacao',
        status='consultando',
        chave_idempotencia=chave,
        login_externo=cliente.login_externo or '',
        external_id=preview.conta.id,
        meses=meses,
        creditos_externos=preview.creditos,
        vencimento_anterior=preview.conta.vencimento,
        requisicao_resumo={
            'painel': plano.integracao_tipo,
            'usuario': cliente.login_externo or '',
            'meses': meses,
            'pacote': preview.pacote_nome,
            'creditos': str(preview.creditos),
        },
    )

    try:
        resultado = adapter.renovar(preview)
        # SIGMAN devolve o vencimento real. UniTV aceita a operação e pode levar
        # alguns minutos; nesse caso calculamos uma previsão sem reenviar a renovação.
        venc_dt = resultado.vencimento_novo
        if not venc_dt:
            base_dt = preview.conta.vencimento or timezone.now()
            if base_dt < timezone.now():
                base_dt = timezone.now()
            venc_dt = base_dt + relativedelta(months=meses)
        venc_dt = venc_dt if timezone.is_aware(venc_dt) else timezone.make_aware(venc_dt)
        nova_data = timezone.localtime(venc_dt).date()

        custo = Decimal('0.00')
        consumiu = False
        if qtd_creditos > 0:
            sucesso, msg, custo = CreditoService.consumir_credito_cliente(
                plano=plano,
                cliente=cliente,
                quantidade=qtd_creditos,
                is_renovacao=True,
            )
            if not sucesso:
                # O painel já confirmou a renovação. Não escondemos esse estado.
                operacao.status = 'verificar'
                operacao.erro = f'Painel renovou, mas o gestor não conseguiu baixar créditos: {msg}'
                operacao.vencimento_novo = venc_dt
                operacao.resposta_resumo = {'mensagem': resultado.mensagem, 'painel_renovou': True}
                operacao.save(update_fields=['status', 'erro', 'vencimento_novo', 'resposta_resumo', 'atualizado_em'])
                return JsonResponse({
                    'status': 'error_critico',
                    'message': 'O painel confirmou a renovação, mas houve falha ao baixar o crédito local. A operação foi marcada para verificação e NÃO será reenviada.',
                    'operacao_id': operacao.id,
                }, status=409)
            consumiu = bool(plano.controlar_estoque and plano.tipo_estoque in ['creditos', 'ambos'])

        valor_base, valor_pago, saldo_anterior = _registrar_finalizacao(
            nova_data, custo, consumiu, qtd_creditos,
            f"Painel {plano.get_integracao_tipo_display()} | {resultado.status_externo}"
        )

        operacao.status = 'aceita' if resultado.status_externo == 'aceita' else 'concluida'
        operacao.creditos_locais = qtd_creditos if consumiu else 0
        operacao.custo_local = custo
        operacao.vencimento_novo = venc_dt
        operacao.resposta_resumo = {
            'mensagem': resultado.mensagem,
            'status_externo': resultado.status_externo,
            'usuario': resultado.conta.usuario,
            'vencimento': venc_dt.isoformat() if venc_dt else None,
        }
        operacao.concluido_em = timezone.now()
        operacao.save(update_fields=[
            'status', 'creditos_locais', 'custo_local', 'vencimento_novo',
            'resposta_resumo', 'concluido_em', 'atualizado_em'
        ])

        return JsonResponse({
            'status': 'success', 'modo': 'automatico',
            'proximo_vencimento': nova_data.strftime('%Y-%m-%d'),
            'consumiu_credito': consumiu, 'creditos': qtd_creditos if consumiu else 0,
            'custo': str(custo), 'valor_base': str(valor_base), 'valor_pago': str(valor_pago),
            'saldo_anterior': str(saldo_anterior), 'saldo_atual': '0.00',
            'painel_status': resultado.status_externo,
            'message': resultado.mensagem,
            'operacao_id': operacao.id,
            'mensagem_enviada': enviar_mensagem and bool(cliente.whatsapp),
        })
    except (IntegracaoPainelErro, ContaNaoEncontrada, ContaAmbigua) as exc:
        operacao.status = 'falhou'
        operacao.erro = str(exc)
        operacao.concluido_em = timezone.now()
        operacao.save(update_fields=['status', 'erro', 'concluido_em', 'atualizado_em'])
        return JsonResponse({'status': 'error', 'message': str(exc), 'operacao_id': operacao.id}, status=400)
    except Exception as exc:
        logger.exception('Erro na renovação automática')
        operacao.status = 'verificar'
        operacao.erro = str(exc)
        operacao.save(update_fields=['status', 'erro', 'atualizado_em'])
        return JsonResponse({
            'status': 'error_critico',
            'message': 'Houve uma falha inesperada durante a integração. Por segurança, a operação ficou marcada para verificação e não deve ser repetida até conferir o painel.',
            'operacao_id': operacao.id,
        }, status=500)

def get_proxima_rodada(grupo, plano):
    """
    Determina a próxima rodada e se o cliente deve pagar custo.
    
    Retorna: (numero_rodada, deve_pagar_custo)
    
    Lógica:
    1. Busca a última rodada do grupo
    2. Conta quantos já pagaram nessa rodada
    3. Se atingiu o multiplicador → nova rodada, paga
    4. Se ninguém pagou → paga
    5. Se já tem alguém mas não atingiu → não paga
    """
    from django.db.models import Max, Count
    
    # Pega o maior número de rodada do grupo
    ultima_rodada = RelatorioFinanceiro.objects.filter(
        grupo_renovacao=grupo
    ).aggregate(
        max_rodada=Max('numero_rodada')
    )['max_rodada'] or 0
    
    # Conta quantos clientes PAGARAM custo nesta rodada (valor_servico > 0)
    pagaram_na_rodada = RelatorioFinanceiro.objects.filter(
        grupo_renovacao=grupo,
        numero_rodada=ultima_rodada,
        valor_servico__gt=Decimal('0.00')
    ).values('cliente').distinct().count()
    
    multiplicador = plano.multiplicador if plano else 1
    
    if pagaram_na_rodada >= multiplicador:
        # Atingiu o limite da rodada → NOVA RODADA
        nova_rodada = ultima_rodada + 1
        return nova_rodada, True
    elif pagaram_na_rodada == 0:
        # Ninguém pagou ainda nesta rodada → PRIMEIRO PAGA
        return ultima_rodada, True
    else:
        # Já tem alguém que pagou, mas não atingiu o limite → NÃO PAGA
        return ultima_rodada, False
    



def get_field(obj, *names, default=None):
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None:
                return value
    return default

def parse_decimal_br(valor):
    if valor is None:
        return Decimal('0.00')
    valor = str(valor).strip()
    if not valor:
        return Decimal('0.00')
    valor = valor.replace('.', '').replace(',', '.')
    try:
        return Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal('0.00')
    

@login_required
@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(CustomUser, pk=pk)
    cliente_tags = list(cliente.tags.values_list('id', flat=True))

    # Busca custo FIFO real para exibição
    if cliente.plano and cliente.plano.controlar_estoque and cliente.plano.tipo_estoque in ['creditos', 'ambos']:
        lote_fifo = LoteEstoque.objects.filter(
            servico=cliente.plano,
            quantidade_restante__gt=0
        ).order_by('ordem').first()
        
        if lote_fifo:
            valor_servico_original = lote_fifo.custo_unitario
        elif cliente.plano.custos and cliente.plano.custos > 0:
            valor_servico_original = cliente.plano.custos
        else:
            valor_servico_original = cliente.valor_servico or Decimal('0.00')
    else:
        valor_servico_original = cliente.valor_servico or Decimal('0.00')
    
    valor_a_pagar_original = cliente.valor_a_pagar or Decimal('0.00')
    
    valor_servico_original = valor_servico_original.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    valor_a_pagar_original = valor_a_pagar_original.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    dados_antes = {
        'nome': cliente.nome,
        'username': cliente.username,
        'login_externo': cliente.login_externo,
        'senha_leitura': cliente.senha_leitura,
        'data_vencimento': str(cliente.data_vencimento) if cliente.data_vencimento else None,
        'plano': cliente.plano.nome if cliente.plano else None,
        'whatsapp': cliente.whatsapp,
        'is_active': cliente.is_active,
        'tipo_usuario': cliente.tipo_usuario,
        'valor_servico': str(valor_servico_original),
        'valor_a_pagar': str(valor_a_pagar_original),
    }

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente, user=request.user)

        if form.is_valid():
            cliente = form.save(commit=False)

            nome = request.POST.get('nome', '').strip()
            whatsapp = request.POST.get('whatsapp', '').strip()
            observacao = request.POST.get('observacao', '').strip()
            tipo_usuario = request.POST.get('tipo_usuario', '').strip()

            # Nome
            if nome:
                cliente.nome = nome
                cliente.first_name = nome
            
            # WhatsApp
            if whatsapp:
                cliente.whatsapp = whatsapp
            
            # Observação
            if observacao:
                cliente.observacao = observacao
            else:
                cliente.observacao = ''
            
            # Tipo de usuário
            if tipo_usuario:
                cliente.tipo_usuario = tipo_usuario

            # ==========================================
            # 🔴 LÓGICA CORRETA:
            # ==========================================
            
            if cliente.tipo_usuario in ['revenda', 'admin']:
                # ==========================================
                # REVENDA/ADMIN: Edita username e password do SISTEMA
                # ==========================================
                novo_username = request.POST.get('username', '').strip()
                nova_senha = request.POST.get('password', '').strip()
                
                if novo_username:
                    # Verifica se username já existe
                    if CustomUser.objects.filter(username=novo_username).exclude(pk=cliente.pk).exists():
                        messages.error(request, f"❌ O usuário '{novo_username}' já está em uso!")
                        return render(request, 'clientes/editar_cliente.html', {
                            'form': form, 'cliente': cliente, 'cliente_tags': cliente_tags,
                            'valor_servico_original': float(valor_servico_original),
                            'valor_a_pagar_original': float(valor_a_pagar_original),
                        })
                    cliente.username = novo_username
                
                if nova_senha:
                    cliente.set_password(nova_senha)
                
                # Mantém login_externo e senha_leitura originais
                # (não altera, pois não são relevantes para revenda/admin)
                
            else:
                # ==========================================
                # CLIENTE: Edita login_externo e senha_leitura (IPTV)
                # ==========================================
                login_externo = request.POST.get('login_externo', '').strip()
                senha_leitura = request.POST.get('senha_leitura', '').strip()
                
                cliente.login_externo = login_externo
                cliente.senha_leitura = senha_leitura

            # Data de vencimento
            data_vencimento = request.POST.get('data_vencimento', '').strip()
            if data_vencimento:
                try:
                    from datetime import datetime
                    cliente.data_vencimento = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
                except:
                    pass
            else:
                cliente.data_vencimento = None

            # Plano
            plano_id = request.POST.get('plano', '').strip()
            if plano_id:
                try:
                    cliente.plano = Servico.objects.get(id=plano_id, revenda=request.user)
                except Servico.DoesNotExist:
                    cliente.plano = None
            else:
                cliente.plano = None

            # ==========================================
            # VALIDAÇÕES DE PLANO (apenas para clientes)
            # ==========================================
            if cliente.tipo_usuario == 'cliente' and cliente.plano and cliente.login_externo:
                
                if cliente.plano.usuario_unico:
                    existente = CustomUser.objects.filter(
                        login_externo=cliente.login_externo,
                        plano=cliente.plano,
                        is_active=True,
                        dono=request.user
                    ).exclude(pk=cliente.pk).exists()

                    if existente:
                        messages.error(request, f"❌ O login '{cliente.login_externo}' já está em uso no plano '{cliente.plano.nome}'!")
                        return render(request, 'clientes/editar_cliente.html', {
                            'form': form, 'cliente': cliente, 'cliente_tags': cliente_tags,
                            'valor_servico_original': float(valor_servico_original),
                            'valor_a_pagar_original': float(valor_a_pagar_original),
                        })
                
                elif not cliente.plano.usuario_unico and cliente.plano.multiplicador > 1:
                    total_mesmo_login = CustomUser.objects.filter(
                        login_externo=cliente.login_externo,
                        plano=cliente.plano,
                        is_active=True,
                        dono=request.user
                    ).exclude(pk=cliente.pk).count()
                    
                    if total_mesmo_login >= cliente.plano.multiplicador:
                        messages.error(request, f"❌ Limite de compartilhamento atingido! Máximo: {cliente.plano.multiplicador}")
                        return render(request, 'clientes/editar_cliente.html', {
                            'form': form, 'cliente': cliente, 'cliente_tags': cliente_tags,
                            'valor_servico_original': float(valor_servico_original),
                            'valor_a_pagar_original': float(valor_a_pagar_original),
                        })

            # Salva valores
            valor_servico_str = request.POST.get('valor_servico', '').strip()
            valor_pagar_str = request.POST.get('valor_a_pagar', '').strip()
            
            if valor_servico_str:
                valor_servico_str = valor_servico_str.replace(',', '.')
                try:
                    cliente.valor_servico = Decimal(valor_servico_str)
                except:
                    pass
            
            if valor_pagar_str:
                valor_pagar_str = valor_pagar_str.replace(',', '.')
                try:
                    cliente.valor_a_pagar = Decimal(valor_pagar_str)
                except:
                    pass

            # SALVA
            cliente.save()

            # Tags
            tag_ids = request.POST.getlist('tags')
            tags_validas = Tag.objects.filter(id__in=tag_ids, usuario=request.user) if tag_ids else Tag.objects.none()
            cliente.tags.set(tags_validas)

            # Log
            dados_depois = {
                'nome': cliente.nome,
                'username': cliente.username,
                'login_externo': cliente.login_externo,
                'senha_leitura': cliente.senha_leitura,
                'data_vencimento': str(cliente.data_vencimento) if cliente.data_vencimento else None,
                'plano': cliente.plano.nome if cliente.plano else None,
                'whatsapp': cliente.whatsapp,
                'is_active': cliente.is_active,
                'tipo_usuario': cliente.tipo_usuario,
                'tags': list(cliente.tags.values_list('nome', flat=True)),
                'valor_servico': str(cliente.valor_servico),
                'valor_a_pagar': str(cliente.valor_a_pagar),
            }

            LogAtividade.registrar(
                request=request,
                usuario=request.user,
                tipo_acao='update',
                descricao=f"Usuário {request.user.username} editou cliente {cliente.nome}",
                modelo_afetado='CustomUser',
                objeto_id=cliente.id,
                dados_antes=dados_antes,
                dados_depois=dados_depois,
            )

            messages.success(request, f"✅ Cliente {cliente.nome} atualizado com sucesso!")

            # Atualiza avatar
            from clientes.utils_avatar import atualizar_avatar_rapido
            whatsapp_mudou = whatsapp != dados_antes.get('whatsapp', '')
            precisa_atualizar = whatsapp_mudou or not cliente.whatsapp_avatar_url or cliente.whatsapp_avatar_status != 'found'
            if precisa_atualizar:
                atualizar_avatar_rapido(cliente, forcar=whatsapp_mudou)

            return redirect('listar_clientes')
        
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"❌ {label}: {error}")
    else:
        form = ClienteForm(instance=cliente, user=request.user)

    return render(request, 'clientes/editar_cliente.html', {
        'form': form,
        'cliente': cliente,
        'cliente_tags': cliente_tags,
        'valor_servico_original': float(valor_servico_original),
        'valor_a_pagar_original': float(valor_a_pagar_original),
    })

@login_required
def excluir_cliente(request, pk):
    # 🔒 Só exclui se pertence ao usuário logado
    cliente = get_object_or_404(CustomUser, pk=pk, dono=request.user)
    
    if request.method == "POST":
        try:
            cliente_nome = cliente.nome or cliente.username
            
            dados_antes = {
                'nome': cliente.nome,
                'username': cliente.username,
                'email': cliente.email,
                'whatsapp': cliente.whatsapp,
                'data_vencimento': str(cliente.data_vencimento) if cliente.data_vencimento else None,
                'plano': cliente.plano.nome if cliente.plano else None
            }
            
            cliente.delete()
            
            LogAtividade.registrar(
                request=request,
                usuario=request.user,
                tipo_acao='delete',
                descricao=f"Usuário {request.user.username} excluiu cliente: {cliente_nome}",
                modelo_afetado='CustomUser',
                objeto_id=pk,
                dados_antes=dados_antes
            )
            
            messages.success(request, f"Cliente '{cliente_nome}' excluído com sucesso!")
            
        except Exception as e:
            messages.error(request, f"Erro ao excluir cliente: {str(e)}")
            LogAtividade.registrar(
                request=request,
                usuario=request.user,
                tipo_acao='delete',
                descricao=f"Erro ao excluir cliente ID {pk}: {str(e)}",
                status='erro'
            )
        
        return redirect('listar_clientes')
    
    return redirect('listar_clientes')

@login_required
def cliente_vencido(request):
    cliente = request.user
    return render(request, 'clientes/cliente_vencido.html', {'cliente': cliente})










@login_required
@require_POST
def alterar_saldo(request):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        valor = request.POST.get("valor")
        tipo = request.POST.get("tipo")

        if not cliente_id or not valor or not tipo:
            return JsonResponse({"status": "error", "message": "Dados inválidos."}, status=400)

        try:
            clientes = CustomUser.objects.all()
            if not request.user.is_superuser:
                clientes = clientes.filter(dono=request.user)
            cliente = get_object_or_404(clientes, pk=cliente_id)
            valor_decimal = Decimal(valor)

            if tipo == "adicionar":
                cliente.saldo += valor_decimal
            elif tipo == "debitar":
                cliente.saldo -= valor_decimal
            else:
                return JsonResponse({"status": "error", "message": "Tipo de operação inválido."}, status=400)

            cliente.save()

            # Calcula valor total a pagar com o novo saldo
            # saldo positivo = crédito (desconta da parcela)
            # saldo negativo = débito (soma à parcela)
            valor_a_pagar = cliente.valor_a_pagar or Decimal('0.00')
            saldo = cliente.saldo

            if saldo < 0:
                valor_total = valor_a_pagar + abs(saldo)
            else:
                valor_total = max(Decimal('0.00'), valor_a_pagar - saldo)

            return JsonResponse({
                "status": "success",
                "message": "Saldo atualizado com sucesso!",
                "cliente": {
                    "id": cliente.id,
                    "saldo": str(saldo),
                },
                "valor_total_a_pagar": str(valor_total),
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error", "message": "Método inválido."}, status=405)



@login_required
def detalhes_cliente(request, pk):
    cliente = get_object_or_404(CustomUser, pk=pk)
    return render(request, 'clientes/detalhes_cliente.html', {'cliente': cliente})



@login_required
def listar_servicos(request):
    user = request.user

    # Lista apenas os serviços associados ao usuário logado (revenda)
    servicos = Servico.objects.filter(revenda=user)

    if request.method == 'POST':
        form = ServicoForm(request.POST)
        if form.is_valid():
            servico = form.save(commit=False)
            servico.revenda = user  # Associa o serviço à revenda logada
            servico.save()
            return redirect('listar_servicos')
    else:
        form = ServicoForm()

    return render(request, 'servicos/listar_servicos.html', {'servicos': servicos, 'form': form})

@login_required
def editar_servico(request, pk):
    servico = get_object_or_404(Servico, pk=pk, revenda=request.user)  # Filtra pelo pk e pela revenda autenticada
    if request.method == 'POST':
        form = ServicoForm(request.POST, instance=servico)
        if form.is_valid():
            form.save()
            return redirect('listar_servicos')
    else:
        form = ServicoForm(instance=servico)
    return render(request, 'servicos/editar_servico.html', {'form': form, 'servico': servico})

@login_required
def excluir_servico(request, pk):
    user = request.user

    # Verificação de permissão baseada no tipo de usuário
    if user.is_superuser:
        # Admin pode excluir qualquer serviço
        servico = get_object_or_404(Servico, pk=pk)
    elif hasattr(user, 'tipo_usuario') and user.tipo_usuario == 'revenda':
        # Revenda só pode excluir serviços associados a ela
        servico = get_object_or_404(Servico, pk=pk, revenda=user)
    else:
        # Cliente não tem permissão para excluir serviços
        return redirect('listar_servicos')

    if request.method == 'POST':
        servico.delete()
        return redirect('listar_servicos')

    return render(request, 'servicos/excluir_servico.html', {'servico': servico})

@login_required
def cadastrar_servico(request):
    if request.method == 'POST':
        form = ServicoForm(request.POST)
        if form.is_valid():
            servico = form.save(commit=False)
            servico.revenda = request.user  # Define a revenda como a revenda autenticada
            servico.save()
            return redirect('listar_servicos')  # Redireciona para a listagem de serviços após o cadastro
    else:
        form = ServicoForm()

    return render(request, 'servicos/cadastrar_servico.html', {'form': form})

# Valor do Serviço



@login_required
def get_valor_servico(request):
    """Retorna apenas valor e custos do plano (SIMPLES)"""
    plano_id = request.GET.get("plano_id")
    if plano_id:
        servico = Servico.objects.filter(pk=plano_id, revenda=request.user).first()
        if servico:
            return JsonResponse({
                "success": True,
                "custos": float(servico.custos) if servico.custos else 0.00,
                "valor": float(servico.valor) if servico.valor else 0.00,
            })
    return JsonResponse({"success": False, "custos": "", "valor": ""})



def tags_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # 🔄 Busca APENAS as tags do usuário logado
    tags = Tag.objects.filter(usuario=request.user).order_by('nome')
    
    form = TagForm()
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        cor = request.POST.get('cor', '#667eea')
        
        if nome:
            # Verifica se já existe para ESTE usuário
            tag_existente = Tag.objects.filter(
                nome__iexact=nome, 
                usuario=request.user
            ).first()
            
            if tag_existente:
                messages.warning(request, f'Tag "{nome}" já existe!')
            else:
                Tag.objects.create(
                    nome=nome,
                    descricao=descricao,
                    cor=cor,
                    usuario=request.user  # ← Associa ao usuário logado
                )
                messages.success(request, f'Tag "{nome}" criada com sucesso!')
                return redirect('tags_page')
        else:
            messages.error(request, 'O nome da tag é obrigatório!')
    
    return render(request, 'tags/tags_page.html', {
        'form': form,
        'tags': tags  # ← Agora só tags do usuário
    })




# ============================================
# VIEW DE EXCLUSÃO (VOLTAR AO ORIGINAL)
# ============================================
def delete_tag(request, tag_id):
    tag = get_object_or_404(Tag, id=tag_id, usuario=request.user)
    
    if request.method == 'POST':
        nome = tag.nome
        tag.delete()
        messages.success(request, f'Tag "{nome}" excluída com sucesso!')
        return redirect('tags_page')
    
    # GET - mostra página de confirmação (modo antigo)
    return render(request, 'tags/delete_tag.html', {'tag': tag})


# ============================================
# VIEW DE EDIÇÃO (VOLTAR AO ORIGINAL)
# ============================================
@login_required
def edit_tag(request, tag_id):
    tag = get_object_or_404(Tag, id=tag_id, usuario=request.user)
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        
        if nome:
            existente = Tag.objects.filter(
                nome__iexact=nome, 
                usuario=request.user
            ).exclude(id=tag_id).first()
            
            if existente:
                messages.error(request, f'Já existe uma tag com o nome "{nome}"!')
            else:
                tag.nome = nome
                tag.descricao = descricao
                tag.save()
                messages.success(request, f'Tag "{nome}" atualizada com sucesso!')
        else:
            messages.error(request, 'O nome da tag é obrigatório!')
        
        return redirect('tags_page')
    
    # GET - mostra formulário de edição
    return render(request, 'tags/edit_tag.html', {'tag': tag})

def buscar_tags(request):
    if not request.user.is_authenticated:
        return JsonResponse([], safe=False)

    query = request.GET.get('q', '')
    
    # 🔒 Filtra apenas tags do usuário logado
    tags = Tag.objects.filter(usuario=request.user)

    if query:
        tags = tags.filter(nome__icontains=query)

    # Retorna no formato que o Select2 espera
    tags_data = list(tags.values('id', 'nome'))
    
    return JsonResponse(tags_data, safe=False)







def logout_view(request):
    """
    View de logout com registro de atividade
    """
    # Salva o nome do usuário antes de fazer logout
    username = None
    if request.user.is_authenticated:
        username = request.user.username
    
    # Tenta registrar o log
    try:
        # Verifica se o modelo LogAtividade existe
        from .models import LogAtividade
        
        if username:
            LogAtividade.registrar(
                request=request,
                usuario=request.user,
                tipo_acao='logout',
                descricao=f"Usuário {username} saiu do sistema"
            )
            logger.info(f"Log de logout registrado para: {username}")
    except ImportError:
        # Modelo ainda não existe (migrations não aplicadas)
        logger.debug("Modelo LogAtividade não disponível")
    except Exception as e:
        # Log do erro mas continua o processo de logout
        logger.error(f"Erro ao registrar log de logout: {e}", exc_info=True)
    
    # Faz logout de qualquer forma
    logout(request)
    
    # Limpa a sessão
    request.session.flush()
    
    # Mensagem de sucesso
    if username:
        messages.info(request, f"Até logo, {username}!")
    
    return redirect('login')





def combine_date_time(date_obj, time_obj):
    from datetime import datetime as dt_class
    return dt_class(
        date_obj.year,
        date_obj.month,
        date_obj.day,
        time_obj.hour,
        time_obj.minute,
        time_obj.second,
        time_obj.microsecond,
        tzinfo=timezone.get_current_timezone()
    )







def combine_date_time(date_obj, time_obj):
    """Combina date e time considerando timezone"""
    naive_datetime = datetime.combine(date_obj, time_obj)
    return timezone.make_aware(naive_datetime)


def agrupar_clientes_por_login_externo(clientes_queryset):
    """
    Agrupa clientes que compartilham o mesmo login_externo,
    retornando apenas 1 representante por grupo para cálculos de custo.
    Clientes sem login_externo são considerados únicos.
    """
    from django.db.models import Min, Count
    
    # Pega os IDs únicos (1 por login_externo + plano, ou o próprio ID se não
    # tiver login). O mesmo username pode existir em servidores diferentes e
    # não deve compartilhar custo entre planos.
    ids_unicos = []
    
    # Primeiro, agrupa apenas logins realmente preenchidos. CharField com
    # blank=True costuma salvar string vazia, e antes todos os "" viravam um
    # único grupo, reduzindo artificialmente clientes/custos do dashboard.
    grupos = clientes_queryset.filter(
        login_externo__isnull=False,
    ).exclude(
        login_externo='',
    ).values('login_externo', 'plano_id').annotate(
        primeiro_id=Min('id'),
        total=Count('id')
    )
    
    for grupo in grupos:
        ids_unicos.append(grupo['primeiro_id'])
    
    # Clientes sem login_externo, nulo ou vazio, contam individualmente.
    for cliente in clientes_queryset.filter(
        Q(login_externo__isnull=True) | Q(login_externo='')
    ).values_list('id', flat=True):
        ids_unicos.append(cliente)
    
    return clientes_queryset.filter(id__in=ids_unicos)


def calcular_custo_compartilhado(clientes_queryset):
    """
    Calcula o custo total considerando compartilhamento de créditos.
    - Clientes com mesmo login_externo dividem o custo do crédito.
    - Clientes sem login_externo ou únicos pagam o custo integral.
    
    Exemplo:
    - 2 clientes com login_externo="chico", custo R$ 6 → custo total = R$ 6
    - 1 cliente com login_externo="maria", custo R$ 6 → custo total = R$ 6
    - 1 cliente sem login_externo, custo R$ 6 → custo total = R$ 6
    """
    from django.db.models import Min
    
    custo_total = Decimal('0')
    
    # Agrupa por login_externo + plano. Um username igual em servidores
    # diferentes não representa o mesmo crédito/assinatura.
    grupos = clientes_queryset.filter(
        login_externo__isnull=False,
    ).exclude(
        login_externo='',
    ).values('login_externo', 'plano_id').annotate(
        custo_individual=Min('valor_servico')
    )
    
    for grupo in grupos:
        custo = grupo['custo_individual'] or Decimal('0')
        # Cada grupo de login_externo paga apenas 1 custo
        custo_total += custo
    
    # Clientes sem login_externo (nulo ou vazio) pagam seu próprio custo.
    for cliente in clientes_queryset.filter(
        Q(login_externo__isnull=True) | Q(login_externo='')
    ):
        custo_total += (cliente.valor_servico or Decimal('0'))
    
    return custo_total


@never_cache
@login_required
def dashboard_view(request):
    """
    Dashboard completo com métricas financeiras, clientes, créditos e ranking de servidores
    AGORA COM FILTRO POR DATA E HORA - age como se a data/hora selecionada fosse AGORA
    """
    
    from datetime import datetime as dt_datetime
    
    # ===== 🎯 CAPTURA DA DATA E HORA DE REFERÊNCIA =====
    data_referencia_str = request.GET.get('data_referencia')
    hora_referencia_str = request.GET.get('hora_referencia')
    
    agora_real = timezone.localtime()

    if data_referencia_str:
        try:
            hoje = dt_datetime.strptime(data_referencia_str, '%Y-%m-%d').date()
            if hoje > agora_real.date():
                hoje = agora_real.date()
        except (ValueError, TypeError):
            hoje = agora_real.date()
    else:
        hoje = agora_real.date()

    if hora_referencia_str:
        try:
            hora_ref = dt_datetime.strptime(hora_referencia_str, '%H:%M').time()
        except (ValueError, TypeError):
            hora_ref = time.max
    else:
        if hoje == agora_real.date():
            hora_ref = agora_real.time()
        else:
            hora_ref = time.max

    if hoje == agora_real.date() and hora_ref > agora_real.time():
        hora_ref = agora_real.time()

    hora_referencia_str = hora_ref.strftime('%H:%M')
    data_hora_ref = dt_datetime.combine(hoje, hora_ref)
    data_hora_ref_aware = timezone.make_aware(data_hora_ref, timezone.get_current_timezone())
    data_referencia_iso = hoje.strftime('%Y-%m-%d')

    agora_sem_segundos = agora_real.replace(second=0, microsecond=0)
    data_hora_ref_local = timezone.localtime(data_hora_ref_aware).replace(second=0, microsecond=0)
    visualizando_passado = data_hora_ref_local < agora_sem_segundos
    
    # ===== 1. CONFIGURAÇÃO DE DATAS =====
    amanha = hoje + timedelta(days=1)
    depois_de_amanha = hoje + timedelta(days=2)
    
    inicio_dia = combine_date_time(hoje, time.min)
    fim_dia = combine_date_time(hoje, time.max)
    
    # 🔥 CORRIGIDO: Semana começa no DOMINGO
    dia_semana_hoje = hoje.weekday()  # 0=segunda, 1=terça, ..., 6=domingo
    
    # Ajuste: domingo = início da semana
    if dia_semana_hoje == 6:  # Hoje é domingo
        inicio_semana = hoje
    else:
        inicio_semana = hoje - timedelta(days=dia_semana_hoje + 1)
    
    # Fim da semana (sábado)
    fim_semana = inicio_semana + timedelta(days=6)
    
    ano_atual = hoje.year
    mes_atual = hoje.month
    
    if mes_atual == 12:
        primeiro_dia_prox_mes = date(ano_atual + 1, 1, 1)
    else:
        primeiro_dia_prox_mes = date(ano_atual, mes_atual + 1, 1)
    
    inicio_mes_atual = date(ano_atual, mes_atual, 1)
    fim_mes_atual = primeiro_dia_prox_mes - timedelta(days=1)
    inicio_mes_aware = combine_date_time(inicio_mes_atual, time.min)
    fim_mes_aware = combine_date_time(fim_mes_atual, time.max)
    
    if mes_atual == 1:
        inicio_mes_anterior = date(ano_atual - 1, 12, 1)
        fim_mes_anterior = date(ano_atual - 1, 12, 31)
    else:
        inicio_mes_anterior = date(ano_atual, mes_atual - 1, 1)
        fim_mes_anterior = inicio_mes_atual - timedelta(days=1)

    # Compara MTD com o mesmo intervalo do mês anterior. Comparar, por
    # exemplo, os primeiros 7 dias do mês atual com os 31 dias inteiros do
    # mês anterior distorcia o crescimento mensal no começo de cada mês.
    dia_equivalente_mes_anterior = min(hoje.day, fim_mes_anterior.day)
    fim_periodo_mes_anterior = date(
        fim_mes_anterior.year,
        fim_mes_anterior.month,
        dia_equivalente_mes_anterior,
    )
    
    inicio_ano = date(ano_atual, 1, 1)
    fim_ano = date(ano_atual, 12, 31)
    inicio_ano_aware = combine_date_time(inicio_ano, time.min)
    inicio_12_meses = (hoje - relativedelta(months=12)).replace(day=1)
    
    # ===== 2. QUERYSETS =====
    try:
        # O corte por data/hora precisa acontecer no queryset base. Antes o
        # dashboard filtrava clientes apenas pela data, então ao visualizar
        # 10:00 apareciam clientes criados às 15:00 do mesmo dia.
        base_query_clientes_todos = CustomUser.objects.filter(
            dono=request.user,
            data_criacao__lte=data_hora_ref_aware,
        )
        base_query_relatorios = RelatorioFinanceiro.objects.filter(
            cliente__dono=request.user,
            data_geracao__lte=data_hora_ref_aware
        )
    except Exception:
        logger.exception("Falha ao montar os querysets base do dashboard")
        base_query_clientes_todos = CustomUser.objects.none()
        base_query_relatorios = RelatorioFinanceiro.objects.none()
    
    base_query_clientes_ativos = base_query_clientes_todos.filter(
        is_active=True,
    )
    
    # ===== 3. MÉTRICAS DE CLIENTES =====
    total_clientes_ativos = base_query_clientes_ativos.count()
    clientes_vencidos = base_query_clientes_ativos.filter(data_vencimento__lt=hoje).count()
    clientes_em_dia = base_query_clientes_ativos.filter(data_vencimento__gte=hoje).count()
    clientes_a_vencer_hoje = base_query_clientes_ativos.filter(data_vencimento=hoje).count()
    clientes_a_vencer_amanha = base_query_clientes_ativos.filter(data_vencimento=amanha).count()
    clientes_a_vencer_restante_mes = base_query_clientes_ativos.filter(
        data_vencimento__gte=depois_de_amanha,
        data_vencimento__lte=fim_mes_atual
    ).count()
    clientes_desativados = base_query_clientes_todos.filter(
        is_active=False,
    ).count()
    clientes_novos_mes = base_query_clientes_todos.filter(
        date_joined__gte=inicio_mes_aware,
        date_joined__lte=data_hora_ref_aware,
    ).count()
    total_clientes = base_query_clientes_todos.count()
    taxa_desativacao = round((clientes_desativados / total_clientes * 100), 1) if total_clientes > 0 else 0
    taxa_retencao = round(100 - taxa_desativacao, 1)
    
    # ===== 4. MÉTRICAS FINANCEIRAS =====
    receita_diaria = base_query_relatorios.filter(
        data_geracao__date=hoje
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
    
    lucro_diario = base_query_relatorios.filter(
        data_geracao__date=hoje
    ).aggregate(total=Sum('valor_liquido'))['total'] or Decimal('0')
    
    receita_semanal = base_query_relatorios.filter(
        data_geracao__date__gte=inicio_semana,
        data_geracao__date__lte=fim_semana
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
    
    lucro_semanal = base_query_relatorios.filter(
        data_geracao__date__gte=inicio_semana,
        data_geracao__date__lte=fim_semana
    ).aggregate(total=Sum('valor_liquido'))['total'] or Decimal('0')
    
    receita_mensal_bruto = base_query_relatorios.filter(
        data_geracao__gte=inicio_mes_aware,
        data_geracao__date__lte=hoje
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
    
    receita_mensal_liquido = base_query_relatorios.filter(
        data_geracao__gte=inicio_mes_aware,
        data_geracao__date__lte=hoje
    ).aggregate(total=Sum('valor_liquido'))['total'] or Decimal('0')
    
    receita_mes_anterior = base_query_relatorios.filter(
        data_geracao__date__gte=inicio_mes_anterior,
        data_geracao__date__lte=fim_periodo_mes_anterior
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
    
    receita_anual_bruto = base_query_relatorios.filter(
        data_geracao__gte=inicio_ano_aware,
        data_geracao__date__lte=hoje
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')
    
    receita_anual_liquido = base_query_relatorios.filter(
        data_geracao__gte=inicio_ano_aware,
        data_geracao__date__lte=hoje
    ).aggregate(total=Sum('valor_liquido'))['total'] or Decimal('0')
    
    if receita_mes_anterior > 0:
        crescimento_mensal = round(float((receita_mensal_bruto - receita_mes_anterior) / receita_mes_anterior * 100), 1)
    else:
        crescimento_mensal = 100 if receita_mensal_bruto > 0 else 0
    
    total_clientes_mes = base_query_relatorios.filter(
        data_geracao__gte=inicio_mes_aware,
        data_geracao__date__lte=hoje
    ).values('cliente').distinct().count()
    
    ticket_medio = (receita_mensal_bruto / Decimal(str(total_clientes_mes))).quantize(Decimal('0.01')) if total_clientes_mes > 0 else Decimal('0')
    ticket_medio_liquido = (receita_mensal_liquido / Decimal(str(total_clientes_mes))).quantize(Decimal('0.01')) if total_clientes_mes > 0 else Decimal('0')
    margem_lucro = round(float((receita_mensal_liquido / receita_mensal_bruto * 100)), 1) if receita_mensal_bruto > 0 else 0
    
    # ===== 5. RANKING DE SERVIDORES =====
    def ranking_servidores(queryset, limite=5):
        ranking = queryset.filter(servidor__isnull=False).exclude(servidor='').values(
            'servidor'
        ).annotate(
            total_vendas=Count('id'),
            receita_bruta=Sum('valor_pago'),
            lucro=Sum('valor_liquido')
        ).order_by('-total_vendas', '-lucro')[:limite]
        return list(ranking)
    
    ranking_semana = ranking_servidores(
        base_query_relatorios.filter(
            data_geracao__date__gte=inicio_semana,
            data_geracao__date__lte=fim_semana
        )
    )
    
    ranking_mes = ranking_servidores(
        base_query_relatorios.filter(
            data_geracao__gte=inicio_mes_aware,
            data_geracao__date__lte=hoje
        )
    )
    
    ranking_ano = ranking_servidores(
        base_query_relatorios.filter(
            data_geracao__gte=inicio_ano_aware,
            data_geracao__date__lte=hoje
        )
    )
    
    servidor_mais_vendido = ranking_mes[0]['servidor'] if ranking_mes else "Nenhum"
    
    # ===== 6. GRÁFICOS =====
    chart_ativos_futuros = base_query_clientes_ativos.filter(data_vencimento__gt=fim_mes_atual).count()
    chart_a_vencer_mes = clientes_a_vencer_hoje + clientes_a_vencer_amanha + clientes_a_vencer_restante_mes
    
    meses_query = base_query_relatorios.filter(
        data_geracao__date__gte=inicio_12_meses,
        data_geracao__date__lte=hoje
    ).annotate(
        mes=TruncMonth('data_geracao')
    ).values('mes').annotate(
        bruto=Sum('valor_pago'),
        liquido=Sum('valor_liquido')
    ).order_by('mes')
    
    labels_12_meses = []
    bruto_12_meses = []
    liquido_12_meses = []
    meses_abreviados = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez',
    }
    
    for i in range(11, -1, -1):
        mes_data = (hoje.replace(day=1) - relativedelta(months=i))
        labels_12_meses.append(
            f"{meses_abreviados.get(mes_data.month, mes_data.month)}/{str(mes_data.year)[-2:]}"
        )
        bruto_12_meses.append(Decimal('0'))
        liquido_12_meses.append(Decimal('0'))
    
    for item in meses_query:
        if item.get('mes'):
            mes_date = item['mes']
            diff = (hoje.year - mes_date.year) * 12 + (hoje.month - mes_date.month)
            idx = 11 - diff
            if 0 <= idx < 12:
                bruto_12_meses[idx] = item.get('bruto') or Decimal('0')
                liquido_12_meses[idx] = item.get('liquido') or Decimal('0')

    # ===== COMPARAÇÃO DIÁRIA =====
    labels_comparacao_dias = []
    mes_atual_comparacao = []
    mes_anterior_comparacao = []
    
    ultimo_dia_comparacao = hoje.day
    dias_mes_anterior = fim_mes_anterior.day

    comparacao_query = base_query_relatorios.filter(
        data_geracao__date__gte=inicio_mes_anterior,
        data_geracao__date__lte=hoje
    ).annotate(
        dia=TruncDate('data_geracao')
    ).values('dia').annotate(
        bruto=Sum('valor_pago'),
        liquido=Sum('valor_liquido')
    ).order_by('dia')

    valores_por_dia = {}
    for item in comparacao_query:
        data_item = item.get('dia')
        if data_item:
            valores_por_dia[data_item] = {
                'bruto': item.get('bruto') or Decimal('0'),
                'liquido': item.get('liquido') or Decimal('0'),
            }

    for numero_dia in range(1, ultimo_dia_comparacao + 1):
        labels_comparacao_dias.append(str(numero_dia))
        data_mes_atual = date(ano_atual, mes_atual, numero_dia)
        dados = valores_por_dia.get(data_mes_atual, {'bruto': Decimal('0'), 'liquido': Decimal('0')})
        mes_atual_comparacao.append(dados['bruto'])
        
        if numero_dia <= dias_mes_anterior:
            data_mes_anterior = date(inicio_mes_anterior.year, inicio_mes_anterior.month, numero_dia)
            dados_ant = valores_por_dia.get(data_mes_anterior, {'bruto': Decimal('0'), 'liquido': Decimal('0')})
            mes_anterior_comparacao.append(dados_ant['bruto'])
        else:
            mes_anterior_comparacao.append(Decimal('0'))

    receita_dia_mes_atual = mes_atual_comparacao[-1] if mes_atual_comparacao else Decimal('0')
    receita_dia_mes_anterior = mes_anterior_comparacao[-1] if mes_anterior_comparacao else Decimal('0')
    receita_acumulada_mes_atual = sum(mes_atual_comparacao, Decimal('0'))
    receita_acumulada_mes_anterior = sum(mes_anterior_comparacao, Decimal('0'))
    
    diferenca_dia = receita_dia_mes_atual - receita_dia_mes_anterior
    diferenca_mes = receita_acumulada_mes_atual - receita_acumulada_mes_anterior
    diferenca_dia_absoluta = abs(diferenca_dia)
    diferenca_mes_absoluta = abs(diferenca_mes)

    if receita_dia_mes_anterior > 0:
        variacao_comparacao_dia = round(float(diferenca_dia / receita_dia_mes_anterior * 100), 1)
    elif receita_dia_mes_atual > 0:
        variacao_comparacao_dia = None
    else:
        variacao_comparacao_dia = 0

    if receita_acumulada_mes_anterior > 0:
        variacao_comparacao_mes = round(float(diferenca_mes / receita_acumulada_mes_anterior * 100), 1)
    elif receita_acumulada_mes_atual > 0:
        variacao_comparacao_mes = 100.0
    else:
        variacao_comparacao_mes = 0.0

    # ===== MENSAGENS COMPARATIVAS (INICIALIZADAS ANTES DOS IFs) =====
    mensagem_comparacao_dia = 'Nenhuma entrada registrada neste dia nos dois meses.'
    status_comparacao_dia = 'neutro'
    
    mensagem_comparacao_mes = 'Ainda não há faturamento acumulado para comparar os meses.'
    status_comparacao_mes = 'neutro'

    if receita_dia_mes_atual == 0 and receita_dia_mes_anterior == 0:
        mensagem_comparacao_dia = 'Nenhuma entrada registrada neste dia nos dois meses.'
        status_comparacao_dia = 'neutro'
    elif receita_dia_mes_atual > receita_dia_mes_anterior:
        if receita_dia_mes_anterior == 0:
            mensagem_comparacao_dia = (
                f'Dia produtivo! Foram registrados R$ '
                f'{receita_dia_mes_atual:.2f} em entradas. '
                f'No mesmo dia do mês anterior não houve movimentação.'
            )
        else:
            mensagem_comparacao_dia = (
                f'Dia produtivo! As entradas ficaram R$ '
                f'{diferenca_dia_absoluta:.2f} acima do mesmo dia '
                f'do mês anterior.'
            )
        status_comparacao_dia = 'otimo'
    elif receita_dia_mes_atual < receita_dia_mes_anterior:
        mensagem_comparacao_dia = (
            f'As entradas deste dia ficaram R$ '
            f'{diferenca_dia_absoluta:.2f} abaixo do mesmo dia '
            f'do mês anterior.'
        )
        status_comparacao_dia = 'atencao'
    else:
        mensagem_comparacao_dia = (
            f'Dia estável. As entradas foram iguais às registradas '
            f'no mesmo dia do mês anterior.'
        )
        status_comparacao_dia = 'estavel'

    if receita_acumulada_mes_atual == 0 and receita_acumulada_mes_anterior == 0:
        mensagem_comparacao_mes = 'Ainda não há faturamento acumulado para comparar os meses.'
        status_comparacao_mes = 'neutro'
    elif receita_acumulada_mes_atual > receita_acumulada_mes_anterior:
        mensagem_comparacao_mes = (
            f'O mês está evoluindo bem. Até agora foram faturados R$ '
            f'{receita_acumulada_mes_atual:.2f}, ficando R$ '
            f'{abs(diferenca_mes):.2f} acima do mesmo período do mês anterior.'
        )
        status_comparacao_mes = 'otimo'
    elif receita_acumulada_mes_atual == receita_acumulada_mes_anterior:
        mensagem_comparacao_mes = (
            f'O mês segue equilibrado. O acumulado atual é de R$ '
            f'{receita_acumulada_mes_atual:.2f}, igual ao mesmo período '
            f'do mês anterior.'
        )
        status_comparacao_mes = 'estavel'
    else:
        mensagem_comparacao_mes = (
            f'O mês está abaixo do período anterior. Até agora foram faturados '
            f'R$ {receita_acumulada_mes_atual:.2f}, contra R$ '
            f'{receita_acumulada_mes_anterior:.2f} no mesmo período do mês '
            f'anterior. A diferença é de R$ {abs(diferenca_mes):.2f} a menos.'
        )
        status_comparacao_mes = 'atencao'

    # ===== 7. PREVISÕES (CORRIGIDO - Bruto soma tudo, Custo compartilhado) =====
    
    # ===== 7. PREVISÕES (CORRIGIDO - Bruto soma TODOS, Custo por username) =====

# 🔥 SEMANAL (Domingo a Sábado)
    clientes_semana_todos = base_query_clientes_ativos.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=fim_semana
    )

    # 🔥 BRUTO: Soma o valor_a_pagar de TODOS os clientes (sem agrupar)
    previsao_semanal_bruto = Decimal('0')
    for cliente in clientes_semana_todos:
        previsao_semanal_bruto += (cliente.valor_a_pagar or Decimal('0'))



    # 🔥 CUSTO: Considera compartilhamento (1 custo por username)
    previsao_semanal_custo = calcular_custo_compartilhado(clientes_semana_todos)


    # 🔥 LÍQUIDO
    previsao_semanal_liquido = previsao_semanal_bruto - previsao_semanal_custo


    previsao_clientes_semana = clientes_semana_todos.count()


    # 🔥 MENSAL
    clientes_mes_todos = base_query_clientes_ativos.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=fim_mes_atual
    )

    previsao_mensal_bruto = Decimal('0')
    for cliente in clientes_mes_todos:
        previsao_mensal_bruto += (cliente.valor_a_pagar or Decimal('0'))

    previsao_mensal_custo = calcular_custo_compartilhado(clientes_mes_todos)
    previsao_mensal_liquido = previsao_mensal_bruto - previsao_mensal_custo
    previsao_clientes_mes = clientes_mes_todos.count()


    # 🔥 ANUAL
    receita_ano_realizada = base_query_relatorios.filter(
        data_geracao__gte=inicio_ano_aware,
        data_geracao__date__lte=hoje
    ).aggregate(total=Sum('valor_pago'))['total'] or Decimal('0')

    receita_ano_liquida_realizada = base_query_relatorios.filter(
        data_geracao__gte=inicio_ano_aware,
        data_geracao__date__lte=hoje
    ).aggregate(total=Sum('valor_liquido'))['total'] or Decimal('0')

    clientes_restante_ano_todos = base_query_clientes_ativos.filter(
        data_vencimento__gte=hoje,
        data_vencimento__lte=fim_ano
    )

    previsao_anual_bruto = receita_ano_realizada
    for cliente in clientes_restante_ano_todos:
        previsao_anual_bruto += (cliente.valor_a_pagar or Decimal('0'))

    previsao_anual_custo = calcular_custo_compartilhado(clientes_restante_ano_todos)
    # O líquido realizado já contém o custo das vendas passadas. Somar o
    # bruto realizado e descontar apenas o custo futuro superestimava a
    # previsão líquida anual.
    previsao_anual_liquido = (
        receita_ano_liquida_realizada
        + (previsao_anual_bruto - receita_ano_realizada)
        - previsao_anual_custo
    )
    previsao_clientes_ano = clientes_restante_ano_todos.count()
    
    # ===== 8. RENOVAÇÕES =====
    clientes_novos_ids = base_query_clientes_todos.filter(
        date_joined__gte=inicio_mes_aware,
        date_joined__lte=data_hora_ref_aware,
    ).values_list('id', flat=True)
    
    clientes_renovado_mes = base_query_relatorios.filter(
        data_geracao__gte=inicio_mes_aware,
        data_geracao__date__lte=hoje
    ).exclude(cliente_id__in=list(clientes_novos_ids)).values('cliente_id').distinct().count()
    
    # ===== 9. CRÉDITOS DETALHADOS POR SERVIDOR =====
    creditos_por_servidor = []
    dias_ate_esgotar = None
    consumo_medio_diario = Decimal('0')
    creditos_totais = 0
    planos_estoque_baixo = []
    gasto_creditos_12m = Decimal('0')
    custo_medio_credito = Decimal('0')

    try:
        lotes_ate_referencia = list(
            LoteEstoque.objects.filter(
                servico__revenda=request.user,
                data_compra__lte=data_hora_ref_aware,
            ).select_related('servico')
        )

        # Para uma data/hora histórica, quantidade_restante representa o
        # estoque de hoje, não o estoque daquele momento. Reconstruímos o
        # saldo a partir da quantidade comprada e dos consumos registrados
        # até o instante selecionado. No momento atual preservamos o saldo
        # persistido, inclusive eventuais ajustes manuais.
        saldo_por_lote = {}
        if visualizando_passado and lotes_ate_referencia:
            consumos_por_lote = dict(
                VendaCredito.objects.filter(
                    lote__in=lotes_ate_referencia,
                    data_venda__lte=data_hora_ref_aware,
                ).values('lote_id').annotate(
                    total=Sum('quantidade')
                ).values_list('lote_id', 'total')
            )
            for lote in lotes_ate_referencia:
                consumido = consumos_por_lote.get(lote.id) or 0
                saldo_por_lote[lote.id] = max(0, lote.quantidade - consumido)
        else:
            saldo_por_lote = {
                lote.id: max(0, lote.quantidade_restante)
                for lote in lotes_ate_referencia
            }

        creditos_totais = sum(saldo_por_lote.values())
        
        data_30_dias = hoje - timedelta(days=30)
        consumo_total = VendaCredito.objects.filter(
            servico__revenda=request.user,
            data_venda__date__gte=data_30_dias,
            data_venda__lte=data_hora_ref_aware,
        ).aggregate(total=Sum('quantidade'))['total'] or 0
        
        consumo_medio_diario = Decimal(str(consumo_total)) / Decimal('30') if consumo_total > 0 else Decimal('0')
        
        if consumo_medio_diario > 0 and creditos_totais > 0:
            dias_ate_esgotar = int(Decimal(str(creditos_totais)) / consumo_medio_diario)
        
        planos_com_estoque = Servico.objects.filter(
            revenda=request.user,
            controlar_estoque=True,
            tipo_estoque__in=['creditos', 'ambos'],
            data_criacao__lte=data_hora_ref_aware,
        )
        
        for plano in planos_com_estoque:
            disponivel = sum(
                saldo_por_lote.get(lote.id, 0)
                for lote in lotes_ate_referencia
                if lote.servico_id == plano.id
            )
            
            clientes_unicos_plano = agrupar_clientes_por_login_externo(
                base_query_clientes_ativos.filter(plano=plano)
            )
            
            clientes_ordenados = list(
                clientes_unicos_plano
                .values_list('data_vencimento', flat=True)
                .order_by('data_vencimento')
            )
            
            clientes_no_plano = len(clientes_ordenados)
            
            renovacoes_30d = clientes_unicos_plano.filter(
                data_vencimento__gte=hoje,
                data_vencimento__lte=hoje + timedelta(days=30)
            ).count()
            
            consumo_servidor = VendaCredito.objects.filter(
                servico=plano,
                data_venda__date__gte=data_30_dias,
                data_venda__lte=data_hora_ref_aware,
            ).aggregate(total=Sum('quantidade'))['total'] or 0
            
            if consumo_servidor > 0:
                consumo_diario_servidor = Decimal(str(consumo_servidor)) / Decimal('30')
            else:
                consumo_diario_servidor = Decimal(str(renovacoes_30d)) / Decimal('30') if renovacoes_30d > 0 else Decimal('0')
            
            data_esgotamento = None
            dias_servidor = None
            
            if disponivel > 0 and clientes_no_plano > 0:
                vencimentos_futuros = [v for v in clientes_ordenados if v and v >= hoje]
                if vencimentos_futuros:
                    if disponivel <= len(vencimentos_futuros):
                        data_esgotamento = vencimentos_futuros[disponivel - 1]
                    else:
                        data_esgotamento = vencimentos_futuros[-1]
                    dias_servidor = (data_esgotamento - hoje).days
            elif disponivel == 0 and clientes_no_plano > 0:
                dias_servidor = 0
                data_esgotamento = hoje
            
            alerta = False
            motivo_alerta = ''
            
            if disponivel == 0 and clientes_no_plano > 0:
                alerta = True
                motivo_alerta = 'ESGOTADO'
            elif dias_servidor is not None and dias_servidor <= 7:
                alerta = True
                motivo_alerta = 'Esgota em breve'
            elif renovacoes_30d > disponivel:
                alerta = True
                motivo_alerta = 'Créditos insuficientes!'
            
            creditos_por_servidor.append({
                'nome': plano.nome,
                'cor': plano.cor or '#6c757d',
                'disponivel': disponivel,
                'consumo_diario': float(consumo_diario_servidor),
                'dias_ate_esgotar': dias_servidor,
                'data_esgotamento': data_esgotamento.strftime('%d/%m/%Y') if data_esgotamento else None,
                'clientes_ativos': clientes_no_plano,
                'renovacoes_30d': renovacoes_30d,
                'alerta': alerta,
                'motivo_alerta': motivo_alerta,
            })
            
            if 0 < disponivel <= 10:
                planos_estoque_baixo.append({
                    'nome': plano.nome,
                    'disponivel': disponivel,
                    'cor': plano.cor or '#6c757d'
                })
        
        creditos_por_servidor.sort(key=lambda x: (x['disponivel'] == 0, x['dias_ate_esgotar'] if x['dias_ate_esgotar'] is not None else 9999))
        
        gasto_creditos_12m = LoteEstoque.objects.filter(
            servico__revenda=request.user,
            data_compra__date__gte=inicio_12_meses,
            data_compra__lte=data_hora_ref_aware,
        ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0')

        custo_restante_total = sum(
            Decimal(str(saldo_por_lote.get(lote.id, 0))) * lote.custo_unitario
            for lote in lotes_ate_referencia
        )
        custo_medio_credito = (
            (custo_restante_total / Decimal(str(creditos_totais))).quantize(Decimal('0.01'))
            if creditos_totais > 0 else Decimal('0')
        )
        
    except Exception:
        logger.exception("Falha ao calcular estoque/créditos do dashboard")
    
    # ===== 10. CLIENTE CAMPEÃO E RANKING =====
    def get_nome_exibicao(cliente_dict):
        if not cliente_dict:
            return 'N/A'
        return (cliente_dict.get('cliente__nome') or
                cliente_dict.get('cliente__first_name') or
                cliente_dict.get('cliente__username') or
                'N/A')
    
    ranking_clientes_ano_query = base_query_relatorios.filter(
        data_geracao__gte=inicio_ano_aware,
        data_geracao__date__lte=hoje
    ).values(
        'cliente__id', 'cliente__username', 'cliente__nome', 'cliente__first_name'
    ).annotate(
        total_gasto=Sum('valor_pago'),
        total_liquido=Sum('valor_liquido'),
        total_vendas=Count('id'),
        ultima_compra=Max('data_geracao')
    ).order_by('-total_gasto')[:10]
    
    ranking_clientes_ano = list(ranking_clientes_ano_query)
    for cliente in ranking_clientes_ano:
        cliente['nome_exibicao'] = get_nome_exibicao(cliente)
    
    cliente_campeao = ranking_clientes_ano[0] if ranking_clientes_ano else None
    
    nomes_clientes_bar = []
    valores_clientes_bar = []
    cores_clientes_bar = [
        '#667eea', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
        '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1'
    ]
    
    for i, cliente in enumerate(ranking_clientes_ano):
        nome = cliente.get('nome_exibicao', 'Cliente ' + str(i+1))
        if len(nome) > 20:
            nome = nome[:18] + '...'
        nomes_clientes_bar.append(nome)
        valores_clientes_bar.append(float(cliente['total_gasto']))
    
    cliente_campeao_data = None
    if cliente_campeao:
        cliente_campeao_data = {
            'nome': get_nome_exibicao(cliente_campeao),
            'total_gasto': cliente_campeao.get('total_gasto', Decimal('0')),
            'total_liquido': cliente_campeao.get('total_liquido', Decimal('0')),
            'total_vendas': cliente_campeao.get('total_vendas', 0),
            'ultima_compra': cliente_campeao['ultima_compra'].strftime('%d/%m/%Y') if cliente_campeao.get('ultima_compra') else 'N/A',
        }
    
    # ===== 11. CONTEXTO =====
    meses_extenso = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    context = {
        'dados_dashboard': {
            'total_clientes_ativos_total': total_clientes_ativos,
            'clientes_ativos': clientes_em_dia,
            'clientes_vencidos': clientes_vencidos,
            'clientes_desativados': clientes_desativados,
            'clientes_a_vencer_hoje': clientes_a_vencer_hoje,
            'clientes_a_vencer_amanha': clientes_a_vencer_amanha,
            'clientes_a_vencer_restante_mes': clientes_a_vencer_restante_mes,
            'clientes_criado_mes': clientes_novos_mes,
            'clientes_renovado_mes': clientes_renovado_mes,
            'taxa_desativacao': taxa_desativacao,
            'taxa_retencao': taxa_retencao,
            
            'receita_diaria': receita_diaria,
            'lucro_diario': lucro_diario,
            'receita_semanal': receita_semanal,
            'lucro_semanal': lucro_semanal,
            'receita_mensal_bruto': receita_mensal_bruto,
            'receita_mensal_liquido': receita_mensal_liquido,
            'receita_anual_bruto': receita_anual_bruto,
            'receita_anual_liquido': receita_anual_liquido,
            'crescimento_mensal': crescimento_mensal,
            'ticket_medio': ticket_medio,
            'ticket_medio_liquido': ticket_medio_liquido,
            'margem_lucro': margem_lucro,
            
            'previsao_semanal_bruto': previsao_semanal_bruto,
            'previsao_semanal_liquido': previsao_semanal_liquido,
            'previsao_clientes_semana': previsao_clientes_semana,
            'previsao_mensal_bruto': previsao_mensal_bruto,
            'previsao_mensal_liquido': previsao_mensal_liquido,
            'previsao_clientes_mes': previsao_clientes_mes,
            'previsao_anual_bruto': previsao_anual_bruto,
            'previsao_anual_liquido': previsao_anual_liquido,
            'previsao_clientes_ano': previsao_clientes_ano,
            
            'creditos_disponiveis': creditos_totais,
            'consumo_medio_diario': float(consumo_medio_diario),
            'dias_ate_esgotar': dias_ate_esgotar,
            'planos_estoque_baixo': planos_estoque_baixo,
            'gasto_creditos_12m': gasto_creditos_12m,
            'custo_medio_credito': custo_medio_credito,
            'creditos_por_servidor': creditos_por_servidor,
            
            'ranking_semana': ranking_semana,
            'ranking_mes': ranking_mes,
            'ranking_ano': ranking_ano,
            
            'chart_ativos_futuros': chart_ativos_futuros,
            'chart_a_vencer_mes': chart_a_vencer_mes,
            'chart_vencidos': clientes_vencidos,
            'chart_desativados': clientes_desativados,
            'labels_12_meses': json.dumps(labels_12_meses),
            'bruto_12_meses': json.dumps([float(v) for v in bruto_12_meses]),
            'liquido_12_meses': json.dumps([float(v) for v in liquido_12_meses]),
            # Versões nativas usadas pelo json_script no frontend. Mantemos
            # também as chaves JSON antigas por compatibilidade.
            'labels_12_meses_data': labels_12_meses,
            'bruto_12_meses_data': [float(v) for v in bruto_12_meses],
            'liquido_12_meses_data': [float(v) for v in liquido_12_meses],
            'servidor_mais_vendido': servidor_mais_vendido,
            
            'cliente_campeao': cliente_campeao_data,
            'ranking_clientes_ano': ranking_clientes_ano,
            'nomes_clientes_bar': json.dumps(nomes_clientes_bar),
            'valores_clientes_bar': json.dumps(valores_clientes_bar),
            'cores_clientes_bar': json.dumps(cores_clientes_bar[:len(nomes_clientes_bar)]),
            'nomes_clientes_bar_data': nomes_clientes_bar,
            'valores_clientes_bar_data': valores_clientes_bar,
            'cores_clientes_bar_data': cores_clientes_bar[:len(nomes_clientes_bar)],
            
            'data_atual': hoje.strftime('%d/%m/%Y'),
            'data_referencia_iso': data_referencia_iso,
            'hora_referencia': hora_referencia_str,
            'mes_atual_nome': meses_extenso.get(mes_atual, ''),
            'ano_atual': ano_atual,
            'total_a_vencer_mes': clientes_a_vencer_hoje + clientes_a_vencer_amanha + clientes_a_vencer_restante_mes,
            'visualizando_passado': visualizando_passado,
            'data_hoje_real_iso': agora_real.date().strftime('%Y-%m-%d'),
            'hora_agora_real': agora_real.strftime('%H:%M'),
            
            'labels_comparacao_dias': json.dumps(labels_comparacao_dias),
            'mes_atual_comparacao': json.dumps([float(v) for v in mes_atual_comparacao]),
            'mes_anterior_comparacao': json.dumps([float(v) for v in mes_anterior_comparacao]),
            'labels_comparacao_dias_data': labels_comparacao_dias,
            'mes_atual_comparacao_data': [float(v) for v in mes_atual_comparacao],
            'mes_anterior_comparacao_data': [float(v) for v in mes_anterior_comparacao],
            'receita_dia_mes_atual': receita_dia_mes_atual,
            'receita_dia_mes_anterior': receita_dia_mes_anterior,
            'receita_acumulada_mes_atual': receita_acumulada_mes_atual,
            'receita_acumulada_mes_anterior': receita_acumulada_mes_anterior,
            'variacao_comparacao_dia': variacao_comparacao_dia,
            'variacao_comparacao_mes': variacao_comparacao_mes,
            'mensagem_comparacao_dia': mensagem_comparacao_dia,
            'mensagem_comparacao_mes': mensagem_comparacao_mes,
            'status_comparacao_dia': status_comparacao_dia,
            'status_comparacao_mes': status_comparacao_mes,
            'nome_mes_comparacao_atual': meses_extenso.get(mes_atual, ''),
            'nome_mes_comparacao_anterior': meses_extenso.get(inicio_mes_anterior.month, ''),
            'diferenca_comparacao_dia': diferenca_dia,
            'diferenca_comparacao_mes': diferenca_mes,
            'diferenca_comparacao_dia_absoluta': diferenca_dia_absoluta,
            'diferenca_comparacao_mes_absoluta': diferenca_mes_absoluta,
        }
    }

    
    return render(request, 'dashboard.html', context)
# Mantenha outras views (como a get_mensagem_cliente se ela estiver neste arquivo) inalteradas
########################################### API DE PAGAMNETO #########################################################

# views.py
@login_required
def api_configuracao(request):
    config = Configuracao.objects.filter(usuario=request.user).first()
    return JsonResponse({
        'numero_celular': config.numero_celular if config else None,
        'email': config.email if config else None,
    })

def pagamento_pendente(request, cliente_id):
    cliente = get_object_or_404(CustomUser, id=cliente_id)

    
    # Calcula o valor total a pagar com base no saldo e valor_a_pagar
    if cliente.saldo < 0:
        valor_total_a_pagar = cliente.valor_a_pagar + abs(cliente.saldo)
    else:
        valor_total_a_pagar = max(0, cliente.valor_a_pagar - cliente.saldo)

    cliente.valor_total_a_pagar = valor_total_a_pagar  # Passa o valor calculado ao template
    
    historico_pagamentos = cliente.pagamentos.all()  # ajuste conforme seu relacionamento

    return render(request, 'cliente_vencido.html', {
        'cliente': cliente,
        'historico_pagamentos': historico_pagamentos,
    })


def gerar_pix(request, cliente_id):
    """Funcionalidade temporariamente desativada"""
    return JsonResponse({
        "qr_code": False, 
        "message": "Funcionalidade de PIX está temporariamente desabilitada"
    }, status=501)  # 501 = Not Implemented

def verificar_pagamento(request, cliente_id):
    """Funcionalidade temporariamente desativada"""
    return JsonResponse({
        "pagamentoRealizado": False,
        "message": "Verificação de pagamento está temporariamente desabilitada"
    })

###################################### API DO WHATSSAP #######################################################

class ManageInstanceView(View):
    
    def get(self, request):
        # Renderiza a página principal de gerenciamento de instâncias
        return render(request, "manage_instance.html")



def historico_mensagens(request):
    mensagens = Mensagem.objects.all()
    return render(request, "mensagens.html", {"mensagens": mensagens})



class EditarMensagemView(View):
    def get(self, request, pk):
        # Recuperar a mensagem para edição
        mensagem = get_object_or_404(Mensagem, pk=pk)
        return render(request, 'editar_mensagem.html', {'mensagem': mensagem})

    def post(self, request, pk):
        mensagem = get_object_or_404(Mensagem, pk=pk)
        conteudo = request.POST.get('conteudo')
        
        # Atualiza o conteúdo da mensagem e redefine o status para 'não enviada'
        mensagem.conteudo = conteudo
        mensagem.status_envio = False  # Marcar como não enviada se for editada
        mensagem.save()
        
        return redirect('enviar_mensagem')

class ApagarMensagemView(View):
    def post(self, request, pk):
        # Recuperar e deletar a mensagem
        mensagem = get_object_or_404(Mensagem, pk=pk)
        mensagem.delete()
        return redirect('enviar_mensagem')


@login_required
def configuracao_mensagens(request):
    configuracao, created = ConfiguracaoMensagem.objects.get_or_create(usuario=request.user)
    mensagens = MensagemConfigurada.objects.filter(configuracao=configuracao)
    
    if request.method == "POST":
        tipo = request.POST.get("tipo", "")
        
        # 🔥 Salvar mensagens fixas (boas-vindas e pagamento)
        if tipo == "bemvindo":
            mensagem_bem_vindo = request.POST.get('mensagem_bem_vindo', '').strip()
            configuracao.mensagem_bem_vindo = mensagem_bem_vindo or None
            configuracao.save()
            messages.success(request, "Mensagem de boas-vindas salva!")
            return redirect("configuracao_mensagens")
        
        if tipo == "pagamento":
            mensagem_pagamento = request.POST.get('mensagem_confirmacao_pagamento', '').strip()
            configuracao.mensagem_confirmacao_pagamento = mensagem_pagamento or None
            configuracao.save()
            messages.success(request, "Mensagem de pagamento salva!")
            return redirect("configuracao_mensagens")
        
        # Salvar mensagem de vencimento (lógica existente)
        mensagem_id = request.POST.get("mensagem_id")
        if mensagem_id:
            mensagem = get_object_or_404(MensagemConfigurada, id=mensagem_id, configuracao=configuracao)
            form = MensagemConfiguradaForm(request.POST, instance=mensagem)
        else:
            form = MensagemConfiguradaForm(request.POST)
        
        if form.is_valid():
            obj = form.save(commit=False)
            obj.configuracao = configuracao
            obj.save()
            messages.success(request, "Mensagem de vencimento salva!")
            return redirect("configuracao_mensagens")
        else:
            messages.error(request, "Erro ao salvar. Verifique os campos.")
    
    return render(request, "configuracao_mensagens.html", {
        "mensagens": mensagens,
        "configuracao": configuracao,
    })

@login_required
def remover_mensagem(request, mensagem_id):
    """Remove uma mensagem via POST (chamado por AJAX)."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método não permitido."}, status=405)
    
    try:
        configuracao = get_object_or_404(ConfiguracaoMensagem, usuario=request.user)
        mensagem = get_object_or_404(
            MensagemConfigurada,
            id=mensagem_id,
            configuracao=configuracao
        )
        mensagem.delete()
        return JsonResponse({"success": True})
    except Exception as e:
        logger.error(f"Erro ao remover mensagem {mensagem_id}: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def salvar_configuracao_mensagens(request):
    if request.method != "POST":
        return redirect("configuracao_mensagens")
    
    configuracao, _ = ConfiguracaoMensagem.objects.get_or_create(usuario=request.user)
    
    if "criterio_dias" in request.POST:
        form = MensagemConfiguradaForm(request.POST)
        if form.is_valid():
            mensagem = form.save(commit=False)
            mensagem.configuracao = configuracao
            mensagem.save()
            return JsonResponse({
                "success": True,
                "id": mensagem.id,
                "criterio_dias": mensagem.criterio_dias,
                "mensagem_texto": mensagem.mensagem_texto,
                "horario_envio": mensagem.horario_envio.strftime("%H:%M"),
            })
        return JsonResponse({"success": False, "errors": form.errors}, status=400)
    
    messages.success(request, "Configurações salvas com sucesso!")
    return redirect("configuracao_mensagens")


@login_required
def detalhe_mensagem(request, mensagem_id):
    configuracao = get_object_or_404(ConfiguracaoMensagem, usuario=request.user)
    mensagem = get_object_or_404(MensagemConfigurada, id=mensagem_id, configuracao=configuracao)
    return JsonResponse({
        "id": mensagem.id,
        "criterio_dias": mensagem.criterio_dias,
        "mensagem_texto": mensagem.mensagem_texto,
        "horario_envio": mensagem.horario_envio.strftime("%H:%M"),
    })


# ============================================================
# FUNÇÃO ÚNICA DE BOAS-VINDAS (substitui as 2 antigas)
# ============================================================
def enviar_mensagem_boas_vindas(cliente, user=None):
    """
    Envia a mensagem de boas-vindas usando:
    - variáveis centralizadas;
    - instância conectada do usuário;
    - configurações oficiais da Evolution API.
    """

    try:
        if not cliente:
            logger.error("Boas-vindas: cliente não informado.")
            return False

        dono = getattr(cliente, "dono", None)

        if not dono:
            logger.warning(
                "Boas-vindas: cliente %s não possui dono.",
                getattr(cliente, "id", "sem ID"),
            )
            return False

        config = ConfiguracaoMensagem.objects.filter(
            usuario=dono
        ).first()

        if not config:
            logger.info(
                "Boas-vindas: configuração não encontrada para %s.",
                dono.username,
            )
            return False

        template = (
            getattr(config, "mensagem_bem_vindo", "")
            or ""
        ).strip()

        if not template:
            logger.info(
                "Boas-vindas: mensagem não configurada para %s.",
                dono.username,
            )
            return False

        if not cliente.whatsapp:
            logger.warning(
                "Boas-vindas: cliente %s sem WhatsApp.",
                cliente.nome,
            )
            return False

        usuario_instancia = user or dono

        instance = UserInstance.objects.filter(
            user=usuario_instancia,
            status="connected",
            is_active=True,
        ).first()

        if not instance:
            logger.warning(
                "Boas-vindas: usuário %s sem instância conectada.",
                usuario_instancia.username,
            )
            return False

        mensagem = substituir_variaveis_mensagem(
            template,
            cliente,
        )

        if not mensagem:
            logger.error(
                "Boas-vindas: mensagem ficou vazia para %s.",
                cliente.nome,
            )
            return False

        numero = re.sub(
            r"\D",
            "",
            str(cliente.whatsapp),
        )

        if not numero:
            logger.error(
                "Boas-vindas: número inválido para %s.",
                cliente.nome,
            )
            return False

        if len(numero) in (10, 11):
            numero = f"55{numero}"

        if numero.startswith("5555"):
            numero = numero[2:]

        base_url = getattr(
            settings,
            "EVOLUTION_API_BASE_URL",
            "",
        ).rstrip("/")

        if not base_url:
            logger.error(
                "Boas-vindas: EVOLUTION_API_BASE_URL não configurada."
            )
            return False

        api_key = (
            getattr(instance, "api_key", "")
            or getattr(
                settings,
                "EVOLUTION_GLOBAL_API_KEY",
                "",
            )
        )

        if not api_key:
            logger.error(
                "Boas-vindas: chave da Evolution API ausente."
            )
            return False

        url = (
            f"{base_url}/message/sendText/"
            f"{instance.instance_name}"
        )

        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "number": numero,
            "text": mensagem,
        }

        logger.info(
            "📤 Boas-vindas para %s via %s.",
            cliente.nome,
            instance.instance_name,
        )

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        logger.info(
            "📥 Boas-vindas HTTP %s: %s",
            response.status_code,
            response.text[:500],
        )

        if response.status_code in (200, 201):
            logger.info(
                "✅ Boas-vindas enviada para %s.",
                cliente.nome,
            )
            return True

        logger.error(
            "❌ Falha nas boas-vindas para %s: HTTP %s - %s",
            cliente.nome,
            response.status_code,
            response.text[:500],
        )
        return False

    except requests.exceptions.Timeout:
        logger.exception(
            "Timeout ao enviar boas-vindas para %s.",
            getattr(cliente, "nome", "cliente"),
        )
        return False

    except requests.exceptions.RequestException as erro:
        logger.exception(
            "Erro de conexão nas boas-vindas: %s",
            erro,
        )
        return False

    except Exception as erro:
        logger.exception(
            "Erro inesperado nas boas-vindas: %s",
            erro,
        )
        return False

# ============================================================
# FUNÇÃO ÚNICA DE CONFIRMAÇÃO DE PAGAMENTO
# ============================================================
def enviar_mensagem_confirmacao_pagamento(
    cliente,
    user=None,
):
    """
    Envia confirmação de pagamento ou renovação usando
    o motor centralizado de variáveis.
    """

    try:
        if not cliente:
            logger.error(
                "Confirmação de pagamento: cliente não informado."
            )
            return False

        dono = getattr(cliente, "dono", None)

        if not dono:
            logger.warning(
                "Confirmação: cliente %s não possui dono.",
                getattr(cliente, "id", "sem ID"),
            )
            return False

        config = ConfiguracaoMensagem.objects.filter(
            usuario=dono
        ).first()

        if not config:
            logger.info(
                "Confirmação: configuração não encontrada para %s.",
                dono.username,
            )
            return False

        template = (
            getattr(
                config,
                "mensagem_confirmacao_pagamento",
                "",
            )
            or ""
        ).strip()

        if not template:
            logger.info(
                "Confirmação: mensagem não configurada para %s.",
                dono.username,
            )
            return False

        if not cliente.whatsapp:
            logger.warning(
                "Confirmação: cliente %s sem WhatsApp.",
                cliente.nome,
            )
            return False

        usuario_instancia = user or dono

        instance = UserInstance.objects.filter(
            user=usuario_instancia,
            status="connected",
            is_active=True,
        ).first()

        if not instance:
            logger.warning(
                "Confirmação: usuário %s sem instância conectada.",
                usuario_instancia.username,
            )
            return False

        mensagem = substituir_variaveis_mensagem(
            template,
            cliente,
        )

        if not mensagem:
            logger.error(
                "Confirmação: mensagem vazia para %s.",
                cliente.nome,
            )
            return False

        numero = re.sub(
            r"\D",
            "",
            str(cliente.whatsapp),
        )

        if not numero:
            logger.error(
                "Confirmação: número inválido para %s.",
                cliente.nome,
            )
            return False

        if len(numero) in (10, 11):
            numero = f"55{numero}"

        if numero.startswith("5555"):
            numero = numero[2:]

        base_url = getattr(
            settings,
            "EVOLUTION_API_BASE_URL",
            "",
        ).rstrip("/")

        if not base_url:
            logger.error(
                "Confirmação: EVOLUTION_API_BASE_URL não configurada."
            )
            return False

        api_key = (
            getattr(instance, "api_key", "")
            or getattr(
                settings,
                "EVOLUTION_GLOBAL_API_KEY",
                "",
            )
        )

        if not api_key:
            logger.error(
                "Confirmação: chave da Evolution API ausente."
            )
            return False

        url = (
            f"{base_url}/message/sendText/"
            f"{instance.instance_name}"
        )

        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "number": numero,
            "text": mensagem,
        }

        logger.info(
            "📤 Confirmação para %s via %s.",
            cliente.nome,
            instance.instance_name,
        )

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        logger.info(
            "📥 Confirmação HTTP %s: %s",
            response.status_code,
            response.text[:500],
        )

        if response.status_code in (200, 201):
            logger.info(
                "✅ Confirmação enviada para %s.",
                cliente.nome,
            )
            return True

        logger.error(
            "❌ Falha na confirmação para %s: HTTP %s - %s",
            cliente.nome,
            response.status_code,
            response.text[:500],
        )
        return False

    except requests.exceptions.Timeout:
        logger.exception(
            "Timeout na confirmação para %s.",
            getattr(cliente, "nome", "cliente"),
        )
        return False

    except requests.exceptions.RequestException as erro:
        logger.exception(
            "Erro de conexão na confirmação: %s",
            erro,
        )
        return False

    except Exception as erro:
        logger.exception(
            "Erro inesperado na confirmação: %s",
            erro,
        )
        return False

    

        

######################################### CHAT ENTRE O ADMIN E USUARIO ######################################################################
@login_required
def configuracao_view(request):
    # Cada usuário tem sua própria configuração
    config, _ = Configuracao.objects.get_or_create(usuario=request.user)
    
    form = ConfiguracaoForm(request.POST or None, instance=config, is_admin=request.user.is_superuser)

    saved = False
    if request.method == 'POST' and form.is_valid():
        # Atualiza senha se necessário
        senha_nova = form.cleaned_data.get('senha')
        if senha_nova and senha_nova != request.user.senha_leitura:
            request.user.set_password(senha_nova)
            request.user.senha_leitura = senha_nova
            request.user.save()

        form.save()
        saved = True
        messages.success(request, "Configurações salvas com sucesso!")

    return render(request, 'configuracao/configuracao.html', {'form': form, 'saved': saved})


###################################### ATUALIZAÇÃO DO SISTEMA ###########################################################
####################################### LEMBRA QUE TEM QUE MUDAR O HTML TBM ######################################

@login_required
def atualizacoes(request):
    atualizacoes = Atualizacao.objects.order_by('-data_criacao')
    return render(request, 'configuracao/atualizacoes.html', {'atualizacoes': atualizacoes})

@login_required
@user_passes_test(lambda u: u.is_staff)
def nova_atualizacao(request):
    if request.method == 'POST':
        form = AtualizacaoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('atualizacoes')
    else:
        form = AtualizacaoForm()
    return render(request, 'configuracao/nova_atualizacao.html', {'form': form})


def register(request):
    if request.method == "POST":
        nome = (request.POST.get('fullname') or '').strip()
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        whatsapp = (request.POST.get('whatsapp') or '').strip()
        password = request.POST.get('password') or ''

        whatsapp_digits = re.sub(r'\D', '', whatsapp)
        verified_number = request.session.get('registration_whatsapp_number', '')
        verified_at = request.session.get('registration_whatsapp_verified_at')
        verificacao_valida = False
        try:
            verificacao_valida = (
                bool(verified_at)
                and verified_number == whatsapp_digits
                and timezone.now().timestamp() - float(verified_at) <= 600
            )
        except (TypeError, ValueError):
            verificacao_valida = False

        if not verificacao_valida:
            messages.error(request, "Verifique seu WhatsApp novamente antes de criar a conta.")
            return redirect('login')

        if not all([nome, username, email, whatsapp_digits, password]):
            messages.error(request, "Preencha todos os campos.")
            return redirect('login')

        if len(password) < 6:
            messages.error(request, "A senha deve ter no mínimo 6 caracteres.")
            return redirect('login')

        # Verificar se o usuário já existe
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Usuário já existe.")
            return redirect('login')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "E-mail já cadastrado.")
            return redirect('login')

        if CustomUser.objects.filter(whatsapp=whatsapp).exists():
            messages.error(request, "Número de WhatsApp já cadastrado.")
            return redirect('login')

        # Definir validade de 3 dias
        data_vencimento = timezone.now().date() + timedelta(days=3)

        # Buscar plano "NOVO" se existir, senão manter como None
        plano = Servico.objects.filter(nome="NOVO").first()

        # Buscar tag "teste" se existir
        tag_teste = Tag.objects.filter(nome="novo").first()

        # Buscar o admin como dono
        
        
        admin_user = CustomUser.objects.filter(tipo_usuario='admin', username="tiago").first()



        if not admin_user:
            messages.error(request, "Nenhum administrador encontrado. Contate o suporte.")
            return redirect('login')

        # Criar usuário
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            nome=nome,
            tipo_usuario="revenda",
            data_vencimento=data_vencimento,
            plano=plano,
            valor_a_pagar=plano.valor if plano else 0,
            valor_servico=plano.custos if plano else 0,
            whatsapp=whatsapp,
            dono=admin_user  # O dono será sempre o admin!
        )

        # Adicionar a tag "teste" se existir
        if tag_teste:
            user.tags.add(tag_teste)

        user.save()

        request.session.pop('registration_whatsapp_number', None)
        request.session.pop('registration_whatsapp_verified_at', None)
        request.session.modified = True

        messages.success(request, "Cadastro realizado com sucesso! Faça login.")
        return redirect('login')

    return redirect('login')


#########################################################################################




def is_admin(user):
    return user.is_staff

def lista_tutoriais(request):
    tutoriais = Tutorial.objects.all().order_by('ordem')
    dados = []
    for t in tutoriais:
        dados.append({
            'tutorial': t,
            'video_id': t.get_video_id(),
        })
    return render(request, 'tutoriais.html', {'tutoriais': dados})

@login_required
@user_passes_test(is_admin, login_url='/admin/login/')
def novo_tutorial(request):
    if request.method == 'POST':
        form = TutorialForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tutorial adicionado com sucesso!')
            return redirect('lista_tutoriais')
    else:
        form = TutorialForm()
    return render(request, 'form_tutorial.html', {'form': form, 'editando': False})

@login_required
@user_passes_test(is_admin, login_url='/admin/login/')
def editar_tutorial(request, tutorial_id):
    tutorial = get_object_or_404(Tutorial, pk=tutorial_id)
    if request.method == 'POST':
        form = TutorialForm(request.POST, instance=tutorial)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tutorial atualizado com sucesso!')
            return redirect('lista_tutoriais')
    else:
        form = TutorialForm(instance=tutorial)
    return render(request, 'form_tutorial.html', {'form': form, 'editando': True})

@login_required
@user_passes_test(is_admin, login_url='/admin/login/')
@require_POST
def excluir_tutorial(request, tutorial_id):
    tutorial = get_object_or_404(Tutorial, pk=tutorial_id)
    titulo = tutorial.titulo
    tutorial.delete()
    messages.success(request, f'Tutorial "{titulo}" excluído!')
    return redirect('lista_tutoriais')
















def gerar_id_jogo(jogo):
    """
    Gera um ID estável usando os dados principais da partida.
    """

    dados = "|".join([
        str(jogo.get("data", "")),
        str(jogo.get("hora", "")),
        str(jogo.get("mandante", "")),
        str(jogo.get("visitante", "")),
        str(jogo.get("campeonato", "")),
    ])

    return hashlib.md5(
        dados.encode("utf-8")
    ).hexdigest()



def jogos_do_dia(request, link_uuid):
    cliente = get_object_or_404(
        CustomUser,
        link_acesso=link_uuid
    )

    jogos = buscar_jogos_do_dia()

    for jogo in jogos:
        jogo["id"] = gerar_id_jogo(jogo)

    context = {
        "cliente": cliente,
        "jogos": jogos,
        "total_jogos": len(jogos),
        "jogos_com_canais": len([
            jogo
            for jogo in jogos
            if jogo.get("tem_canais")
        ]),
        "data_atual": datetime.now().strftime(
            "%d/%m/%Y"
        ),
        "hora_atual": datetime.now().strftime(
            "%H:%M:%S"
        ),
    }

    return render(
        request,
        "clientes/jogos_do_dia.html",
        context
    )




def favoritar_jogo(request):
    if request.method == "POST":
        cliente_id = request.POST.get("cliente_id")
        jogo_id = request.POST.get("jogo_id")

        cliente = CustomUser.objects.get(id=cliente_id)

        JogoFavorito.objects.create(
            cliente=cliente,
            jogo_id=jogo_id
        )

        return JsonResponse({"status": "ok"})

@login_required
@require_POST
def gerar_novo_link(request, cliente_id):
    """Gera um novo link apenas para clientes administrados pelo usuário atual."""
    clientes = CustomUser.objects.all()
    if not request.user.is_superuser:
        clientes = clientes.filter(dono=request.user)
    cliente = get_object_or_404(clientes, id=cliente_id)
    cliente.link_acesso = uuid.uuid4()
    cliente.save()
    
    return JsonResponse({
        'status': 'success',
        'message': 'Link gerado com sucesso!',
        'novo_link': f"{request.scheme}://{request.get_host()}/jogos/{cliente.link_acesso}/"
    })
    
    

############################### dash relatorio financeiro ###################################################
#########################################################################################
#########################################################################################






# ==========================================
# VIEWS PARA LOGS DE ATIVIDADE
# ==========================================

@login_required
def logs_atividade(request):
    """
    View para visualizar logs de atividade do sistema
    """
    # Verifica permissão (apenas admin e revenda podem ver logs)
    if request.user.tipo_usuario not in ['admin', 'revenda']:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('dashboard')
    
    # Filtros
    filtro_usuario = request.GET.get('usuario', '')
    filtro_tipo = request.GET.get('tipo', '')
    filtro_status = request.GET.get('status', '')
    filtro_data_inicio = request.GET.get('data_inicio', '')
    filtro_data_fim = request.GET.get('data_fim', '')
    filtro_pesquisa = request.GET.get('pesquisa', '')
    
    # Base query
    logs = LogAtividade.objects.all()
    
    # Aplica filtros
    if filtro_usuario:
        logs = logs.filter(usuario__username__icontains=filtro_usuario)
    
    if filtro_tipo:
        logs = logs.filter(tipo_acao=filtro_tipo)
    
    if filtro_status:
        logs = logs.filter(status=filtro_status)
    
    if filtro_data_inicio:
        try:
            data_inicio = timezone.make_aware(datetime.strptime(filtro_data_inicio, '%Y-%m-%d'))
            logs = logs.filter(data_hora__gte=data_inicio)
        except:
            pass
    
    if filtro_data_fim:
        try:
            data_fim = timezone.make_aware(datetime.strptime(filtro_data_fim, '%Y-%m-%d'))
            data_fim = data_fim + timedelta(days=1)  # Inclui todo o dia
            logs = logs.filter(data_hora__lte=data_fim)
        except:
            pass
    
    if filtro_pesquisa:
        logs = logs.filter(
            Q(descricao__icontains=filtro_pesquisa) |
            Q(modelo_afetado__icontains=filtro_pesquisa) |
            Q(objeto_id__icontains=filtro_pesquisa) |
            Q(url_acessada__icontains=filtro_pesquisa)
        )
    
    # Ordenação
    ordenacao = request.GET.get('ordenacao', '-data_hora')
    logs = logs.order_by(ordenacao)
    
    # Paginação
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estatísticas
    hoje = timezone.now().date()
    ontem = hoje - timedelta(days=1)
    
    total_logs = logs.count()
    logs_hoje = logs.filter(data_hora__date=hoje).count()
    logs_ontem = logs.filter(data_hora__date=ontem).count()
    
    # Tipos de ação para filtro
    tipos_acao = LogAtividade.TIPO_ACAO_CHOICES
    
    context = {
        'page_obj': page_obj,
        'total_logs': total_logs,
        'logs_hoje': logs_hoje,
        'logs_ontem': logs_ontem,
        'filtro_usuario': filtro_usuario,
        'filtro_tipo': filtro_tipo,
        'filtro_status': filtro_status,
        'filtro_data_inicio': filtro_data_inicio,
        'filtro_data_fim': filtro_data_fim,
        'filtro_pesquisa': filtro_pesquisa,
        'ordenacao': ordenacao,
        'tipos_acao': tipos_acao,
        'usuarios': CustomUser.objects.filter(
            logs_atividade__isnull=False
        ).distinct().order_by('username')[:20],
    }
    
    return render(request, 'logs/logs_atividade.html', context)

@login_required
def log_detalhe(request, log_id):
    """
    View para visualizar detalhes de um log específico
    """
    log = get_object_or_404(LogAtividade, id=log_id)
    
    # Verifica permissão
    if request.user.tipo_usuario not in ['admin', 'revenda']:
        messages.error(request, "Você não tem permissão para visualizar este log.")
        return redirect('dashboard')
    
    context = {
        'log': log,
    }
    
    return render(request, 'logs/log_detalhe.html', context)

@login_required
@require_POST
def limpar_logs(request):
    """
    Limpa logs antigos (apenas admin)
    """
    if not request.user.tipo_usuario == 'admin':
        return JsonResponse({'success': False, 'error': 'Permissão negada'})
    
    try:
        dias = int(request.POST.get('dias', 30))
        data_limite = timezone.now() - timedelta(days=dias)
        
        logs_excluidos, _ = LogAtividade.objects.filter(
            data_hora__lt=data_limite
        ).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{logs_excluidos} logs antigos foram excluídos.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
    


def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def log_delete(request, log_id):
    if request.method == 'DELETE':
        try:
            log = LogAtividade.objects.get(id=log_id)
            log.delete()
            return JsonResponse({'success': True, 'message': 'Log excluído com sucesso'})
        except LogAtividade.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Log não encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)




@login_required
def criar_tag_ajax(request):
    """Cria uma nova tag - FICA DISPONÍVEL PARA TODOS OS CLIENTES"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nome = data.get('nome', '').strip()
            cor = data.get('cor', '#667eea')
            
            if not nome:
                return JsonResponse({'status': 'error', 'message': 'Nome da tag é obrigatório'}, status=400)
            
            # Verifica se já existe (globalmente)
            tag_existente = Tag.objects.filter(nome__iexact=nome).first()
            
            if tag_existente:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Tag já existente',
                    'tag': {
                        'id': tag_existente.id,
                        'nome': tag_existente.nome,
                        'cor': tag_existente.cor
                    }
                })
            
            # Cria nova tag (disponível para todos)
            tag = Tag.objects.create(
                nome=nome,
                cor=cor,
                usuario=request.user  # Quem criou (para controle)
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Tag criada com sucesso!',
                'tag': {
                    'id': tag.id,
                    'nome': tag.nome,
                    'cor': tag.cor
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)





@login_required
def adicionar_tag_cliente(request, cliente_id):
    """
    ADICIONA tags ao cliente
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tag_ids = data.get('tag_ids', [])
            

            
            cliente = get_object_or_404(CustomUser, id=cliente_id, dono=request.user)
            
            # Converte para inteiros
            tag_ids_int = [int(tid) for tid in tag_ids if tid]
            
            if tag_ids_int:
                # Busca as tags
                tags = Tag.objects.filter(id__in=tag_ids_int)
                
                # 🔄 USA .set() PARA SINCRONIZAR (substitui todas)
                cliente.tags.set(tags)
                
                # 🔴 LIMPA O CACHE DO CLIENTE
                cache_key = f'cliente_tags_{cliente.id}'
                cache.delete(cache_key)
                

            else:
                # Se veio array vazio, remove todas as tags
                cliente.tags.clear()
                
                # 🔴 LIMPA O CACHE DO CLIENTE
                cache_key = f'cliente_tags_{cliente.id}'
                cache.delete(cache_key)
                

            
            # Busca as tags atuais para confirmar
            tags_atuais = list(cliente.tags.values_list('nome', flat=True))

            
            return JsonResponse({
                'status': 'success',
                'message': 'Tags atualizadas com sucesso!',
                'tags_atuais': tags_atuais
            })
            
        except Exception as e:

            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)



@login_required
def buscar_clientes_para_indicacao(request):
    """API para buscar clientes - APENAS DO USUÁRIO LOGADO"""
    try:
        termo = request.GET.get('q', '').strip()
        excluir_id = request.GET.get('excluir_id', '')
        
        hoje = timezone.localdate()
        
        # 🔒 TODOS VEEM APENAS SEUS PRÓPRIOS CLIENTES
        clientes = CustomUser.objects.filter(
            tipo_usuario='cliente',
            dono=request.user  # ← FILTRA PELO USUÁRIO LOGADO
        )
        


        
        if termo:
            clientes = clientes.filter(
                Q(nome__icontains=termo) |
                Q(username__icontains=termo) |
                Q(whatsapp__icontains=termo)
            )
        
        if excluir_id and excluir_id.isdigit():
            clientes = clientes.exclude(id=int(excluir_id))
        
        clientes = clientes.order_by('nome')[:20]
        

        
        resultados = []
        for cliente in clientes:
            nome_exibicao = cliente.nome or cliente.username
            
            status_vencimento = ''
            status_cor = 'success'
            
            if not cliente.is_active:
                status_vencimento = 'Desativado'
                status_cor = 'secondary'
            elif cliente.data_vencimento:
                dias = (cliente.data_vencimento - hoje).days
                if dias < 0:
                    status_vencimento = 'Vencido'
                    status_cor = 'danger'
                elif dias == 0:
                    status_vencimento = 'Vence Hoje'
                    status_cor = 'warning'
                elif dias <= 3:
                    status_vencimento = 'Vence em Breve'
                    status_cor = 'info'
                else:
                    status_vencimento = 'Em Dia'
                    status_cor = 'success'
            
            ja_indicado = Indicacao.objects.filter(cliente_indicado=cliente).exists()
            
            resultados.append({
                'id': cliente.id,
                'text': nome_exibicao + (' 🔒' if ja_indicado else ''),
                'inicial': nome_exibicao[0].upper() if nome_exibicao else '?',
                'whatsapp': cliente.whatsapp or '',
                'status_vencimento': status_vencimento,
                'status_cor': status_cor,
                'is_active': cliente.is_active,
                'ja_indicado': ja_indicado,
            })
        
        return JsonResponse({'results': resultados})
        
    except Exception as e:

        return JsonResponse({'results': [], 'error': str(e)})
    


@login_required
def buscar_tags_para_cliente(request):
    """Retorna tags disponíveis - apenas do usuário logado"""
    try:
        termo = request.GET.get('q', '').strip()
        
        # 🔒 Apenas tags do usuário logado
        tags = Tag.objects.filter(usuario=request.user)
        
        if termo:
            tags = tags.filter(nome__icontains=termo)
        
        tags = tags.order_by('nome')[:50]
        
        resultados = []
        for tag in tags:
            resultados.append({
                'id': tag.id,
                'text': tag.nome,
                'cor': tag.cor or '#6c757d'
            })
        
        return JsonResponse({'results': resultados})
        
    except Exception as e:
        return JsonResponse({'results': [], 'error': str(e)})






@login_required
def listar_indicacoes(request, cliente_id):
    """API para listar indicações de um cliente"""
    try:
        cliente = get_object_or_404(CustomUser, id=cliente_id)
        
        # Verificar permissão
        if cliente.dono != request.user and request.user.tipo_usuario != 'admin':
            return JsonResponse({'status': 'error', 'message': 'Permissão negada'}, status=403)
        
        # Indicações feitas
        indicacoes_feitas = Indicacao.objects.filter(
            cliente_indicador=cliente
        ).select_related('cliente_indicado')
        
        # Indicações recebidas
        indicacoes_recebidas = Indicacao.objects.filter(
            cliente_indicado=cliente
        ).select_related('cliente_indicador')
        
        feitas_data = [{
            'id': ind.id,
            'cliente_indicado_id': ind.cliente_indicado.id,
            'cliente_indicado_nome': ind.cliente_indicado.nome or ind.cliente_indicado.username,
            'cliente_indicado_whatsapp': ind.cliente_indicado.whatsapp,
            'data_indicacao': ind.data_indicacao.strftime('%d/%m/%Y'),
            'observacao': ind.observacao or ''
        } for ind in indicacoes_feitas]
        
        recebidas_data = [{
            'id': ind.id,
            'cliente_indicador_id': ind.cliente_indicador.id,
            'cliente_indicador_nome': ind.cliente_indicador.nome or ind.cliente_indicador.username,
            'cliente_indicador_whatsapp': ind.cliente_indicador.whatsapp,
            'data_indicacao': ind.data_indicacao.strftime('%d/%m/%Y'),
            'observacao': ind.observacao or ''
        } for ind in indicacoes_recebidas]
        
        return JsonResponse({
            'status': 'success',
            'indicacoes_feitas': feitas_data,
            'indicacoes_recebidas': recebidas_data
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    

@login_required
def buscar_tags_do_cliente(request, cliente_id):
    """Busca as tags atuais de um cliente - SEM CACHE"""
    try:
        # 🔒 Garante que o cliente pertence ao usuário logado
        cliente = get_object_or_404(CustomUser, id=cliente_id, dono=request.user)
        
        # 🔴 BUSCA DIRETO DO BANCO, SEM CACHE
        tag_ids = list(cliente.tags.values_list('id', flat=True))
        

        
        return JsonResponse({
            'status': 'success',
            'tag_ids': tag_ids
        })
    except Exception as e:

        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def remover_indicacao(request, indicacao_id):
    """Remove uma indicação"""
    if request.method == 'POST':
        try:
            indicacao = get_object_or_404(Indicacao, id=indicacao_id)
            
            # Verificar permissão (só quem fez a indicação ou admin pode remover)
            if indicacao.cliente_indicador.dono != request.user and request.user.tipo_usuario != 'admin':
                return JsonResponse({'status': 'error', 'message': 'Sem permissão'}, status=403)
            
            indicacao.delete()
            return JsonResponse({'status': 'success', 'message': 'Indicação removida'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)



@login_required
def listar_indicacoes_cliente(request, cliente_id):
    """API para listar indicações de um cliente"""
    try:
        cliente = get_object_or_404(CustomUser, id=cliente_id)
        
        # Verifica permissão
        if cliente.dono != request.user and request.user.tipo_usuario != 'admin':
            return JsonResponse({'status': 'error', 'message': 'Sem permissão'}, status=403)
        
        # Indicações feitas
        indicacoes_feitas = Indicacao.objects.filter(
            cliente_indicador=cliente
        ).select_related('cliente_indicado')
        
        feitas_data = [{
            'id': ind.id,
            'cliente_indicado_id': ind.cliente_indicado.id,
            'cliente_indicado_nome': ind.cliente_indicado.nome or ind.cliente_indicado.username,
        } for ind in indicacoes_feitas]
        
        return JsonResponse({
            'status': 'success',
            'indicacoes_feitas': feitas_data
        })
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def api_configuracao_comissao(request):
    """API para get/set configuração de comissão POR CLIENTE"""
    if request.method == 'GET':
        cliente_id = request.GET.get('cliente_id')
        
        if not cliente_id:
            return JsonResponse({'status': 'error', 'message': 'Cliente não informado'}, status=400)
        
        config = ConfiguracaoIndicacao.objects.filter(
            cliente_id=cliente_id, ativo=True
        ).first()
        
        if config:
            return JsonResponse({
                'status': 'success',
                'config': {
                    'id': config.id,
                    'tipo_comissao': config.tipo_comissao,
                    'valor_por_indicacao': str(config.valor_por_indicacao),
                    'valor_por_renovacao': str(config.valor_por_renovacao),
                    'ativar_meta': config.ativar_meta,
                    'quantidade_meta': config.quantidade_meta,
                    'bonus_meta': str(config.bonus_meta),
                    'validade_meses': config.validade_meses,
                }
            })
        return JsonResponse({'status': 'success', 'config': None})
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            cliente_id = data.get('cliente_id')
            
            if not cliente_id:
                return JsonResponse({'status': 'error', 'message': 'Cliente não informado'}, status=400)
            
            cliente = get_object_or_404(CustomUser, id=cliente_id, dono=request.user)
            
            config, created = ConfiguracaoIndicacao.objects.update_or_create(
                cliente=cliente,
                ativo=True,
                defaults={
                    'tipo_comissao': data.get('tipo_comissao', 'indicacao'),
                    'valor_por_indicacao': Decimal(str(data.get('valor_por_indicacao', 0))),
                    'valor_por_renovacao': Decimal(str(data.get('valor_por_renovacao', 0))),
                    'ativar_meta': data.get('ativar_meta', False),
                    'quantidade_meta': int(data.get('quantidade_meta', 3)),
                    'bonus_meta': Decimal(str(data.get('bonus_meta', 0))),
                    'validade_meses': int(data.get('validade_meses', 1)),
                }
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Configuração salva!',
                'created': created
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)



# clientes/views.py

@login_required
def api_pesquisar_clientes(request):
    """
    API para pesquisa AJAX - retorna HTML da tabela COMPLETA
    """
    termo = request.GET.get('termo', '').strip()
    status = request.GET.get('status', 'active')
    plano = request.GET.get('plano', '')
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 100))
    
    # 🔴 CARREGA TODOS OS DADOS RELACIONADOS
    clientes = CustomUser.objects.filter(dono=request.user).select_related(
        'plano'
    ).prefetch_related(
        'tags',
        'indicacoes_feitas',
        'indicacoes_feitas__cliente_indicado',
        'relatoriofinanceiro_set',  # ← Carrega relatórios financeiros
    )
    
    if status == 'active':
        clientes = clientes.filter(is_active=True)
    elif status == 'inactive':
        clientes = clientes.filter(is_active=False)
    
    if plano:
        clientes = clientes.filter(plano__nome=plano)
    
    if termo:
        from django.db.models import Q
        clientes = clientes.filter(
            Q(nome__icontains=termo) |
            Q(username__icontains=termo) |
            Q(whatsapp__icontains=termo) |
            Q(email__icontains=termo) |
            Q(login_externo__icontains=termo) |
            Q(senha_leitura__icontains=termo)
        )
    
    #clientes = clientes.order_by('nome')
    clientes = clientes.order_by(F('data_vencimento').asc(nulls_last=True), 'nome')
    
    # Status de vencimento
    from django.utils import timezone
    hoje = timezone.now().date()
    
    # Paginação
    from django.core.paginator import Paginator
    paginator = Paginator(clientes, page_size)
    clientes_page = paginator.get_page(page)
    
    # 🔴 Calcula status E carrega relatórios para cada cliente
    for cliente in clientes_page:
        # Status de vencimento
        if cliente.data_vencimento:
            dias = (cliente.data_vencimento - hoje).days
            if dias < 0:
                cliente.status_vencimento = 'Vencido'
            elif dias == 0:
                cliente.status_vencimento = 'Vence Hoje'
            elif dias <= 3:
                cliente.status_vencimento = 'Vence em Breve'
            else:
                cliente.status_vencimento = 'Em Dia'
        else:
            cliente.status_vencimento = 'Em Dia'
        
        # 🔴 Carrega relatórios financeiros (últimos 10)
        cliente.relatorios_carregados = cliente.relatoriofinanceiro_set.all().order_by('-data_geracao')[:10]
        
        # 🔴 Calcula valor total a pagar
        # 🔴 Calcula valor total a pagar + custo real FIFO
        from decimal import Decimal
        valor_a_pagar = cliente.valor_a_pagar or Decimal('0.00')
        saldo = cliente.saldo or Decimal('0.00')
        
        # 🔴 Busca custo FIFO
        if cliente.plano and cliente.plano.controlar_estoque and cliente.plano.tipo_estoque in ['creditos', 'ambos']:
            lote_fifo = LoteEstoque.objects.filter(
                servico=cliente.plano,
                quantidade_restante__gt=0
            ).order_by('ordem').first()
            if lote_fifo:
                cliente.custo_real = lote_fifo.custo_unitario
            elif cliente.plano.custos and cliente.plano.custos > 0:
                cliente.custo_real = cliente.plano.custos
            else:
                cliente.custo_real = cliente.valor_servico or Decimal('0.00')
        else:
            cliente.custo_real = cliente.valor_servico or Decimal('0.00')
        
        cliente.valor_servico_exibicao = cliente.custo_real
        
        if saldo < 0:
            cliente.valor_total_a_pagar = valor_a_pagar + abs(saldo)
        else:
            cliente.valor_total_a_pagar = max(Decimal('0.00'), valor_a_pagar - saldo)
    
    # Renderiza template parcial
    html_tabela = render_to_string('clientes/includes/tabela_clientes.html', {
        'clientes': clientes_page,
        'request': request,
    }, request=request)
    
    # HTML da paginação
    html_paginacao = ''
    start = clientes_page.start_index()
    end = clientes_page.end_index()
    total = clientes.count()
    
    if clientes_page.paginator.num_pages > 1:
        html_paginacao = render_to_string('clientes/includes/paginacao_clientes.html', {
            'clientes': clientes_page,
            'mostrando': f'{start} - {end} de {total}',
        }, request=request)
    
    return JsonResponse({
        'success': True,
        'html_tabela': html_tabela,
        'html_paginacao': html_paginacao,
        'total': total,
        'mostrando': f'{start} - {end} de {total}',
    })



# clientes/views.py
@login_required
def configurar_integracao_servico(request, servico_id):
    """Configuração da integração externa do servidor, separada do abastecimento de créditos."""
    servico = get_object_or_404(Servico, pk=servico_id, revenda=request.user)

    if request.method == 'POST':
        tipo = (request.POST.get('integracao_tipo') or 'nenhuma').strip().lower()
        if tipo not in {'nenhuma', 'sigman', 'unitv'}:
            tipo = 'nenhuma'

        servico.integracao_tipo = tipo
        servico.integracao_ativa = (request.POST.get('integracao_ativa') == 'on') and tipo != 'nenhuma'
        servico.integracao_politica = request.POST.get('integracao_politica') or 'manual'
        servico.renovacao_manual_credito = request.POST.get('renovacao_manual_credito') or 'sempre'

        cfg = dict(servico.integracao_config or {})

        # URL/token mudam de nome na UI da UniTV apenas para evitar campos duplicados visuais.
        if tipo == 'unitv':
            url = (request.POST.get('unitv_url') or request.POST.get('integracao_url') or '').strip()
            token = (request.POST.get('unitv_token') or request.POST.get('integracao_token') or '').strip()
            servico.integracao_usuario = (request.POST.get('integracao_usuario') or '').strip() or None
            cfg['unitv_customer'] = (request.POST.get('unitv_customer') or cfg.get('unitv_customer') or 'UniTV').strip()
            # Não existe teste UniTV neste fluxo.
            servico.integracao_pacote_teste = None
        else:
            url = (request.POST.get('integracao_url') or '').strip()
            token = (request.POST.get('integracao_token') or '').strip()
            servico.integracao_usuario = None

        servico.integracao_url = url or None
        if token:
            servico.integracao_token = token

        if tipo == 'sigman':
            modo = (request.POST.get('sigman_modo') or 'direto').strip().lower()
            if modo not in {'direto', 'oficial'}:
                modo = 'direto'
            cfg['sigman_modo'] = modo
            # O usuário não precisa escolher header. No modo direto o adaptador tenta
            # automaticamente os formatos compatíveis; no oficial usa o contrato x-api-key/x-painel-token.
            cfg['sigman_token_header'] = 'auto'
            api_key = (request.POST.get('integracao_api_key') or '').strip()
            if modo == 'oficial':
                if api_key:
                    servico.integracao_api_key = api_key
            else:
                # Fundamental: ao voltar para modo direto, não deixar uma API Key antiga
                # forçar o adaptador para a API oficial.
                servico.integracao_api_key = None
        elif tipo != 'sigman':
            cfg.pop('sigman_modo', None)
            cfg.pop('sigman_token_header', None)
            servico.integracao_api_key = None

        servico.integracao_servidor_externo_id = (request.POST.get('integracao_servidor_externo_id') or '').strip() or None
        servico.integracao_pacote_1_mes = (request.POST.get('integracao_pacote_1_mes') or '').strip() or None
        if tipo == 'sigman':
            servico.integracao_pacote_teste = (request.POST.get('integracao_pacote_teste') or '').strip() or None

        try:
            servico.integracao_conexoes = max(1, int(request.POST.get('integracao_conexoes') or 1))
        except (TypeError, ValueError):
            servico.integracao_conexoes = 1

        servico.integracao_config = cfg
        servico.save(update_fields=[
            'integracao_ativa', 'integracao_tipo', 'integracao_politica', 'integracao_url',
            'integracao_token', 'integracao_api_key', 'integracao_usuario',
            'integracao_servidor_externo_id', 'integracao_pacote_1_mes', 'integracao_pacote_teste',
            'integracao_conexoes', 'renovacao_manual_credito', 'integracao_config', 'data_atualizacao'
        ])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Configuração salva.'})
        messages.success(request, 'Integração salva com sucesso.')
        return redirect('configurar_integracao_servico', servico_id=servico.id)

    operacoes_integracao = OperacaoIntegracaoPainel.objects.filter(
        revenda=request.user, servico=servico
    ).select_related('cliente', 'teste')[:20]

    return render(request, 'servicos/configurar_integracao.html', {
        'servico': servico,
    })


@login_required
def abastecer_estoque(request, servico_id):
    """Compra/abastece novo lote de créditos"""
    servico = get_object_or_404(Servico, pk=servico_id, revenda=request.user)
    
    if request.method == 'POST':
        try:
            quantidade = int(request.POST.get('quantidade', 0))
        except (ValueError, TypeError):
            quantidade = 0
        
        try:
            custo_unitario = Decimal(request.POST.get('custo_unitario', '0').replace(',', '.'))
        except:
            custo_unitario = Decimal('0')
        
        if quantidade <= 0 or custo_unitario <= 0:
            messages.error(request, "Quantidade e custo devem ser maiores que zero.")
            return redirect('abastecer_estoque', servico_id=servico.id)
        
        lote = LoteEstoque.objects.create(
            servico=servico,
            quantidade=quantidade,
            custo_unitario=custo_unitario,
            valor_total=quantidade * custo_unitario,
            quantidade_restante=quantidade,
            data_compra=timezone.now(),
            observacao=f"Compra em {timezone.now().strftime('%d/%m/%Y')}"
        )
        
        messages.success(request, f"✅ Lote de {quantidade} créditos adicionado! Custo unitário: R$ {custo_unitario:.2f}")
        return redirect('listar_servicos')
    
    # GET - Mostrar formulário com histórico
    lotes = servico.lotes.all().order_by('-data_compra')
    
    # 🔴 Buscar consumos (vendas) de cada lote
    for lote in lotes:
        lote.consumos_lista = lote.consumos.select_related('cliente').order_by('-data_venda')[:50]
    
    return render(request, 'servicos/abastecer_estoque.html', {
        'servico': servico,
        'lotes': lotes,
    })


@login_required
def get_custo_fifo(request, plano_id):
    """
    Retorna o custo do próximo crédito disponível (FIFO) + vagas + todos os lotes
    """
    try:
        plano = get_object_or_404(Servico, pk=plano_id, revenda=request.user)
        
        # Busca TODOS os lotes com quantidade disponível
        lotes_disponiveis = LoteEstoque.objects.filter(
            servico=plano,
            quantidade_restante__gt=0
        ).order_by('ordem')
        
        # Próximo lote FIFO
        lote_disponivel = lotes_disponiveis.first()
        
        # Calcula vagas CORRETAMENTE
        vagas_restantes = None
        vagas_total = None
        clientes_ativos = None

        if plano.controlar_estoque:
            # Total de créditos disponíveis nos lotes
            total_creditos = lotes_disponiveis.aggregate(
                total=Sum('quantidade_restante')
            )['total'] or 0
            
            # Vagas = créditos × multiplicador
            vagas_total = total_creditos * plano.multiplicador
            vagas_restantes = vagas_total  # Não subtrai clientes!
            
            # Só está esgotado se ZERO créditos
            if total_creditos == 0:
                vagas_restantes = 0
        
        # Monta resposta
        response_data = {
            'success': True,
            'custo_fifo': float(lote_disponivel.custo_unitario) if lote_disponivel else None,
            'custo_cadastrado': float(plano.custos) if plano.custos else None,
            'lote_ordem': lote_disponivel.ordem if lote_disponivel else None,
            'lote_id': lote_disponivel.id if lote_disponivel else None,
            'lote_data': lote_disponivel.data_compra.strftime('%d/%m/%Y') if lote_disponivel and hasattr(lote_disponivel, 'data_compra') and lote_disponivel.data_compra else None,
            'lote_restante': lote_disponivel.quantidade_restante if lote_disponivel else 0,
            'fonte': 'abastecimento' if lote_disponivel else ('cadastrado' if (plano.custos and plano.custos > 0) else 'nenhum'),
            
            # Informações do plano
            'controlar_estoque': plano.controlar_estoque,
            'usuario_unico': plano.usuario_unico,
            'multiplicador': plano.multiplicador,
            'estoque': plano.estoque,
            'vagas_restantes': vagas_restantes,
            'vagas_total': vagas_total,
            'clientes_ativos': clientes_ativos,
            
            # Todos os lotes disponíveis
            'lotes_disponiveis': [
                {
                    'id': lote.id,
                    'ordem': lote.ordem,
                    'data': lote.data_compra.strftime('%d/%m/%Y') if hasattr(lote, 'data_compra') and lote.data_compra else 'Sem data',
                    'custo': float(lote.custo_unitario),
                    'quantidade': lote.quantidade_restante,
                }
                for lote in lotes_disponiveis
            ]
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
@require_POST
def api_integracao_testar(request, servico_id):
    servico = get_object_or_404(Servico, pk=servico_id, revenda=request.user)
    try:
        adapter = get_painel_adapter(servico)
        info = adapter.testar_conexao()
        servico.integracao_status = 'ok'
        servico.integracao_erro = ''
        servico.integracao_ultima_verificacao = timezone.now()
        servico.save(update_fields=['integracao_status', 'integracao_erro', 'integracao_ultima_verificacao', 'data_atualizacao'])
        return JsonResponse({'success': True, 'message': 'Conexão realizada com sucesso.', 'info': info})
    except Exception as exc:
        servico.integracao_status = 'erro'
        servico.integracao_erro = str(exc)[:2000]
        servico.integracao_ultima_verificacao = timezone.now()
        servico.save(update_fields=['integracao_status', 'integracao_erro', 'integracao_ultima_verificacao', 'data_atualizacao'])
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@login_required
def api_integracao_catalogo(request, servico_id):
    servico = get_object_or_404(Servico, pk=servico_id, revenda=request.user)
    try:
        adapter = get_painel_adapter(servico)
        if not hasattr(adapter, 'catalogo'):
            raise IntegracaoPainelErro('Este painel não fornece catálogo automático.')
        return JsonResponse({'success': True, 'catalogo': adapter.catalogo()})
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=400)


@login_required
def testes_painel(request):
    """Cria e lista testes. Hoje a criação automática é habilitada para SIGMAN."""
    servicos = Servico.objects.filter(
        revenda=request.user,
        integracao_ativa=True,
        integracao_tipo='sigman',
    ).order_by('nome')

    if request.method == 'POST':
        nome = (request.POST.get('nome') or '').strip()
        whatsapp = (request.POST.get('whatsapp') or '').strip()
        servico_id = request.POST.get('servico_id')
        if not nome or not servico_id:
            messages.error(request, 'Informe nome e servidor.')
            return redirect('testes_painel')
        servico = get_object_or_404(servicos, pk=servico_id)
        try:
            adapter = get_painel_adapter(servico)
            conta = adapter.criar_teste(nome=nome, whatsapp=whatsapp)
            teste = TestePainel.objects.create(
                revenda=request.user,
                servico=servico,
                nome=nome,
                whatsapp=whatsapp,
                login_externo=conta.usuario,
                senha_leitura=conta.senha,
                external_id=conta.id,
                data_vencimento=conta.vencimento,
                status='ativo',
                dados_externos=conta.bruto or {},
            )
            OperacaoIntegracaoPainel.objects.create(
                revenda=request.user,
                servico=servico,
                teste=teste,
                tipo='teste',
                status='concluida',
                chave_idempotencia=f'teste:{request.user.id}:{teste.id}:{uuid.uuid4().hex}',
                login_externo=conta.usuario,
                external_id=conta.id,
                meses=1,
                creditos_externos=Decimal('0'),
                vencimento_novo=conta.vencimento,
                resposta_resumo={'usuario': conta.usuario, 'plano': conta.plano, 'servidor': conta.servidor},
                concluido_em=timezone.now(),
            )
            messages.success(request, f'Teste criado: usuário {conta.usuario}.')
            return redirect(f"{reverse('testes_painel')}?criado={teste.id}")
        except Exception as exc:
            messages.error(request, f'Não foi possível criar o teste: {exc}')
            return redirect('testes_painel')

    testes = TestePainel.objects.filter(revenda=request.user).select_related('servico', 'cliente_convertido')[:200]
    agora = timezone.now()
    for teste in testes:
        if teste.status == 'ativo' and teste.data_vencimento and teste.data_vencimento < agora:
            teste.status_visual = 'vencido'
        else:
            teste.status_visual = teste.status
    criado = None
    criado_id = request.GET.get('criado')
    if criado_id:
        criado = TestePainel.objects.filter(pk=criado_id, revenda=request.user).first()
    return render(request, 'clientes/testes_painel.html', {
        'servicos': servicos,
        'testes': testes,
        'criado': criado,
    })


@login_required
@require_POST
def converter_teste_painel(request, teste_id):
    teste = get_object_or_404(TestePainel, pk=teste_id, revenda=request.user)
    if teste.status == 'convertido':
        messages.info(request, 'Este teste já foi convertido em cliente.')
        return redirect('testes_painel')
    try:
        meses = int(request.POST.get('meses') or 1)
    except (TypeError, ValueError):
        meses = 1
    if meses not in (1, 2, 3, 6, 12):
        messages.error(request, 'Período inválido.')
        return redirect('testes_painel')

    servico = teste.servico
    try:
        adapter = get_painel_adapter(servico)
        preview = adapter.preview_renovacao(teste.login_externo, teste.senha_leitura, meses)
        if preview.creditos != preview.creditos.to_integral_value():
            raise IntegracaoPainelErro('O painel exige crédito fracionado e o estoque local usa créditos inteiros.')
        qtd = int(preview.creditos)
        if servico.controlar_estoque and servico.tipo_estoque in ['creditos', 'ambos'] and servico.creditos_disponiveis < qtd:
            raise IntegracaoPainelErro(f'Créditos insuficientes: precisa de {qtd}, disponível {servico.creditos_disponiveis}.')

        chave = f'converter-teste:{request.user.id}:{teste.id}'
        op, created = OperacaoIntegracaoPainel.objects.get_or_create(
            chave_idempotencia=chave,
            defaults={
                'revenda': request.user, 'servico': servico, 'teste': teste,
                'tipo': 'conversao_teste', 'status': 'consultando',
                'login_externo': teste.login_externo, 'external_id': preview.conta.id,
                'meses': meses, 'creditos_externos': preview.creditos,
                'vencimento_anterior': preview.conta.vencimento,
            },
        )
        if not created and op.status in ('concluida', 'aceita'):
            messages.info(request, 'A conversão já foi processada; nenhuma nova renovação foi enviada.')
            return redirect('testes_painel')
        if not created and op.status not in ('falhou',):
            messages.warning(request, 'Esta conversão já está em processamento/verificação.')
            return redirect('testes_painel')
        if not created:
            op.status = 'consultando'; op.erro = ''; op.save(update_fields=['status', 'erro', 'atualizado_em'])

        resultado = adapter.renovar(preview)
        venc_dt = resultado.vencimento_novo
        if not venc_dt:
            base_dt = preview.conta.vencimento or timezone.now()
            if base_dt < timezone.now():
                base_dt = timezone.now()
            venc_dt = base_dt + relativedelta(months=meses)
        nova_data = timezone.localtime(venc_dt).date()

        # Cria/atualiza o cliente local apenas depois do painel confirmar.
        cliente = CustomUser.objects.filter(
            dono=request.user,
            login_externo=teste.login_externo,
            senha_leitura=teste.senha_leitura,
        ).first()
        if not cliente:
            cliente = CustomUser.objects.create(
                dono=request.user,
                tipo_usuario='cliente',
                nome=teste.nome,
                login_externo=teste.login_externo,
                senha_leitura=teste.senha_leitura,
                whatsapp=teste.whatsapp,
                plano=servico,
                data_vencimento=nova_data,
                valor_a_pagar=servico.valor or Decimal('0.00'),
                is_active=True,
            )
        else:
            cliente.nome = teste.nome or cliente.nome
            cliente.whatsapp = teste.whatsapp or cliente.whatsapp
            cliente.plano = servico
            cliente.data_vencimento = nova_data
            cliente.is_active = True
            cliente.save(update_fields=['nome', 'whatsapp', 'plano', 'data_vencimento', 'is_active'])

        custo = Decimal('0.00')
        consumiu = False
        if qtd > 0:
            sucesso, msg, custo = CreditoService.consumir_credito_cliente(servico, cliente, qtd, is_renovacao=True)
            if not sucesso:
                op.status = 'verificar'
                op.erro = f'Painel renovou o teste, mas falhou baixa local: {msg}'
                op.vencimento_novo = venc_dt
                op.save(update_fields=['status', 'erro', 'vencimento_novo', 'atualizado_em'])
                messages.error(request, 'O painel ativou o teste, mas houve falha no crédito local. Operação marcada para verificação; não tente novamente.')
                return redirect('testes_painel')
            consumiu = bool(servico.controlar_estoque and servico.tipo_estoque in ['creditos', 'ambos'])

        valor_base = Decimal(cliente.valor_a_pagar or servico.valor or 0)
        saldo = Decimal(cliente.saldo or 0)
        valor_pago = valor_base + abs(saldo) if saldo < 0 else max(Decimal('0.00'), valor_base - saldo)
        cliente.saldo = Decimal('0.00')
        cliente.valor_servico = custo
        cliente.data_vencimento = nova_data
        cliente.save(update_fields=['saldo', 'valor_servico', 'data_vencimento'])
        gerar_relatorio_financeiro(
            cliente=cliente, valor_pago=valor_pago, valor_servico=custo,
            is_manual_entry=False, numero_renovacao=0, grupo_renovacao=get_grupo_renovacao(cliente)
        )

        teste.status = 'convertido'
        teste.cliente_convertido = cliente
        teste.convertido_em = timezone.now()
        teste.save(update_fields=['status', 'cliente_convertido', 'convertido_em'])

        op.status = 'aceita' if resultado.status_externo == 'aceita' else 'concluida'
        op.cliente = cliente
        op.creditos_locais = qtd if consumiu else 0
        op.custo_local = custo
        op.vencimento_novo = venc_dt
        op.resposta_resumo = {'mensagem': resultado.mensagem, 'usuario': teste.login_externo}
        op.concluido_em = timezone.now()
        op.save(update_fields=['status', 'cliente', 'creditos_locais', 'custo_local', 'vencimento_novo', 'resposta_resumo', 'concluido_em', 'atualizado_em'])
        messages.success(request, f'Teste de {teste.nome} convertido em cliente e renovado por {meses} mês(es).')
    except Exception as exc:
        messages.error(request, f'Falha ao converter o teste: {exc}')
    return redirect('testes_painel')


# ==========================================
# AVISOS DO SISTEMA
# ==========================================

@never_cache
@login_required
def configurar_avisos(request):
    if request.user.tipo_usuario != 'admin':
        return redirect('dashboard')
    
    avisos = AvisoSistema.objects.filter(usuario=request.user).order_by('ordem', '-data_criacao')
    config = Configuracao.objects.filter(usuario=request.user).first()
    
    return render(request, 'clientes/configurar_avisos.html', {
        'avisos': avisos,
        'config': config,
    })


@login_required
@require_POST
def salvar_aviso(request):
    """Cria ou atualiza um aviso"""
    try:
        aviso_id = request.POST.get('aviso_id')
        titulo = request.POST.get('titulo', '').strip()
        mensagem = request.POST.get('mensagem', '').strip()
        tipo = request.POST.get('tipo', 'info')
        icone = request.POST.get('icone', 'fa-bell')
        cor = request.POST.get('cor_destaque', '#667eea')
        ordem = int(request.POST.get('ordem', 0))
        ativo = request.POST.get('ativo') == 'on'
        
        mostrar_login = request.POST.get('mostrar_a_cada_login') == 'on'
        intervalo = request.POST.get('mostrar_intervalo_horas') or None
        antes_venc = request.POST.get('mostrar_antes_vencimento') or None
        no_venc = request.POST.get('mostrar_no_vencimento') == 'on'
        
        data_inicio = request.POST.get('data_inicio') or timezone.now()
        data_fim = request.POST.get('data_fim') or None
        
        if intervalo:
            intervalo = int(intervalo)
        if antes_venc:
            antes_venc = int(antes_venc)
        
        if aviso_id:
            aviso = get_object_or_404(AvisoSistema, id=aviso_id, usuario=request.user)
        else:
            aviso = AvisoSistema(usuario=request.user)
        
        aviso.titulo = titulo
        aviso.mensagem = mensagem
        aviso.tipo = tipo
        aviso.icone = icone
        aviso.cor_destaque = cor
        aviso.ordem = ordem
        aviso.ativo = ativo
        aviso.mostrar_a_cada_login = mostrar_login
        aviso.mostrar_intervalo_horas = intervalo
        aviso.mostrar_antes_vencimento = antes_venc
        aviso.mostrar_no_vencimento = no_venc
        aviso.data_inicio = data_inicio
        aviso.data_fim = data_fim if data_fim else None
        aviso.save()
        
        return JsonResponse({'success': True, 'message': 'Aviso salvo!', 'id': aviso.id})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def editar_aviso(request, aviso_id):
    """Retorna dados do aviso para edição"""
    aviso = get_object_or_404(AvisoSistema, id=aviso_id, usuario=request.user)
    return JsonResponse({
        'success': True,
        'aviso': {
            'id': aviso.id,
            'titulo': aviso.titulo,
            'mensagem': aviso.mensagem,
            'tipo': aviso.tipo,
            'icone': aviso.icone,
            'cor_destaque': aviso.cor_destaque,
            'ordem': aviso.ordem,
            'ativo': aviso.ativo,
            'mostrar_a_cada_login': aviso.mostrar_a_cada_login,
            'mostrar_intervalo_horas': aviso.mostrar_intervalo_horas,
            'mostrar_antes_vencimento': aviso.mostrar_antes_vencimento,
            'mostrar_no_vencimento': aviso.mostrar_no_vencimento,
            'data_inicio': aviso.data_inicio.strftime('%Y-%m-%dT%H:%M') if aviso.data_inicio else '',
            'data_fim': aviso.data_fim.strftime('%Y-%m-%dT%H:%M') if aviso.data_fim else '',
        }
    })


@login_required
@require_POST
def excluir_aviso(request, aviso_id):
    """Exclui um aviso"""
    aviso = get_object_or_404(AvisoSistema, id=aviso_id, usuario=request.user)
    aviso.delete()
    return JsonResponse({'success': True, 'message': 'Aviso excluído!'})


@login_required
@require_POST
def salvar_config_avisos(request):
    """Salva configuração global de avisos"""
    try:
        whatsapp = request.POST.get('whatsapp_suporte', '').strip()
        
        config, _ = Configuracao.objects.get_or_create(usuario=request.user)
        config.numero_celular = whatsapp  # Apenas WhatsApp
        config.save()
        
        return JsonResponse({'success': True, 'message': 'Configuração salva!'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
@require_POST
def reordenar_avisos(request):
    """Reordena avisos via drag-and-drop"""
    try:
        data = json.loads(request.body)
        ordem_ids = data.get('ordem_ids', [])
        for i, aviso_id in enumerate(ordem_ids):
            AvisoSistema.objects.filter(id=aviso_id, usuario=request.user).update(ordem=i + 1)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@login_required
def api_avisos_ativos(request):
    """API que retorna avisos GLOBAIS do admin para todas as revendas"""
    agora = timezone.now()
    
    admin_user = CustomUser.objects.filter(tipo_usuario='admin').first()
    
    if not admin_user:
        return JsonResponse({'success': True, 'avisos': [], 'whatsapp': ''})
    
    config_admin = Configuracao.objects.filter(usuario=admin_user).first()
    
    avisos_ativos = AvisoSistema.objects.filter(
        usuario=admin_user,
        ativo=True,
        data_inicio__lte=agora
    ).filter(
        Q(data_fim__isnull=True) | Q(data_fim__gte=agora)
    ).order_by('ordem')
    
    avisos_vistos_sessao = request.session.get('avisos_vistos', [])
    avisos_para_mostrar = []
    
    for aviso in avisos_ativos:
        # 🔴 CORREÇÃO: Se NÃO é "a cada login" e já foi visto na sessão, PULA
        # Se É "a cada login", mostra 1 vez por sessão também
        if str(aviso.id) in avisos_vistos_sessao:
            continue
        
        # Verifica se foi ocultado permanentemente
        visto = AvisoVisto.objects.filter(
            aviso=aviso, 
            cliente=request.user, 
            oculto_permanentemente=True
        ).first()
        if visto:
            continue
        
        mostrar = False
        
        # REGRA 1: Mostrar a cada login (mostra 1 vez por sessão)
        if aviso.mostrar_a_cada_login:
            mostrar = True
        
        # REGRA 2: Mostrar primeiros logins
        elif aviso.mostrar_primeiro_login:
            visto_count = AvisoVisto.objects.filter(
                aviso=aviso, 
                cliente=request.user
            ).count()
            if visto_count < aviso.repeticoes:
                mostrar = True
        
        # REGRA 3: Intervalo de horas
        elif aviso.mostrar_intervalo_horas:
            ultimo_visto = AvisoVisto.objects.filter(
                aviso=aviso, 
                cliente=request.user
            ).order_by('-data_visto').first()
            
            if ultimo_visto:
                horas = (agora - ultimo_visto.data_visto).total_seconds() / 3600
                if horas >= aviso.mostrar_intervalo_horas:
                    mostrar = True
            else:
                mostrar = True
        
        # REGRA 4: Vencimento
        elif aviso.mostrar_antes_vencimento or aviso.mostrar_no_vencimento:
            hoje = timezone.localdate()
            data_vencimento_usuario = request.user.data_vencimento
            
            if data_vencimento_usuario:
                if hasattr(data_vencimento_usuario, 'date'):
                    data_vencimento_usuario = data_vencimento_usuario.date()
                
                if aviso.mostrar_antes_vencimento:
                    data_alvo = hoje + timedelta(days=aviso.mostrar_antes_vencimento)
                    if data_vencimento_usuario == data_alvo:
                        mostrar = True
                
                if aviso.mostrar_no_vencimento and not mostrar:
                    if data_vencimento_usuario == hoje:
                        mostrar = True
        
        # REGRA 5: Sem regra específica
        else:
            mostrar = True
        
        if mostrar:
            avisos_para_mostrar.append({
                'id': aviso.id,
                'titulo': aviso.titulo,
                'mensagem': aviso.mensagem,
                'tipo': aviso.tipo,
                'icone': aviso.icone,
                'cor_destaque': aviso.cor_destaque,
                'permitir_ocultar': aviso.permitir_ocultar,
            })
            
            # 🔴 Registra na sessão (NÃO mostra de novo até próximo login)
            avisos_vistos_sessao.append(str(aviso.id))
            
            if aviso.permitir_ocultar:
                visto_obj, created = AvisoVisto.objects.get_or_create(
                    aviso=aviso,
                    cliente=request.user,
                    defaults={'contador': 1}
                )
                if not created:
                    visto_obj.contador += 1
                    visto_obj.data_visto = agora
                    visto_obj.save()
    
    request.session['avisos_vistos'] = avisos_vistos_sessao
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'avisos': avisos_para_mostrar,
        'whatsapp': config_admin.numero_celular if config_admin else '',
    })

@login_required
@require_POST
def ocultar_aviso(request, aviso_id):
    """Cliente decide não ver mais este aviso"""
    try:
        visto, created = AvisoVisto.objects.get_or_create(
            aviso_id=aviso_id,
            cliente=request.user,
            defaults={'oculto_permanentemente': True, 'contador': 1}
        )
        visto.oculto_permanentemente = True
        visto.save()
        
        # Também remove da sessão
        avisos_vistos = request.session.get('avisos_vistos', [])
        if str(aviso_id) in avisos_vistos:
            avisos_vistos.remove(str(aviso_id))
            request.session['avisos_vistos'] = avisos_vistos
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required
@require_POST
def marcar_aviso_visto(request):
    """Marca que o usuário viu os avisos"""
    request.session['ultimo_aviso_exibido'] = timezone.now().isoformat()
    return JsonResponse({'success': True})






#############################################################################
# views.py - Adicione estas funções
# views.py - Atualize a função send_recovery_code

@require_POST
def send_recovery_code(request):
    """Envia um código de recuperação sem expor o código ou o WhatsApp completo."""
    username = request.POST.get("username", "").strip()
    if not username:
        return JsonResponse({"success": False, "message": "Usuário não informado."}, status=400)

    # Limita reenvios por usuário e IP para reduzir abuso e enumeração.
    ip = (request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
          or request.META.get("REMOTE_ADDR", "")
          or "unknown")
    rate_key = f"password-recovery:{hashlib.sha256((username.lower() + '|' + ip).encode()).hexdigest()}"
    if cache.get(rate_key):
        return JsonResponse({
            "success": False,
            "message": "Aguarde um minuto antes de solicitar outro código.",
        }, status=429)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # Resposta neutra: evita confirmar publicamente quais usuários existem.
        cache.set(rate_key, True, 60)
        return JsonResponse({
            "success": True,
            "message": "Se o usuário possuir WhatsApp cadastrado, o código será enviado.",
            "expires_in": 300,
        })

    whatsapp = re.sub(r"\D", "", user.whatsapp or "")
    if not whatsapp:
        return JsonResponse({
            "success": False,
            "message": "Esta conta não possui WhatsApp cadastrado. Contate o suporte.",
        }, status=400)

    request.session.cycle_key()
    session_key = request.session.session_key or ""
    VerificationCode.objects.filter(
        code_type="whatsapp",
        whatsapp_number=whatsapp,
        is_used=False,
    ).update(is_used=True)

    verification_code = VerificationCode.generate_code(
        code_type="whatsapp",
        session_key=session_key,
        whatsapp_number=whatsapp,
        length=6,
    )

    if not send_whatsapp_recovery_message(whatsapp, verification_code.code, user):
        verification_code.mark_as_used()
        return JsonResponse({
            "success": False,
            "message": "Não foi possível enviar o código agora. Tente novamente.",
        }, status=502)

    request.session["recovery_user_id"] = user.id
    request.session["recovery_started_at"] = timezone.now().timestamp()
    request.session.pop("recovery_failed_attempts", None)
    request.session.pop("password_reset_user_id", None)
    request.session.pop("password_reset_verified_at", None)
    request.session.modified = True
    cache.set(rate_key, True, 60)

    LogAtividade.registrar(
        request=request,
        usuario=user,
        tipo_acao="acesso",
        descricao="Solicitação de recuperação de senha - código enviado",
        status="sucesso",
    )
    return JsonResponse({
        "success": True,
        "message": "Código enviado para o WhatsApp cadastrado.",
        "expires_in": 300,
    })


def send_whatsapp_recovery_message(whatsapp_number, code, user):
    """Envia a recuperação usando somente configuração protegida do ambiente."""
    base_url = str(getattr(settings, "EVOLUTION_API_BASE_URL", "") or "").rstrip("/")
    api_key = str(getattr(settings, "EVOLUTION_GLOBAL_API_KEY", "") or "").strip()
    instance_name = str(getattr(settings, "EVOLUTION_RECOVERY_INSTANCE", "gestor") or "gestor").strip()

    if not base_url or not api_key or not instance_name:
        logger.error("Configuração da Evolution incompleta para recuperação de senha.")
        return False

    numero = re.sub(r"\D", "", str(whatsapp_number or ""))
    if not numero.startswith("55") and len(numero) in (10, 11):
        numero = f"55{numero}"
    if len(numero) < 12 or len(numero) > 15:
        return False

    message = (
        "🔐 *RECUPERAÇÃO DE SENHA*\n\n"
        f"Olá *{user.nome or user.username}*!\n\n"
        "Seu código de verificação é:\n\n"
        f"*{code}*\n\n"
        "⚠️ Não compartilhe este código com ninguém.\n"
        "⏰ Este código expira em 5 minutos.\n\n"
        "Se você não solicitou a recuperação de senha, ignore esta mensagem."
    )

    try:
        response = requests.post(
            f"{base_url}/message/sendText/{instance_name}",
            json={"number": numero, "text": message},
            headers={"apikey": api_key, "Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code in (200, 201):
            return True
        logger.error("Evolution recusou recuperação de senha: HTTP %s", response.status_code)
        return False
    except requests.RequestException as exc:
        logger.error("Falha de rede ao enviar recuperação de senha: %s", exc)
        return False


@require_POST
def verify_recovery_code(request):
    """Valida o código somente para a conta vinculada à sessão atual."""
    code = request.POST.get("code", "").strip()
    user_id = request.session.get("recovery_user_id")
    started_at = request.session.get("recovery_started_at")

    if not code or not user_id or not started_at:
        return JsonResponse({"success": False, "message": "Sessão de recuperação expirada."}, status=400)
    if timezone.now().timestamp() - float(started_at) > 300:
        return JsonResponse({"success": False, "message": "Código expirado. Solicite outro."}, status=400)

    tentativas = int(request.session.get("recovery_failed_attempts", 0) or 0)
    if tentativas >= 5:
        for key in ("recovery_user_id", "recovery_started_at", "recovery_failed_attempts"):
            request.session.pop(key, None)
        request.session.modified = True
        return JsonResponse({
            "success": False,
            "message": "Muitas tentativas inválidas. Solicite um novo código.",
        }, status=429)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "Sessão de recuperação inválida."}, status=400)

    whatsapp = re.sub(r"\D", "", user.whatsapp or "")
    session_key = request.session.session_key or ""
    code_obj = VerificationCode.objects.filter(
        code=code,
        code_type="whatsapp",
        is_used=False,
        expires_at__gt=timezone.now(),
        whatsapp_number=whatsapp,
        session_key=session_key,
    ).first()

    if not code_obj:
        request.session["recovery_failed_attempts"] = tentativas + 1
        request.session.modified = True
        return JsonResponse({"success": False, "message": "Código inválido ou expirado."}, status=400)

    request.session.pop("recovery_failed_attempts", None)
    code_obj.mark_as_used()
    request.session["password_reset_user_id"] = user.id
    request.session["password_reset_verified_at"] = timezone.now().timestamp()
    request.session.modified = True

    LogAtividade.registrar(
        request=request,
        usuario=user,
        tipo_acao="acesso",
        descricao="Código de recuperação verificado com sucesso",
        status="sucesso",
    )
    return JsonResponse({"success": True, "message": "Código verificado com sucesso."})


@require_POST
def reset_password(request):
    """Redefine a senha somente após autorização registrada na sessão."""
    new_password = request.POST.get("password", "")
    user_id = request.session.get("password_reset_user_id")
    verified_at = request.session.get("password_reset_verified_at")

    if len(new_password) < 6:
        return JsonResponse({
            "success": False,
            "message": "A senha deve ter no mínimo 6 caracteres.",
        }, status=400)
    if not user_id or not verified_at:
        return JsonResponse({"success": False, "message": "Sessão de recuperação não autorizada."}, status=403)
    if timezone.now().timestamp() - float(verified_at) > 600:
        return JsonResponse({"success": False, "message": "Autorização expirada. Recomece a recuperação."}, status=403)

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"success": False, "message": "Sessão inválida."}, status=400)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    VerificationCode.objects.filter(
        code_type="whatsapp",
        whatsapp_number=re.sub(r"\D", "", user.whatsapp or ""),
        is_used=False,
    ).update(is_used=True)

    for key in (
        "recovery_user_id", "recovery_started_at",
        "password_reset_user_id", "password_reset_verified_at",
    ):
        request.session.pop(key, None)
    request.session.modified = True

    LogAtividade.registrar(
        request=request,
        usuario=user,
        tipo_acao="update",
        descricao="Senha redefinida via recuperação por WhatsApp",
        status="sucesso",
    )
    logger.info("Senha redefinida via recuperação para o usuário id=%s", user.id)
    return JsonResponse({
        "success": True,
        "message": "Senha alterada com sucesso. Faça login com a nova senha.",
    })


@require_POST
def check_username(request):
    """Retorna apenas o WhatsApp mascarado; nunca expõe número completo ou id."""
    username = request.POST.get("username", "").strip()
    if len(username) < 2:
        return JsonResponse({"success": False, "message": "Digite mais caracteres."}, status=400)

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": "Usuário não encontrado.",
            "has_whatsapp": False,
        }, status=404)

    whatsapp = re.sub(r"\D", "", user.whatsapp or "")
    if not whatsapp:
        return JsonResponse({
            "success": True,
            "whatsapp": False,
            "whatsapp_masked": "Não cadastrado",
            "has_whatsapp": False,
        })

    masked = f"••••••{whatsapp[-4:]}" if len(whatsapp) >= 4 else "••••••••"
    return JsonResponse({
        "success": True,
        "whatsapp": True,
        "whatsapp_masked": masked,
        "has_whatsapp": True,
    })




# ============================================================
# INTEGRAÇÕES DE PLAYLIST
# Fun Plays, FocoX Player, Lazer Player e providers futuros
# ============================================================

# ============================================================
# INTEGRAÇÕES DE PLAYLISTS
# Apague todas as versões antigas destas funções antes de colar.
# ============================================================

# ============================================================
# INTEGRAÇÕES DE PLAYLISTS
# Apague todas as versões antigas destas funções antes de colar.
# ============================================================

import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .integrations.playlists.factory import (
    get_playlist_provider,
    get_providers,
    listar_provedores,
)
from .models import (
    CustomUser,
    HistoricoIntegracaoPlaylist,
    IntegracaoPlaylistCliente,
)

logger = logging.getLogger(__name__)


VERDADEIROS = {"on", "true", "1", "yes", "sim"}







def _credenciais_iptv(integracao):
    if integracao.cliente_id:
        usuario = getattr(integracao.cliente, "login_externo", "") or ""
        senha = getattr(integracao.cliente, "senha_leitura", "") or ""
        nome = (
            getattr(integracao.cliente, "nome", "")
            or getattr(integracao.cliente, "username", "")
            or usuario
        )
        username_sistema = getattr(integracao.cliente, "username", "") or ""
    else:
        usuario = integracao.usuario_iptv or ""
        senha = integracao.senha_iptv or ""
        nome = integracao.nome_avulso or usuario
        username_sistema = ""

    return {
        "usuario": str(usuario).strip(),
        "senha": str(senha).strip(),
        "nome": str(nome).strip(),
        "username_sistema": str(username_sistema).strip(),
    }


def resolver_variaveis_playlist(integracao):
    """
    Resolve credenciais e URL.

    Importante:
    - Fun Plays ignora DNS e URL, pois usa /playlist/code.
    - FocoX/Lazer usam URL pronta ou DNS para montar a URL Xtream.
    """
    dados = _credenciais_iptv(integracao)
    usuario_final = integracao.usuario_template or "{usuario}"
    senha_final = integracao.senha_template or "{senha}"
    dns = str(integracao.dns or "").strip().rstrip("/")
    url_final = str(integracao.url_template or "").strip()

    substituicoes = {
        "{usuario}": dados["usuario"],
        "{senha}": dados["senha"],
        "{nome}": dados["nome"],
        "{username_sistema}": dados["username_sistema"],
        "{dns}": dns,
    }

    for variavel, valor in substituicoes.items():
        usuario_final = usuario_final.replace(variavel, valor)
        senha_final = senha_final.replace(variavel, valor)
        url_final = url_final.replace(variavel, valor)

    classe = get_providers().get(integracao.provedor)
    campos = getattr(classe, "campos", {}) if classe else {}
    usa_dns = bool(campos.get("dns", {}).get("mostrar"))

    # Só providers de URL direta recebem URL automática.
    if usa_dns and not url_final and dns:
        if not dns.startswith(("http://", "https://")):
            dns = f"http://{dns}"
        url_final = (
            f"{dns.rstrip('/')}/get.php"
            f"?username={usuario_final}"
            f"&password={senha_final}"
            "&type=m3u_plus&output=ts"
        )

    return {
        **dados,
        "usuario": usuario_final,
        "senha": senha_final,
        "dns": dns,
        "url_playlist": url_final,
    }








@login_required
@require_POST
def pesquisar_dispositivo_playlist(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)

    try:
        resultado = get_playlist_provider(integracao).pesquisar_dispositivo()
        sucesso = bool(resultado.get("success"))
        integracao.status = "configurado" if sucesso else "erro"
        integracao.ultima_mensagem = resultado.get("message", "Pesquisa concluída.")
        integracao.ultima_sincronizacao = timezone.now()
        if isinstance(resultado.get("data"), dict):
            integracao.dados_remotos = resultado["data"]
        integracao.save()

        _registrar_historico(
            integracao,
            "pesquisar",
            "sucesso" if sucesso else "erro",
            integracao.ultima_mensagem,
            resultado,
        )
        return JsonResponse(
            {
                "success": sucesso,
                "confirmed": bool(resultado.get("confirmed", sucesso)),
                "message": integracao.ultima_mensagem,
                "status": integracao.status,
                "data": resultado.get("data", {}),
            },
            status=200 if sucesso else 400,
        )
    except Exception as erro:
        logger.exception("Erro ao pesquisar dispositivo da integração %s", integracao.id)
        integracao.status = "erro"
        integracao.ultima_mensagem = str(erro)
        integracao.save(update_fields=["status", "ultima_mensagem", "atualizado_em"])
        _registrar_historico(integracao, "pesquisar", "erro", str(erro))
        return JsonResponse(
            {"success": False, "message": f"Erro ao pesquisar: {erro}", "status": "erro"},
            status=500,
        )







############################   API INTEGRAÇÃO #######################################################################

import logging
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .integrations.playlists.factory import (
    get_playlist_provider,
    get_providers,
    listar_provedores,
)
from .models import (
    CustomUser,
    HistoricoIntegracaoPlaylist,
    IntegracaoPlaylistCliente,
    PlaylistRemota,
)

logger = logging.getLogger(__name__)
VERDADEIROS = {"on", "true", "1", "yes", "sim"}


def _json_erro(message, status=400, **extra):
    return JsonResponse(
        {"success": False, "message": message, **extra},
        status=status,
    )


def _integracao_usuario(request, integracao_id):
    return get_object_or_404(
        IntegracaoPlaylistCliente.objects.select_related("cliente"),
        id=integracao_id,
        dono=request.user,
    )


def _playlist_usuario(request, playlist_id):
    return get_object_or_404(
        PlaylistRemota.objects.select_related(
            "integracao",
            "integracao__cliente",
            "cliente",
        ),
        id=playlist_id,
        integracao__dono=request.user,
    )


def _nome_provedor(slug):
    classe = get_providers().get(str(slug or "").strip())
    return classe.nome if classe else str(slug or "Aplicativo")


def _registrar_historico(
    integracao,
    acao,
    status,
    mensagem,
    resultado=None,
    playlist=None,
    requisicao=None,
):
    resultado = resultado if isinstance(resultado, dict) else {}
    return HistoricoIntegracaoPlaylist.objects.create(
        integracao=integracao,
        playlist=playlist,
        acao=acao,
        status=status,
        mensagem=mensagem,
        http_status=resultado.get("http_status"),
        requisicao_resumo=requisicao or {},
        resposta_api=resultado,
    )


def _credenciais_playlist(playlist):
    dados = playlist.credenciais()
    return (
        str(dados.get("usuario") or "").strip(),
        str(dados.get("senha") or "").strip(),
    )


def _montar_url(playlist, usuario, senha):
    url = str(playlist.url_playlist or "").strip()
    if url:
        return url

    dns = str(playlist.dns or playlist.integracao.dns or "").strip().rstrip("/")
    if not dns:
        return ""

    if not dns.startswith(("http://", "https://")):
        dns = f"http://{dns}"

    return (
        f"{dns}/get.php?username={usuario}&password={senha}"
        "&type=m3u_plus&output=ts"
    )


def _extrair_dados_url(url):
    try:
        parsed = urlparse(str(url or ""))
        params = parse_qs(parsed.query)
        dns = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        return {
            "dns": dns,
            "usuario": (params.get("username") or [""])[0],
            "senha": (params.get("password") or [""])[0],
        }
    except Exception:
        return {"dns": "", "usuario": "", "senha": ""}


def _payload_subida(playlist):
    usuario, senha = _credenciais_playlist(playlist)
    url_playlist = _montar_url(playlist, usuario, senha)

    modo_cadastro = str(playlist.modo_envio or "").strip().lower()
    modo_provider = "codigo" if modo_cadastro == "parceria" else "url"

    return {
        "nome_playlist": playlist.nome,
        "usuario": usuario,
        "senha": senha,
        "dns": playlist.dns or playlist.integracao.dns,
        "url_playlist": url_playlist,
        "codigo": playlist.codigo or playlist.integracao.codigo,
        "proteger": playlist.protegida,
        "pin": playlist.pin_protecao,
        # Os providers antigos conhecem apenas URL ou código.
        "modo_envio": modo_provider,
    }


@login_required
def pagina_integracoes_playlist(request):
    termo = request.GET.get("termo", "").strip()

    playlists_prefetch = Prefetch(
        "playlists",
        queryset=PlaylistRemota.objects.select_related("cliente").order_by("nome", "id"),
    )

    integracoes = (
        IntegracaoPlaylistCliente.objects
        .select_related("cliente")
        .prefetch_related(playlists_prefetch)
        .filter(dono=request.user)
    )

    if termo:
        integracoes = integracoes.filter(
            Q(cliente__nome__icontains=termo)
            | Q(cliente__username__icontains=termo)
            | Q(cliente__login_externo__icontains=termo)
            | Q(nome_avulso__icontains=termo)
            | Q(usuario_iptv__icontains=termo)
            | Q(mac_address__icontains=termo)
            | Q(device_key__icontains=termo)
            | Q(playlists__nome__icontains=termo)
            | Q(playlists__remote_id__icontains=termo)
        ).distinct()

    provedores = listar_provedores()
    configuracao = Configuracao.objects.filter(usuario=request.user).first()
    cliente_preselecionado_id = str(request.GET.get("cliente_id", "") or "").strip()
    if cliente_preselecionado_id and not CustomUser.objects.filter(
        id=cliente_preselecionado_id, dono=request.user
    ).exists():
        cliente_preselecionado_id = ""

    integracoes_lista = list(integracoes.order_by("nome_avulso", "-id"))
    for integracao in integracoes_lista:
        playlists = list(integracao.playlists.all())
        principal = playlists[0] if playlists else None
        integracao.lista_principal = principal
        modo = ""
        if principal:
            modo = str(principal.modo_envio or "").strip().lower()
            if modo not in {"m3u", "xtream", "parceria"}:
                # Compatibilidade com cadastros antigos.
                if principal.codigo:
                    modo = "parceria"
                elif principal.url_playlist:
                    modo = "m3u"
                elif principal.usuario_iptv or principal.senha_iptv or principal.dns:
                    modo = "xtream"
        if not modo:
            modo = str((integracao.dados_remotos or {}).get("modo_acesso") or "m3u")
        integracao.modo_acesso_view = modo
        integracao.tem_lista_view = bool(
            principal and (
                principal.url_playlist or principal.usuario_iptv or
                principal.senha_iptv or principal.dns or principal.codigo
            )
        )

    return render(
        request,
        "clientes/integracoes_playlist.html",
        {
            "integracoes": integracoes_lista,
            "clientes_disponiveis": CustomUser.objects.filter(
                dono=request.user
            ).order_by("nome", "username"),
            "provedores": provedores,
            "provedores_json": provedores,
            "termo": termo,
            "codigo_protecao_playlist": getattr(configuracao, "codigo_protecao_playlist", "") or "",
            "cliente_preselecionado_id": cliente_preselecionado_id,
            "abrir_novo_dispositivo": bool(cliente_preselecionado_id or request.GET.get("novo")),
        },
    )


@login_required
@require_POST
def salvar_integracao_playlist(request):
    """Salva o dispositivo e a lista como um único cadastro visual.

    A PlaylistRemota continua existindo apenas como detalhe técnico para não
    quebrar a integração já existente. Para o usuário, dispositivo e lista são
    editados no mesmo formulário. Se nenhum dado da lista for informado, o
    cadastro é tratado como "somente dispositivo".
    """
    integracao_id = str(request.POST.get("integracao_id", "") or "").strip()
    cliente_id = str(request.POST.get("cliente_id", "") or "").strip()
    provedor_slug = str(request.POST.get("provedor", "") or "").strip()
    nome_avulso = str(request.POST.get("nome_avulso", "") or "").strip()
    mac_address = str(request.POST.get("mac_address", "") or "").strip().lower()

    device_key_recebida = str(request.POST.get("device_key", "") or "").strip()
    if len(device_key_recebida) > 150:
        return _json_erro("A Device Key deve ter no máximo 150 caracteres.")

    # A Device Key pertence ao dispositivo e nunca é reaproveitada como código
    # de proteção. O código de proteção é uma configuração separada, aplicada
    # automaticamente somente às listas.
    codigo_protecao_padrao = str(
        Configuracao.objects.filter(usuario=request.user)
        .values_list("codigo_protecao_playlist", flat=True)
        .first()
        or ""
    ).strip()

    classe = get_providers().get(provedor_slug)
    if not classe:
        return _json_erro("Aplicativo inválido.")

    cliente = None
    if cliente_id:
        cliente = get_object_or_404(CustomUser, id=cliente_id, dono=request.user)

    playlist_existente = None
    if integracao_id:
        integracao = get_object_or_404(
            IntegracaoPlaylistCliente, id=integracao_id, dono=request.user
        )
        playlist_existente = (
            PlaylistRemota.objects.filter(integracao=integracao)
            .order_by("id")
            .first()
        )
        if playlist_existente and playlist_existente.protegida:
            codigo_edicao = str(
                request.POST.get("codigo_protecao_edicao", "") or ""
            ).strip()
            if not codigo_edicao:
                return _json_erro(
                    "Informe o código de proteção para editar esta lista.",
                    status=403,
                )
            if codigo_edicao != str(playlist_existente.pin_protecao or "").strip():
                return _json_erro(
                    "Código de proteção incorreto. A edição não foi salva.",
                    status=403,
                )
    else:
        integracao = IntegracaoPlaylistCliente(dono=request.user)

    if not nome_avulso:
        return _json_erro("Informe o Nome do cadastro. Esse será o nome exibido no Gerenciador de playlists.")

    campos_provedor = getattr(classe, "campos", {}) or {}
    campo_mac = campos_provedor.get("mac_address", {}) or {}
    campo_key = campos_provedor.get("device_key", {}) or {}
    if campo_mac.get("mostrar", True) and campo_mac.get("obrigatorio") and not mac_address:
        return _json_erro("Informe o MAC Address do dispositivo.")
    if (
        campo_key.get("mostrar", False)
        and campo_key.get("obrigatorio")
        and not device_key_recebida
        and not integracao.device_key
    ):
        return _json_erro("Informe a Device Key do dispositivo.")

    duplicada = (
        IntegracaoPlaylistCliente.objects.filter(
            dono=request.user,
            provedor=provedor_slug,
            mac_address__iexact=mac_address,
        )
        .exclude(pk=integracao.pk)
        .first()
    )
    if duplicada:
        nome_existente = duplicada.nome_exibicao or duplicada.nome_avulso or mac_address
        return JsonResponse(
            {
                "success": False,
                "duplicate": True,
                "integracao_id": duplicada.id,
                "message": (
                    f'Este dispositivo já está cadastrado como "{nome_existente}" '
                    f'no aplicativo "{getattr(classe, "nome", provedor_slug)}".'
                ),
            },
            status=409,
        )

    # -------- dados do modo de acesso --------
    modo_acesso = str(request.POST.get("modo_acesso", "m3u") or "m3u").strip().lower()
    if modo_acesso not in {"m3u", "xtream", "parceria"}:
        return _json_erro("Modo de acesso inválido.")

    lista_url = str(request.POST.get("playlist_url", "") or "").strip()
    lista_epg = str(request.POST.get("playlist_epg_url", "") or "").strip()
    lista_senha_edicao = str(request.POST.get("playlist_senha_edicao", "") or "").strip()
    lista_usuario = str(request.POST.get("playlist_usuario", "") or "").strip()
    lista_senha = str(request.POST.get("playlist_senha", "") or "").strip()
    lista_dns = str(request.POST.get("playlist_dns", "") or "").strip()
    lista_codigo = str(request.POST.get("playlist_codigo", "") or "").strip()
    if modo_acesso == "parceria":
        lista_usuario = str(request.POST.get("playlist_usuario_parceria", "") or "").strip()
        lista_senha = str(request.POST.get("playlist_senha_parceria", "") or "").strip()
        lista_codigo = str(request.POST.get("playlist_codigo_parceria", "") or "").strip()

    if modo_acesso == "m3u":
        tem_lista = bool(lista_url or lista_epg or lista_senha_edicao)
        if tem_lista and not lista_url:
            return _json_erro("Informe a URL da lista M3U.")
    elif modo_acesso == "xtream":
        tem_lista = bool(lista_usuario or lista_senha or lista_dns)
        if tem_lista and not (lista_usuario and lista_senha and lista_dns):
            return _json_erro("Para Xtream Code, informe DNS, usuário e senha.")
    else:  # parceria
        tem_lista = bool(lista_usuario or lista_senha or lista_codigo)
        if tem_lista and not (lista_usuario and lista_senha and lista_codigo):
            return _json_erro("Para Parceria, informe usuário, senha e código do servidor.")

    integracao.cliente = cliente
    integracao.provedor = provedor_slug
    integracao.nome_avulso = nome_avulso
    integracao.mac_address = mac_address
    if device_key_recebida or not integracao.pk:
        integracao.device_key = device_key_recebida

    # Não duplicamos DNS/código no dispositivo. Esses dados pertencem ao acesso.
    if not integracao.pk:
        integracao.codigo = ""
        integracao.dns = ""

    dados_integracao = dict(integracao.dados_remotos or {})
    dados_integracao["modo_acesso"] = modo_acesso
    integracao.dados_remotos = dados_integracao
    integracao.status = "configurado"
    integracao.ultima_mensagem = (
        "Cadastro salvo com lista configurada." if tem_lista
        else "Dispositivo salvo. Lista ainda não configurada."
    )

    playlist_principal = None
    try:
        with transaction.atomic():
            integracao.save()

            playlist_principal = (
                PlaylistRemota.objects.filter(integracao=integracao)
                .order_by("id")
                .first()
            )

            if tem_lista:
                if playlist_principal is None:
                    playlist_principal = PlaylistRemota(integracao=integracao)

                # O código configurado na tela de aplicativos é exclusivamente
                # um PIN de proteção da lista. Ele não aparece no cadastro do
                # cliente e é aplicado automaticamente. Listas já protegidas
                # preservam o próprio PIN para não perder acesso remoto.
                pin_protecao_lista = (
                    str(playlist_principal.pin_protecao or "").strip()
                    if playlist_principal.pk and playlist_principal.protegida
                    else codigo_protecao_padrao
                )
                playlist_principal.protegida = bool(pin_protecao_lista)
                playlist_principal.pin_protecao = pin_protecao_lista
                playlist_principal.pin_conhecido = bool(pin_protecao_lista)

                nome_lista = (
                    (cliente.nome or cliente.username) if cliente
                    else (nome_avulso or "Lista principal")
                )
                playlist_principal.cliente = cliente
                playlist_principal.nome = nome_lista
                playlist_principal.modo_envio = modo_acesso

                # Limpa campos que pertencem a outro tipo de acesso.
                playlist_principal.usuario_iptv = ""
                playlist_principal.senha_iptv = ""
                playlist_principal.dns = ""
                playlist_principal.codigo = ""
                playlist_principal.url_playlist = ""

                extras = dict(playlist_principal.dados_remotos or {})
                extras["modo_acesso"] = modo_acesso
                extras["epg_url"] = ""
                extras["senha_edicao"] = ""

                if modo_acesso == "m3u":
                    playlist_principal.url_playlist = lista_url
                    extras["epg_url"] = lista_epg
                    extras["senha_edicao"] = lista_senha_edicao
                    extraidos = _extrair_dados_url(lista_url)
                    playlist_principal.usuario_iptv = extraidos.get("usuario", "")
                    playlist_principal.senha_iptv = extraidos.get("senha", "")
                    playlist_principal.dns = extraidos.get("dns", "")
                elif modo_acesso == "xtream":
                    playlist_principal.usuario_iptv = lista_usuario
                    playlist_principal.senha_iptv = lista_senha
                    playlist_principal.dns = lista_dns
                else:
                    playlist_principal.usuario_iptv = lista_usuario
                    playlist_principal.senha_iptv = lista_senha
                    playlist_principal.codigo = lista_codigo

                playlist_principal.dados_remotos = extras
                playlist_principal.status = (
                    "confirmacao_pendente" if playlist_principal.remote_id else "rascunho"
                )
                playlist_principal.ultima_mensagem = (
                    "Dados atualizados no gestor. Publicação remota pendente."
                    if playlist_principal.remote_id
                    else "Lista configurada no cadastro. Ainda não foi publicada."
                )
                playlist_principal.save()
            elif playlist_principal and not playlist_principal.remote_id:
                # Se a lista nunca foi publicada e o usuário limpou os dados,
                # o cadastro volta a ser somente dispositivo.
                playlist_principal.delete()
                playlist_principal = None

    except IntegrityError as erro:
        logger.warning(
            "Tentativa de cadastrar dispositivo duplicado: dono=%s provedor=%s mac=%s erro=%s",
            request.user.id,
            provedor_slug,
            mac_address,
            erro,
        )
        duplicada = (
            IntegracaoPlaylistCliente.objects.filter(
                dono=request.user,
                provedor=provedor_slug,
                mac_address__iexact=mac_address,
            ).first()
        )
        return JsonResponse(
            {
                "success": False,
                "duplicate": True,
                "integracao_id": duplicada.id if duplicada else None,
                "message": "Este dispositivo já está cadastrado. Edite o cadastro existente.",
            },
            status=409,
        )
    except Exception as erro:
        logger.exception("Erro ao salvar cadastro unificado de playlist.")
        return JsonResponse(
            {
                "success": False,
                "message": f"Não foi possível salvar o cadastro: {erro}",
            },
            status=500,
        )

    return JsonResponse(
        {
            "success": True,
            "message": (
                "Cadastro e lista salvos com sucesso."
                if tem_lista else "Dispositivo salvo sem lista configurada."
            ),
            "integracao_id": integracao.id,
            "playlist_id": playlist_principal.id if playlist_principal else None,
            "tem_lista": bool(playlist_principal),
            "modo_acesso": modo_acesso,
            "status": integracao.status,
            "provedor": provedor_slug,
            "provedor_nome": getattr(classe, "nome", provedor_slug),
        }
    )

@login_required
@require_POST
def salvar_configuracao_playlist(request):
    """Salva o código/PIN usado para proteger novas listas.

    Este valor não é Device Key do aplicativo. A Device Key continua sendo
    informada no próprio dispositivo quando o provedor exigir.
    """
    configuracao, _ = Configuracao.objects.get_or_create(usuario=request.user)
    novo_codigo = str(
        request.POST.get("codigo_protecao_playlist", "") or ""
    ).strip()

    if len(novo_codigo) > 150:
        return JsonResponse(
            {
                "success": False,
                "message": "O código de proteção deve ter no máximo 150 caracteres.",
            },
            status=400,
        )

    limpar = (
        str(request.POST.get("limpar_codigo_protecao", "") or "").lower()
        in VERDADEIROS
    )
    if limpar:
        configuracao.codigo_protecao_playlist = ""
        configuracao.save(update_fields=["codigo_protecao_playlist"])
        return JsonResponse(
            {
                "success": True,
                "message": "Código de proteção padrão removido. As listas já protegidas mantêm o código atual.",
            }
        )

    if novo_codigo:
        configuracao.codigo_protecao_playlist = novo_codigo
        configuracao.save(update_fields=["codigo_protecao_playlist"])
        return JsonResponse(
            {
                "success": True,
                "message": "Código de proteção atualizado. Ele será aplicado automaticamente às novas listas.",
            }
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Configuração mantida sem alterações.",
        }
    )


@login_required
@require_GET
@never_cache
def detalhes_integracao_playlist(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)
    principal = integracao.playlists.all().order_by("id").first()
    modo = str((integracao.dados_remotos or {}).get("modo_acesso") or "m3u").strip().lower()
    playlist_data = None
    if principal:
        modo_p = str(principal.modo_envio or "").strip().lower()
        if modo_p in {"m3u", "xtream", "parceria"}:
            modo = modo_p
        else:
            modo = "parceria" if principal.codigo else "m3u" if principal.url_playlist else "xtream"
        extras = principal.dados_remotos if isinstance(principal.dados_remotos, dict) else {}
        playlist_data = {
            "id": principal.id,
            "nome": principal.nome,
            "remote_id": principal.remote_id,
            "usuario_iptv": principal.usuario_iptv,
            "senha_iptv": principal.senha_iptv,
            "dns": principal.dns,
            "url_playlist": principal.url_playlist,
            "codigo": principal.codigo,
            "modo_envio": modo,
            "epg_url": extras.get("epg_url", ""),
            "senha_edicao": extras.get("senha_edicao", ""),
            "status": principal.status,
            "protegida": principal.protegida,
            # O PIN nunca é devolvido para a tela. Em edição de lista
            # protegida o operador precisa informá-lo novamente.
            "pin_protecao": "",
            "requer_codigo_edicao": bool(
                principal.protegida and principal.pin_protecao
            ),
        }

    response = JsonResponse({
        "success": True,
        "integracao": {
            "id": integracao.id,
            "nome": integracao.nome_exibicao,
            "nome_avulso": integracao.nome_avulso,
            "cliente_id": integracao.cliente_id,
            "cliente": getattr(integracao.cliente, "nome", "") if integracao.cliente else "",
            "provedor": integracao.provedor,
            "provedor_nome": _nome_provedor(integracao.provedor),
            "mac_address": integracao.mac_address,
            "device_key": integracao.device_key,
            "status": integracao.status,
            "ultima_mensagem": integracao.ultima_mensagem,
            "modo_acesso": modo,
            "tem_lista": bool(playlist_data),
        },
        "lista": playlist_data,
        # Mantido para compatibilidade com JavaScript antigo ainda presente.
        "playlists": [playlist_data] if playlist_data else [],
    })
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@login_required
@require_GET
@never_cache
def detalhes_cliente_playlist(request, cliente_id):
    cliente = get_object_or_404(CustomUser, id=cliente_id, dono=request.user)
    response = JsonResponse({
        "success": True,
        "cliente": {
            "id": cliente.id,
            "nome": cliente.nome or cliente.username,
            "usuario_iptv": cliente.login_externo or "",
            "senha_iptv": cliente.senha_leitura or "",
        },
    })
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@login_required
@require_GET
@never_cache
def detalhes_playlist(request, playlist_id):
    p = _playlist_usuario(request, playlist_id)
    response = JsonResponse({
        "success": True,
        "playlist": {
            "id": p.id, "cliente_id": p.cliente_id, "nome": p.nome,
            "usuario_iptv": p.usuario_iptv, "senha_iptv": p.senha_iptv,
            "dns": p.dns, "codigo": p.codigo, "url_playlist": p.url_playlist,
            "modo_envio": p.modo_envio, "protegida": p.protegida,
            "pin_protecao": p.pin_protecao, "remote_id": p.remote_id,
            "status": p.status,
        },
    })
    response["Cache-Control"] = "no-store, max-age=0"
    return response


def _normalizar_novo_dns(valor):
    valor = str(valor or "").strip().rstrip("/")
    if not valor:
        raise ValueError("Informe o novo DNS.")
    if not valor.startswith(("http://", "https://")):
        valor = "http://" + valor
    parsed = urlparse(valor)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("DNS inválido. Exemplo: http://servidor.com:80")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _url_com_novo_dns(url_atual, novo_dns, usuario, senha):
    atual = str(url_atual or "").strip()
    if atual:
        parsed = urlparse(atual)
        if parsed.path or parsed.query:
            base = urlparse(novo_dns)
            return parsed._replace(scheme=base.scheme, netloc=base.netloc).geturl()
    return f"{novo_dns}/get.php?username={usuario}&password={senha}&type=m3u_plus&output=ts"


@login_required
@require_POST
def trocar_dns_em_massa(request):
    try:
        ids_raw = request.POST.get("playlist_ids", "[]")
        try:
            ids = json.loads(ids_raw) if isinstance(ids_raw, str) else ids_raw
        except json.JSONDecodeError:
            ids = request.POST.getlist("playlist_ids[]")
        ids = [int(x) for x in ids if str(x).isdigit()]
        if not ids:
            raise ValueError("Selecione pelo menos uma playlist.")
        novo_dns = _normalizar_novo_dns(request.POST.get("novo_dns"))
        playlists = list(
            PlaylistRemota.objects.select_related("integracao", "cliente")
            .filter(id__in=ids, integracao__dono=request.user)
        )
        if len(playlists) != len(set(ids)):
            raise ValueError("Uma ou mais playlists selecionadas não pertencem à sua conta.")

        atualizadas, publicadas, pendentes, falhas = 0, 0, [], []
        auth_map = {}
        for playlist in playlists:
            usuario, senha = _credenciais_playlist(playlist)
            playlist.dns = novo_dns
            playlist.url_playlist = _url_com_novo_dns(playlist.url_playlist, novo_dns, usuario, senha)
            playlist.status = "confirmacao_pendente" if playlist.remote_id else "rascunho"
            playlist.ultima_mensagem = "DNS alterado no gestor. Publicação remota pendente." if playlist.remote_id else "DNS alterado no gestor."
            playlist.save()
            atualizadas += 1

            if not playlist.remote_id:
                pendentes.append(playlist.id)
                continue
            provider = get_playlist_provider(playlist.integracao)
            if not bool(getattr(provider, "suporta_edicao_remota", False)):
                pendentes.append(playlist.id)
                continue
            try:
                resultado = provider.editar_playlist(remote_id=playlist.remote_id, **_payload_subida(playlist))
                if resultado.get("success"):
                    playlist.status = "ativo"
                    playlist.ultima_mensagem = resultado.get("message", "DNS atualizado no aplicativo.")
                    playlist.ultima_sincronizacao = timezone.now()
                    playlist.save()
                    publicadas += 1
                    _registrar_historico(playlist.integracao, "atualizar_remoto", "sucesso", playlist.ultima_mensagem, resultado, playlist=playlist)
                elif resultado.get("requires_captcha") and playlist.integracao.provedor == "ibo_player":
                    integracao = playlist.integracao
                    integracao.status = "aguardando_captcha"
                    integracao.ultima_mensagem = resultado.get("message", "Autentique o IBO para continuar.")
                    integracao.save(update_fields=["status", "ultima_mensagem", "atualizado_em"])
                    auth_map[integracao.id] = {
                        "integracao_id": integracao.id,
                        "nome": integracao.nome_exibicao,
                        "captcha_url": reverse("gerar_captcha_ibo", args=[integracao.id]),
                        "auth_url": reverse("autenticar_ibo_playlist", args=[integracao.id]),
                    }
                    pendentes.append(playlist.id)
                else:
                    pendentes.append(playlist.id)
                    falhas.append({"playlist_id": playlist.id, "message": resultado.get("message", "Falha ao publicar DNS.")})
            except Exception as exc:
                logger.exception("Falha ao trocar DNS remoto da playlist %s", playlist.id)
                pendentes.append(playlist.id)
                falhas.append({"playlist_id": playlist.id, "message": str(exc)})

        return JsonResponse({
            "success": True,
            "message": f"DNS atualizado em {atualizadas} playlist(s). {publicadas} publicada(s) no aplicativo.",
            "atualizadas": atualizadas, "publicadas": publicadas,
            "pendentes": sorted(set(pendentes)), "falhas": falhas,
            "auth_required": list(auth_map.values()),
        })
    except ValueError as exc:
        return JsonResponse({"success": False, "message": str(exc)}, status=400)


@login_required
@require_POST
def criar_playlist_local(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)
    cliente_id = request.POST.get("cliente_id", "").strip()

    cliente = None
    if cliente_id:
        cliente = get_object_or_404(
            CustomUser,
            id=cliente_id,
            dono=request.user,
        )

    nome = request.POST.get("nome", "").strip()
    if not nome:
        return _json_erro("Informe o nome da playlist.")

    codigo_padrao = str(
        Configuracao.objects.filter(usuario=request.user)
        .values_list("codigo_protecao_playlist", flat=True)
        .first()
        or ""
    ).strip()
    pin = request.POST.get("pin_protecao", "").strip() or codigo_padrao
    protegida = bool(pin)

    device_key_recebida = request.POST.get("device_key", "").strip()

    if device_key_recebida or not integracao.pk:
        integracao.device_key = device_key_recebida

    playlist = PlaylistRemota.objects.create(
        integracao=integracao,
        cliente=cliente,
        nome=nome,
        usuario_iptv=request.POST.get("usuario_iptv", "").strip(),
        senha_iptv=request.POST.get("senha_iptv", "").strip(),
        dns=request.POST.get("dns", "").strip(),
        codigo=request.POST.get("codigo", "").strip(),
        url_playlist=request.POST.get("url_playlist", "").strip(),
        modo_envio=request.POST.get("modo_envio", "url").strip() or "url",
        protegida=protegida,
        pin_protecao=pin if protegida else "",
        pin_conhecido=bool(protegida and pin),
        status="rascunho",
        ultima_mensagem="Playlist criada localmente. Ainda não foi enviada.",
    )

    if request.POST.get("subir_agora", "").lower() in VERDADEIROS:
        return _subir_playlist_objeto(request, playlist)

    return JsonResponse({
        "success": True,
        "message": "Playlist criada localmente.",
        "playlist_id": playlist.id,
    })


def _subir_playlist_objeto(request, playlist):
    usuario, senha = _credenciais_playlist(playlist)
    if not usuario or not senha:
        return _json_erro(
            "Informe usuário e senha IPTV antes de subir a playlist.",
            playlist_id=playlist.id,
        )

    historico = _registrar_historico(
        playlist.integracao,
        "adicionar",
        "processando",
        "Iniciando envio da playlist.",
        playlist=playlist,
    )

    try:
        playlist.status = "processando"
        playlist.save(update_fields=["status", "atualizado_em"])

        resultado = get_playlist_provider(
            playlist.integracao
        ).adicionar_playlist(**_payload_subida(playlist))

        sucesso = bool(resultado.get("success"))
        confirmado = bool(resultado.get("confirmed", sucesso))
        remote_id = str(resultado.get("remote_id") or "").strip()

        playlist.remote_id = remote_id or playlist.remote_id
        playlist.nome_remoto = playlist.nome if confirmado else playlist.nome_remoto
        playlist.status = (
            "ativo"
            if sucesso and confirmado
            else "confirmacao_pendente"
            if sucesso
            else "erro"
        )
        playlist.ultima_mensagem = resultado.get("message", "Operação concluída.")
        playlist.ultima_sincronizacao = timezone.now()
        playlist.dados_remotos = resultado.get("data", {})
        playlist.save()

        historico.status = (
            "sucesso"
            if sucesso and confirmado
            else "parcial"
            if sucesso
            else "erro"
        )
        historico.mensagem = playlist.ultima_mensagem
        historico.http_status = resultado.get("http_status")
        historico.resposta_api = resultado
        historico.save()

        return JsonResponse({
            "success": sucesso,
            "confirmed": confirmado,
            "message": playlist.ultima_mensagem,
            "playlist_id": playlist.id,
            "remote_id": playlist.remote_id,
            "status": playlist.status,
        }, status=200 if sucesso else 400)

    except Exception as erro:
        logger.exception("Erro ao subir playlist %s", playlist.id)
        playlist.status = "erro"
        playlist.ultima_mensagem = str(erro)
        playlist.save()
        historico.status = "erro"
        historico.mensagem = str(erro)
        historico.save()
        return _json_erro("Não foi possível publicar a playlist no aplicativo.", 500)


@login_required
@require_POST
def subir_playlist(request, playlist_id):
    playlist = _playlist_usuario(request, playlist_id)
    return _subir_playlist_objeto(request, playlist)




@login_required
@require_POST
def atualizar_playlist_remota(request, playlist_id):
    playlist = _playlist_usuario(request, playlist_id)
    if not playlist.remote_id:
        return _json_erro("Esta playlist ainda não possui ID remoto.")

    try:
        resultado = get_playlist_provider(
            playlist.integracao
        ).obter_playlist(playlist.remote_id)

        remota = resultado.get("playlist")
        if not resultado.get("success") or not remota:
            playlist.status = "nao_encontrada"
            playlist.encontrada_na_ultima_sync = False
            playlist.ultima_mensagem = resultado.get(
                "message",
                "Playlist não encontrada.",
            )
            playlist.ultima_sincronizacao = timezone.now()
            playlist.save()
            return _json_erro(playlist.ultima_mensagem, 404)

        playlist.nome_remoto = remota.get("nome") or playlist.nome_remoto
        playlist.protegida = bool(remota.get("protegida"))
        playlist.status = "ativo"
        playlist.encontrada_na_ultima_sync = True
        playlist.ultima_sincronizacao = timezone.now()
        playlist.ultima_mensagem = "Playlist atualizada a partir do painel."
        playlist.dados_remotos = remota.get("raw", remota)
        playlist.save()

        _registrar_historico(
            playlist.integracao,
            "consultar",
            "sucesso",
            playlist.ultima_mensagem,
            resultado,
            playlist,
        )

        return JsonResponse({
            "success": True,
            "message": playlist.ultima_mensagem,
            "playlist": {
                "id": playlist.id,
                "nome": playlist.nome,
                "nome_remoto": playlist.nome_remoto,
                "protegida": playlist.protegida,
                "status": playlist.status,
            },
        })
    except Exception as erro:
        return _json_erro(f"Erro ao atualizar playlist: {erro}", 500)





@login_required
@require_POST
def excluir_playlist(request, playlist_id):
    playlist = _playlist_usuario(request, playlist_id)
    modo = request.POST.get("modo", "").strip().lower()
    pin = request.POST.get("pin", "").strip() or playlist.pin_protecao

    if modo not in {"local", "remota", "ambas"}:
        return _json_erro("Escolha excluir local, remota ou ambas.")

    if modo == "local":
        playlist.delete()
        return JsonResponse({
            "success": True,
            "message": "Playlist excluída somente do sistema.",
            "deleted_local": True,
        })

    if not playlist.remote_id:
        return _json_erro(
            "A playlist não possui ID remoto. Exclua somente do sistema."
        )

    resultado = get_playlist_provider(
        playlist.integracao
    ).excluir_playlist(
        remote_id=playlist.remote_id,
        pin=pin,
        protegida=playlist.protegida,
    )

    sucesso = bool(resultado.get("success") and resultado.get("confirmed"))
    _registrar_historico(
        playlist.integracao,
        "excluir",
        "sucesso" if sucesso else "erro",
        resultado.get("message", "Exclusão concluída."),
        resultado,
        playlist,
    )

    if not sucesso:
        return _json_erro(
            resultado.get("message", "O painel não confirmou a exclusão."),
            400,
        )

    if modo == "ambas":
        playlist.delete()
        return JsonResponse({
            "success": True,
            "message": "Playlist excluída do painel e do sistema.",
            "deleted_local": True,
        })

    playlist.remote_id = ""
    playlist.status = "excluida"
    playlist.encontrada_na_ultima_sync = False
    playlist.ultima_mensagem = "Playlist excluída somente do painel."
    playlist.save()

    return JsonResponse({
        "success": True,
        "message": playlist.ultima_mensagem,
        "deleted_local": False,
    })


@login_required
@require_POST
def excluir_integracao(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)
    if integracao.playlists.exists():
        return _json_erro(
            "Exclua as playlists locais antes de excluir o dispositivo."
        )
    integracao.delete()
    return JsonResponse({
        "success": True,
        "message": "Dispositivo excluído do sistema.",
    })


@login_required
def historico_integracao_playlist(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)
    playlist_id = request.GET.get("playlist_id", "").strip()

    queryset = integracao.historico.select_related("playlist")
    if playlist_id:
        queryset = queryset.filter(playlist_id=playlist_id)

    dados = [{
        "acao": item.get_acao_display(),
        "status": item.status,
        "status_nome": item.get_status_display(),
        "playlist": item.playlist.nome if item.playlist else "",
        "mensagem": item.mensagem,
        "http_status": item.http_status,
        "criado_em": timezone.localtime(item.criado_em).strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    } for item in queryset[:100]]

    return JsonResponse({
        "success": True,
        "cliente": integracao.nome_exibicao,
        "provedor": _nome_provedor(integracao.provedor),
        "historico": dados,
    })


@login_required
@require_POST
def migrar_playlist_legada(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)

    if not (
        integracao.playlist_remote_id
        or integracao.nome_playlist
        or integracao.usuario_iptv
    ):
        return _json_erro("Esta integração não possui playlist legada.")

    playlist, criada = PlaylistRemota.objects.get_or_create(
        integracao=integracao,
        remote_id=integracao.playlist_remote_id or "",
        defaults={
            "cliente": integracao.cliente,
            "nome": integracao.nome_playlist or integracao.nome_exibicao,
            "nome_remoto": integracao.nome_playlist or "",
            "usuario_iptv": integracao.usuario_iptv,
            "senha_iptv": integracao.senha_iptv,
            "dns": integracao.dns,
            "codigo": integracao.codigo,
            "url_playlist": integracao.url_template,
            "modo_envio": (
                integracao.dados_remotos.get("modo_envio", "url")
                if isinstance(integracao.dados_remotos, dict)
                else "url"
            ),
            "protegida": integracao.proteger,
            "pin_protecao": integracao.pin_protecao,
            "pin_conhecido": bool(integracao.pin_protecao),
            "status": (
                "ativo"
                if integracao.playlist_remote_id
                else "rascunho"
            ),
            "dados_remotos": integracao.dados_remotos,
        },
    )

    return JsonResponse({
        "success": True,
        "message": (
            "Playlist antiga migrada."
            if criada
            else "A playlist antiga já estava migrada."
        ),
        "playlist_id": playlist.id,
    })



from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST


@login_required
@require_POST
def excluir_dispositivo_playlist(request, integracao_id):
    integracao = get_object_or_404(
        IntegracaoPlaylistCliente.objects.prefetch_related("playlists"),
        id=integracao_id,
        dono=request.user,
    )

    nome = (
        getattr(integracao, "nome_exibicao", "")
        or getattr(integracao, "nome_avulso", "")
        or getattr(integracao, "mac_address", "")
        or f"Dispositivo #{integracao.id}"
    )

    quantidade_playlists = integracao.playlists.count()

    try:
        with transaction.atomic():
            # Remove primeiro as playlists locais vinculadas.
            # Isso também funciona caso o relacionamento não esteja com CASCADE.
            integracao.playlists.all().delete()

            # Depois remove o cadastro do dispositivo.
            integracao.delete()

        if quantidade_playlists:
            mensagem = (
                f'Dispositivo "{nome}" excluído com sucesso. '
                f"{quantidade_playlists} playlist(s) local(is) removida(s)."
            )
        else:
            mensagem = (
                f'Dispositivo "{nome}" excluído com sucesso.'
            )

        return JsonResponse(
            {
                "success": True,
                "message": mensagem,
                "playlists_excluidas": quantidade_playlists,
            }
        )

    except Exception as erro:
        logger.exception(
            "Erro ao excluir dispositivo de playlist %s",
            integracao_id,
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Não foi possível excluir o dispositivo: "
                    f"{erro}"
                ),
            },
            status=500,
        )


# ADICIONE/ATUALIZE ESTAS FUNÇÕES EM clientes/views.py
# Pressupõe que já existam no arquivo:
# _playlist_usuario, _integracao_usuario, _registrar_historico,
# _json_erro, get_playlist_provider, PlaylistRemota, transaction,
# timezone, JsonResponse, login_required e require_POST.

VERDADEIROS_PLAYLIST = {"1", "true", "on", "yes", "sim"}


def _estado_publicado_playlist(playlist):
    return {
        "remote_id": str(playlist.remote_id or "").strip(),
        "nome": str(playlist.nome or "").strip(),
        "usuario_iptv": str(playlist.usuario_iptv or "").strip(),
        "senha_iptv": str(playlist.senha_iptv or "").strip(),
        "dns": str(playlist.dns or "").strip(),
        "codigo": str(playlist.codigo or "").strip(),
        "url_playlist": str(playlist.url_playlist or "").strip(),
        "modo_envio": str(playlist.modo_envio or "url").strip(),
        "protegida": bool(playlist.protegida),
        "pin_protecao": str(playlist.pin_protecao or "").strip(),
    }




@login_required
@require_POST
def editar_playlist(request, playlist_id):
    playlist = _playlist_usuario(request, playlist_id)

    nome = str(request.POST.get("nome", "") or "").strip()
    if not nome:
        return JsonResponse(
            {"success": False, "message": "Informe o nome da playlist."},
            status=400,
        )

    protegida = (
        str(request.POST.get("protegida", "") or "").strip().lower()
        in VERDADEIROS_PLAYLIST
    )

    senha_recebida = str(request.POST.get("senha_iptv", "") or "").strip()
    pin_recebido = str(request.POST.get("pin_protecao", "") or "").strip()

    if playlist.protegida:
        if not pin_recebido:
            return JsonResponse(
                {"success": False, "message": "Informe o código de proteção para editar esta lista."},
                status=403,
            )
        if pin_recebido != str(playlist.pin_protecao or "").strip():
            return JsonResponse(
                {"success": False, "message": "Código de proteção incorreto. A edição não foi salva."},
                status=403,
            )

    dados_novos = {
        "nome": nome,
        "cliente_id": request.POST.get("cliente_id") or None,
        "usuario_iptv": str(request.POST.get("usuario_iptv", "") or "").strip(),
        "senha_iptv": senha_recebida or playlist.senha_iptv,
        "dns": str(request.POST.get("dns", "") or "").strip(),
        "codigo": str(request.POST.get("codigo", "") or "").strip(),
        "url_playlist": str(request.POST.get("url_playlist", "") or "").strip(),
        "modo_envio": str(request.POST.get("modo_envio", "") or "url").strip(),
        "protegida": protegida,
        "pin_protecao": (
            playlist.pin_protecao
            if protegida and playlist.protegida
            else (pin_recebido if protegida else "")
        ),
    }

    campos = tuple(dados_novos.keys())
    alterados = [
        campo
        for campo in campos
        if getattr(playlist, campo) != dados_novos[campo]
    ]

    if not alterados:
        return JsonResponse(
            {
                "success": True,
                "changed": False,
                "message": "Nenhuma alteração foi identificada.",
            }
        )

    dados_remotos = (
        dict(playlist.dados_remotos)
        if isinstance(playlist.dados_remotos, dict)
        else {}
    )

    if playlist.remote_id and not dados_remotos.get("ultimo_estado_publicado"):
        dados_remotos["ultimo_estado_publicado"] = _estado_publicado_playlist(
            playlist
        )

    for campo, valor in dados_novos.items():
        setattr(playlist, campo, valor)

    playlist.pin_conhecido = bool(
        playlist.protegida and playlist.pin_protecao
    )
    playlist.dados_remotos = dados_remotos

    if playlist.remote_id:
        playlist.status = "confirmacao_pendente"
        if playlist.integracao.provedor == "ibo_player":
            playlist.ultima_mensagem = (
                "Alterações salvas no gestor. Use “Atualizar no aplicativo” "
                "para publicá-las no IBO."
            )
        else:
            playlist.ultima_mensagem = (
                "Alterações salvas no gestor. Use “Substituir no aplicativo” "
                "para publicá-las."
            )
    else:
        playlist.status = "rascunho"
        playlist.ultima_mensagem = "Alterações salvas somente no gestor."

    playlist.save()

    _registrar_historico(
        playlist.integracao,
        "editar",
        "sucesso",
        playlist.ultima_mensagem,
        playlist=playlist,
    )

    return JsonResponse(
        {
            "success": True,
            "changed": True,
            "pending_remote": bool(playlist.remote_id),
            "message": playlist.ultima_mensagem,
            "fields_changed": alterados,
            "status": playlist.status,
        }
    )



@login_required
@require_POST
def substituir_playlist_remota(request, playlist_id):
    playlist = _playlist_usuario(request, playlist_id)

    confirmado = (
        str(request.POST.get("confirmar", "") or "").strip().lower()
        in VERDADEIROS_PLAYLIST
    )
    if not confirmado:
        return JsonResponse(
            {"success": False, "message": "Confirme a publicação das alterações."},
            status=400,
        )

    if not playlist.remote_id:
        return JsonResponse(
            {"success": False, "message": "Esta playlist não possui ID remoto."},
            status=400,
        )

    dados_remotos = (
        dict(playlist.dados_remotos)
        if isinstance(playlist.dados_remotos, dict)
        else {}
    )
    publicado = dados_remotos.get("ultimo_estado_publicado")
    if not isinstance(publicado, dict):
        publicado = _estado_publicado_playlist(playlist)

    historico = _registrar_historico(
        playlist.integracao,
        "atualizar_remoto" if playlist.integracao.provedor == "ibo_player" else "substituir",
        "processando",
        "Publicando alterações da playlist no aplicativo.",
        playlist=playlist,
    )

    provider = get_playlist_provider(playlist.integracao)

    try:
        if bool(getattr(provider, "suporta_edicao_remota", False)):
            resultado = provider.editar_playlist(
                remote_id=playlist.remote_id,
                nome_playlist=playlist.nome,
                usuario=playlist.usuario_iptv,
                senha=playlist.senha_iptv,
                dns=playlist.dns,
                url_playlist=playlist.url_playlist,
                codigo=playlist.codigo,
                proteger=playlist.protegida,
                pin=playlist.pin_protecao,
                modo_envio=playlist.modo_envio,
            )

            if not isinstance(resultado, dict):
                raise ValueError("O provedor retornou uma edição inválida.")

            if not resultado.get("success"):
                mensagem = resultado.get("message") or (
                    "Não foi possível atualizar a playlist no aplicativo."
                )
                playlist.status = "erro"
                playlist.ultima_mensagem = mensagem
                playlist.ultima_sincronizacao = timezone.now()
                playlist.save()

                historico.status = "erro"
                historico.mensagem = mensagem
                historico.http_status = resultado.get("http_status")
                historico.resposta_api = resultado
                historico.save()

                return JsonResponse(
                    {"success": False, "message": mensagem},
                    status=400,
                )

            novo_remote_id = str(
                resultado.get("remote_id") or playlist.remote_id
            ).strip()
            playlist.remote_id = novo_remote_id
            playlist.nome_remoto = playlist.nome
            playlist.status = "ativo"
            playlist.encontrada_na_ultima_sync = True
            playlist.ultima_sincronizacao = timezone.now()
            playlist.ultima_mensagem = resultado.get(
                "message",
                "Playlist atualizada no aplicativo.",
            )

            dados_remotos["ultimo_estado_publicado"] = _estado_publicado_playlist(
                playlist
            )
            dados_remotos["ultima_edicao_remota"] = resultado
            playlist.dados_remotos = dados_remotos
            playlist.save()

            historico.status = "sucesso"
            historico.mensagem = playlist.ultima_mensagem
            historico.http_status = resultado.get("http_status")
            historico.resposta_api = resultado
            historico.save()

            return JsonResponse(
                {
                    "success": True,
                    "confirmed": True,
                    "message": playlist.ultima_mensagem,
                    "remote_id": playlist.remote_id,
                    "status": playlist.status,
                    "remote_edit": True,
                }
            )

        remote_id_antigo = str(
            publicado.get("remote_id") or playlist.remote_id or ""
        ).strip()
        protegida_antiga = bool(publicado.get("protegida"))
        pin_antigo = str(
            request.POST.get("pin_atual", "")
            or publicado.get("pin_protecao")
            or ""
        ).strip()

        if protegida_antiga and not pin_antigo:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Informe o PIN atual da playlist remota para excluí-la.",
                },
                status=400,
            )

        resultado_exclusao = provider.excluir_playlist(
            remote_id=remote_id_antigo,
            pin=pin_antigo,
            protegida=protegida_antiga,
        )

        if not isinstance(resultado_exclusao, dict):
            raise ValueError("O provedor retornou uma exclusão inválida.")

        if not resultado_exclusao.get("success"):
            mensagem = resultado_exclusao.get("message") or (
                "Não foi possível excluir a playlist atual."
            )
            return JsonResponse(
                {"success": False, "message": mensagem},
                status=400,
            )

        playlist.remote_id = ""
        playlist.status = "processando"
        playlist.ultima_mensagem = "Versão antiga removida. Cadastrando a nova."
        playlist.save()

        resultado_cadastro = provider.adicionar_playlist(
            nome_playlist=playlist.nome,
            usuario=playlist.usuario_iptv,
            senha=playlist.senha_iptv,
            dns=playlist.dns,
            url_playlist=playlist.url_playlist,
            codigo=playlist.codigo,
            proteger=playlist.protegida,
            pin=playlist.pin_protecao,
            modo_envio=playlist.modo_envio,
        )

        if not isinstance(resultado_cadastro, dict):
            raise ValueError("O provedor retornou um cadastro inválido.")

        if not resultado_cadastro.get("success"):
            mensagem = (
                "A playlist antiga foi removida, mas a nova não pôde ser cadastrada: "
                + str(resultado_cadastro.get("message") or "falha não informada")
            )
            playlist.status = "erro"
            playlist.ultima_mensagem = mensagem
            playlist.ultima_sincronizacao = timezone.now()
            playlist.save()
            return JsonResponse(
                {"success": False, "message": mensagem, "deleted_old": True},
                status=400,
            )

        playlist.remote_id = str(
            resultado_cadastro.get("remote_id") or ""
        ).strip()
        playlist.nome_remoto = playlist.nome
        playlist.status = (
            "ativo"
            if resultado_cadastro.get("confirmed", True)
            else "confirmacao_pendente"
        )
        playlist.encontrada_na_ultima_sync = bool(playlist.remote_id)
        playlist.ultima_sincronizacao = timezone.now()
        playlist.ultima_mensagem = resultado_cadastro.get(
            "message",
            "Playlist substituída com sucesso.",
        )

        dados_remotos["ultimo_estado_publicado"] = _estado_publicado_playlist(
            playlist
        )
        dados_remotos["ultima_substituicao"] = {
            "exclusao": resultado_exclusao,
            "cadastro": resultado_cadastro,
        }
        playlist.dados_remotos = dados_remotos
        playlist.save()

        historico.status = "sucesso"
        historico.mensagem = playlist.ultima_mensagem
        historico.http_status = resultado_cadastro.get("http_status")
        historico.resposta_api = dados_remotos["ultima_substituicao"]
        historico.save()

        return JsonResponse(
            {
                "success": True,
                "confirmed": bool(resultado_cadastro.get("confirmed", True)),
                "message": playlist.ultima_mensagem,
                "remote_id": playlist.remote_id,
                "status": playlist.status,
                "remote_edit": False,
            }
        )

    except Exception as erro:
        logger.exception("Erro ao publicar playlist %s", playlist.id)
        playlist.status = "erro"
        playlist.ultima_mensagem = str(erro)
        playlist.ultima_sincronizacao = timezone.now()
        playlist.save()

        historico.status = "erro"
        historico.mensagem = str(erro)
        historico.save()

        return JsonResponse(
            {"success": False, "message": f"Erro ao publicar playlist: {erro}"},
            status=500,
        )



@login_required
@require_GET
def gerar_captcha_ibo(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)

    if integracao.provedor != "ibo_player":
        return JsonResponse(
            {"success": False, "message": "Esta integração não é do IBO Player."},
            status=400,
        )

    try:
        provider = get_playlist_provider(integracao)
        resultado = provider.gerar_captcha()

        return JsonResponse(
            {
                "success": bool(resultado.get("success")),
                "message": resultado.get("message", "Operação concluída."),
                "svg": resultado.get("svg", ""),
                "token": resultado.get("token", ""),
            },
            status=200 if resultado.get("success") else 400,
        )

    except Exception as erro:
        logger.exception("Erro ao gerar CAPTCHA IBO da integração %s", integracao.id)
        return JsonResponse(
            {"success": False, "message": f"Erro ao gerar CAPTCHA IBO: {erro}"},
            status=500,
        )


@login_required
@require_POST
def autenticar_ibo_playlist(request, integracao_id):
    integracao = _integracao_usuario(request, integracao_id)

    if integracao.provedor != "ibo_player":
        return JsonResponse(
            {"success": False, "message": "Esta integração não é do IBO Player."},
            status=400,
        )

    captcha = str(request.POST.get("captcha", "") or "").strip().upper()
    captcha_token = str(request.POST.get("captcha_token", "") or "").strip()

    if not captcha or not captcha_token:
        return JsonResponse(
            {"success": False, "message": "Informe o CAPTCHA exibido."},
            status=400,
        )

    historico = _registrar_historico(
        integracao,
        "autenticar",
        "processando",
        "Autenticando dispositivo no IBO Player.",
    )

    try:
        provider = get_playlist_provider(integracao)
        resultado = provider.pesquisar_dispositivo(
            captcha=captcha,
            captcha_token=captcha_token,
        )

        sucesso = bool(resultado.get("success"))
        integracao.status = "configurado" if sucesso else "aguardando_captcha"
        integracao.ultima_mensagem = resultado.get(
            "message",
            "Autenticação concluída.",
        )
        integracao.ultima_sincronizacao = timezone.now()
        integracao.save(
            update_fields=[
                "status",
                "ultima_mensagem",
                "ultima_sincronizacao",
                "atualizado_em",
            ]
        )

        historico.status = "sucesso" if sucesso else "erro"
        historico.mensagem = integracao.ultima_mensagem
        historico.http_status = resultado.get("http_status")
        historico.resposta_api = resultado
        historico.save()

        return JsonResponse(
            {
                "success": sucesso,
                "message": integracao.ultima_mensagem,
                "status": integracao.status,
            },
            status=200 if sucesso else 400,
        )

    except Exception as erro:
        logger.exception("Erro ao autenticar IBO da integração %s", integracao.id)
        integracao.status = "erro"
        integracao.ultima_mensagem = str(erro)
        integracao.save(update_fields=["status", "ultima_mensagem", "atualizado_em"])

        historico.status = "erro"
        historico.mensagem = str(erro)
        historico.save()

        return JsonResponse(
            {"success": False, "message": f"Erro ao autenticar IBO: {erro}"},
            status=500,
        )


