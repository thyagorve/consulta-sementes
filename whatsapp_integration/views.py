import json
import requests
import logging
import threading
import re
from datetime import datetime, date, timedelta
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError, close_old_connections
from django.utils import timezone
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.urls import reverse
from django.contrib.sites.models import Site
from django.db.models import Q
from django.middleware.csrf import get_token
from django.db import models

# Importe todos os modelos de uma vez
from clientes.models import CustomUser, Servico, Tag, MensagemConfigurada
from .models import (
    UserInstance,
    HistoricoMensagemAutomatica,
    MensagemMassa,
    HistoricoEnvioMassa
)




from clientes.message_variables import (
    substituir_variaveis_mensagem,
)

logger = logging.getLogger(__name__)

# Variáveis globais
OWNER_USER_TYPES = getattr(settings, 'OWNER_USER_TYPES', ['admin', 'revenda'])
EVOLUTION_API_BASE_URL = getattr(settings, 'EVOLUTION_API_BASE_URL', 'http://localhost:8080')
EVO_HEADERS = getattr(settings, 'EVOLUTION_API_HEADERS', {})
EVOLUTION_API_TIMEOUT_FETCH = getattr(settings, 'EVOLUTION_API_TIMEOUT_FETCH_SECONDS', 15)
EVOLUTION_API_TIMEOUT_CONNECT = getattr(settings, 'EVOLUTION_API_TIMEOUT_CONNECT_SECONDS', 90)

# =============================================
# FUNÇÕES AUXILIARES PARA AVATAR
# =============================================

def _get_user_connected_instance(request):
    """
    Retorna a instância CONECTADA do usuário logado
    ou None se não houver
    """
    try:
        # Primeiro tenta buscar instância CONECTADA
        instance = UserInstance.objects.filter(
            user=request.user,
            status='connected',
            is_active=True
        ).first()
        
        if instance:
            return instance
        
        # Se não tiver conectada, busca qualquer instância ativa
        instance = UserInstance.objects.filter(
            user=request.user,
            is_active=True
        ).first()
        
        return instance
        
    except Exception as e:
        logger.error(f"Erro ao buscar instância: {e}")
        return None

def _validate_user_instance(request):
    """
    Valida se o usuário tem instância configurada e conectada
    Retorna (instância, resposta_de_erro) ou (instância, None)
    """
    instance = _get_user_connected_instance(request)
    
    if not instance:
        return None, JsonResponse({
            'success': False,
            'error': 'Usuário não tem instância WhatsApp configurada',
            'needs_setup': True,
            'setup_url': '/integra/whatsapp/'
        }, status=400)
    
    if instance.status != 'connected':
        return instance, JsonResponse({
            'success': False,
            'error': f'Instância não está conectada (status: {instance.status})',
            'instance_status': instance.status,
            'needs_connection': True,
            'connection_url': '/integra/whatsapp/'
        }, status=400)
    
    return instance, None

def _fetch_avatar_from_evolution_api(request, phone_number, cliente=None):
    """
    Função interna para buscar avatar na API Evolution
    """
    # VALIDAR phone_number
    if not phone_number:
        if cliente:
            cliente.whatsapp_avatar_status = 'error'
            cliente.whatsapp_avatar_error = 'Número de telefone não disponível'
            cliente.save()
        return JsonResponse({
            'success': False,
            'error': 'Número de telefone não disponível',
            'status': 'error'
        }, status=400)
    
    # Garantir que é string
    phone_number = str(phone_number)
    
    # VALIDAR INSTÂNCIA DO USUÁRIO
    instance, error_response = _validate_user_instance(request)
    if error_response:
        return error_response
    
    instance_name = instance.instance_name
    
    # Configurações da API
    EVOLUTION_API_BASE_URL = getattr(settings, 'EVOLUTION_API_BASE_URL', '').rstrip('/')
    EVOLUTION_GLOBAL_API_KEY = getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', '')
    if not EVOLUTION_API_BASE_URL or not EVOLUTION_GLOBAL_API_KEY:
        return JsonResponse({
            'success': False,
            'error': 'Integração Evolution não configurada no servidor.',
            'status': 'error'
        }, status=503)
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'apikey': EVOLUTION_GLOBAL_API_KEY
    }
    
    # Formatar número
    try:
        phone_clean = re.sub(r'\D', '', phone_number)
        
        if not phone_clean:
            if cliente:
                cliente.whatsapp_avatar_status = 'error'
                cliente.whatsapp_avatar_error = 'Número de telefone inválido'
                cliente.save()
            return JsonResponse({
                'success': False,
                'error': 'Número de telefone inválido',
                'status': 'error'
            }, status=400)
            
    except Exception as e:
        if cliente:
            cliente.whatsapp_avatar_status = 'error'
            cliente.whatsapp_avatar_error = f'Erro ao processar número: {str(e)}'
            cliente.save()
        return JsonResponse({
            'success': False,
            'error': f'Erro ao processar número: {str(e)}',
            'status': 'error'
        }, status=400)
    
    # Adicionar código do país se necessário
    if not phone_clean.startswith('55') and len(phone_clean) <= 11:
        phone_clean = f'55{phone_clean}'
    
    logger.info("Buscando avatar para final %s na instância %s", phone_clean[-4:], instance_name)
    
    try:
        # URL da API Evolution
        api_url = f"{EVOLUTION_API_BASE_URL}/chat/fetchProfilePictureUrl/{instance_name}"
        
        payload = {
            "number": phone_clean
        }
        
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            profile_picture_url = data.get('profilePictureUrl')
            
            if profile_picture_url:
                # Atualizar o usuário no banco
                if cliente:
                    cliente.whatsapp_avatar_url = profile_picture_url
                    cliente.whatsapp_avatar_status = 'found'
                    cliente.whatsapp_avatar_updated = timezone.now()
                    cliente.whatsapp_avatar_expires = timezone.now() + timedelta(days=7)
                    cliente.whatsapp_avatar_error = None
                    cliente.save()
                
                return JsonResponse({
                    'success': True,
                    'profilePicture': profile_picture_url,
                    'cached': False,
                    'status': 'found',
                    'instance_used': instance_name
                })
            else:
                if cliente:
                    cliente.whatsapp_avatar_status = 'not_found'
                    cliente.whatsapp_avatar_error = 'Foto não encontrada'
                    cliente.save()
                
                return JsonResponse({
                    'success': False,
                    'status': 'not_found',
                    'message': 'Foto não encontrada para este número'
                }, status=404)
                
        else:
            error_msg = f"Evolution respondeu HTTP {response.status_code}"
            logger.warning("Falha ao buscar avatar. Instância=%s HTTP=%s", instance_name, response.status_code)
            
            if cliente:
                cliente.whatsapp_avatar_status = 'error'
                cliente.whatsapp_avatar_error = error_msg
                cliente.save()
            
            return JsonResponse({
                'success': False,
                'status': 'error',
                'message': error_msg
            }, status=response.status_code)
            
    except requests.exceptions.Timeout:
        error_msg = 'Timeout na comunicação com a API'
        
        if cliente:
            cliente.whatsapp_avatar_status = 'error'
            cliente.whatsapp_avatar_error = error_msg
            cliente.save()
        
        return JsonResponse({
            'success': False,
            'status': 'error',
            'message': 'Timeout ao conectar com a API'
        }, status=408)
        
    except Exception as e:
        error_msg = str(e)
        
        if cliente:
            cliente.whatsapp_avatar_status = 'error'
            cliente.whatsapp_avatar_error = error_msg
            cliente.save()
        
        return JsonResponse({
            'success': False,
            'status': 'error',
            'message': f'Erro interno: {error_msg}'
        }, status=500)

def _get_whatsapp_avatar_internal(request, user_id=None, phone_number=None, cliente=None):
    """
    Função interna para buscar avatar
    """
    # Se cliente foi fornecido, usar direto
    if cliente:
        # Verificar cache primeiro
        if cliente.is_avatar_found():
            return JsonResponse({
                'success': True,
                'profilePicture': cliente.whatsapp_avatar_url,
                'cached': True,
                'status': 'found'
            })
        
        # Buscar na API
        if cliente.whatsapp:
            return _fetch_avatar_from_evolution_api(request, cliente.whatsapp, cliente)
        else:
            return JsonResponse({
                'success': False,
                'error': 'Cliente não tem WhatsApp cadastrado',
                'status': 'no_whatsapp'
            })
    
    # Se temos user_id, buscar cliente
    elif user_id:
        try:
            cliente = CustomUser.objects.get(id=user_id, dono=request.user)
            
            # Verificar cache
            if cliente.is_avatar_found():
                return JsonResponse({
                    'success': True,
                    'profilePicture': cliente.whatsapp_avatar_url,
                    'cached': True,
                    'status': 'found'
                })
            
            # Buscar na API
            if cliente.whatsapp:
                return _fetch_avatar_from_evolution_api(request, cliente.whatsapp, cliente)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Cliente não tem WhatsApp cadastrado',
                    'status': 'no_whatsapp'
                })
                
        except CustomUser.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Cliente não encontrado'
            }, status=404)
    
    # Se temos phone_number
    elif phone_number:
        return _fetch_avatar_from_evolution_api(request, phone_number, None)
    
    # Nenhum parâmetro válido
    else:
        return JsonResponse({
            'success': False,
            'error': 'Parâmetros insuficientes. Forneça user_id ou phone_number.'
        }, status=400)




# =============================================
# VIEWS PARA INSTÂNCIAS WHATSAPP
# =============================================

# =============================================
# VIEWS PARA ENVIO EM MASSA #############################################################################################################
# =============================================

@login_required
def enviar_mensagem_massa(request):
    """
    View principal para envio.
    Agora suporta carregar um rascunho para edição via ?rascunho_id=...
    """
    servicos = Servico.objects.filter(revenda=request.user).distinct().order_by('nome')
    tags = Tag.objects.filter(users__dono=request.user).distinct().order_by('nome')
    tem_instancia = UserInstance.objects.filter(user=request.user, status='connected').exists()
    
    # Datas
    data_minima = (timezone.now() + timezone.timedelta(days=1)).strftime('%Y-%m-%d')
    hoje = timezone.now().strftime('%Y-%m-%d')

    # Listas de Histórico
    rascunhos = MensagemMassa.objects.filter(remetente=request.user, status='rascunho').order_by('-data_criacao')
    agendadas = MensagemMassa.objects.filter(remetente=request.user, status='agendada').order_by('data_agendamento')
    
    # LÓGICA DE EDIÇÃO
    rascunho_atual = None
    tags_pre_selecionadas = "[]"
    
    rascunho_id = request.GET.get('rascunho_id')
    if rascunho_id:
        try:
            rascunho_atual = MensagemMassa.objects.get(id=rascunho_id, remetente=request.user)
            # Prepara as tags para o Javascript
            tags_list = [{'id': t.id, 'nome': t.nome} for t in rascunho_atual.tags_filtro.all()]
            tags_pre_selecionadas = json.dumps(tags_list)
        except MensagemMassa.DoesNotExist:
            pass

    context = {
        'servicos': servicos,
        'tags': tags,
        'hoje': hoje,
        'data_minima': data_minima,
        'tem_instancia': tem_instancia,
        'rascunhos': rascunhos,
        'agendadas': agendadas,
        # Dados para edição
        'rascunho_atual': rascunho_atual,
        'tags_pre_selecionadas': tags_pre_selecionadas
    }
    
    return render(request, 'whatsapp_integration/envio_massa.html', context)

LIMITE_MIDIA_BYTES = 16 * 1024 * 1024


def normalizar_numero(numero):
    numero = re.sub(r'\D', '', str(numero or ''))
    if not numero:
        return ''
    if not numero.startswith('55') and len(numero) in (10, 11):
        numero = f'55{numero}'
    return numero if 12 <= len(numero) <= 15 else ''


def normalizar_numeros_avulsos(texto):
    vistos = set()
    numeros = []
    for item in re.split(r'[\n,;]+', texto or ''):
        numero = normalizar_numero(item)
        if numero and numero not in vistos:
            vistos.add(numero)
            numeros.append(numero)
    return numeros


def ler_ids_clientes(request):
    try:
        dados = json.loads(request.POST.get('clientes_ids', '[]'))
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(dados, list):
        return []
    return [int(item) for item in dados if str(item).isdigit()]


def filtrar_clientes_do_request(request):
    modo = request.POST.get('modo_destinatarios', 'clientes')
    if modo == 'avulsos':
        return []

    ids = ler_ids_clientes(request)
    queryset = CustomUser.objects.filter(dono=request.user)

    if ids:
        return list(queryset.filter(id__in=ids).distinct())

    status = request.POST.get('status', '')
    plano_id = request.POST.get('plano', '')
    dias_vencido = request.POST.get('dias_vencido', '')
    tags = request.POST.getlist('tags[]')
    hoje = timezone.localdate()

    if status == 'ativos':
        queryset = queryset.filter(is_active=True, data_vencimento__gte=hoje)
    elif status == 'vencidos':
        queryset = queryset.filter(is_active=True, data_vencimento__lt=hoje)
        if dias_vencido.isdigit():
            queryset = queryset.filter(
                data_vencimento__lte=hoje - timedelta(days=int(dias_vencido))
            )
    elif status == 'desativados':
        queryset = queryset.filter(is_active=False)

    if plano_id.isdigit():
        queryset = queryset.filter(plano_id=int(plano_id))

    tag_ids = [int(tag) for tag in tags if str(tag).isdigit()]
    if tag_ids:
        queryset = queryset.filter(tags__id__in=tag_ids).distinct()

    return list(queryset)


def obter_data_agendamento(request):
    if request.POST.get('agendamento') != 'horario':
        return None

    data_str = request.POST.get('data_agendamento', '').strip()
    hora_str = request.POST.get('hora_agendamento', '').strip() or request.POST.get('hora_agendada', '').strip()
    if not data_str or not hora_str:
        raise ValueError('Informe a data e o horário do envio.')

    data = datetime.strptime(f'{data_str} {hora_str}', '%Y-%m-%d %H:%M')
    data = timezone.make_aware(data, timezone.get_current_timezone())
    if data <= timezone.now():
        raise ValueError('A data de agendamento precisa estar no futuro.')
    return data


def preparar_destinatarios(mensagem):
    destinatarios = []
    numeros_usados = set()

    if mensagem.modo_destinatarios in ('clientes', 'ambos'):
        for cliente in mensagem.clientes.all():
            numero = normalizar_numero(
                cliente.whatsapp
                or getattr(cliente, 'telefone', '')
                or getattr(cliente, 'numero', '')
            )
            if numero and numero not in numeros_usados:
                numeros_usados.add(numero)
                destinatarios.append({'cliente': cliente, 'numero': numero})

    if mensagem.modo_destinatarios in ('avulsos', 'ambos'):
        for numero in normalizar_numeros_avulsos(mensagem.numeros_avulsos):
            if numero not in numeros_usados:
                numeros_usados.add(numero)
                destinatarios.append({'cliente': None, 'numero': numero})

    return destinatarios


def garantir_historicos_pendentes(mensagem):
    """Cria uma fila persistente de destinatários para campanhas agendadas.

    O comando ``processar_envio_massa`` consome essa fila. A criação é
    idempotente por campanha+número para evitar duplicidade quando uma
    campanha é retomada.
    """
    criados = 0
    for destinatario in preparar_destinatarios(mensagem):
        cliente = destinatario['cliente']
        numero = destinatario['numero']
        texto = (
            substituir_variaveis_mensagem(mensagem.mensagem, cliente)
            if cliente else mensagem.mensagem
        )
        historico, criado = HistoricoEnvioMassa.objects.get_or_create(
            mensagem_massa=mensagem,
            whatsapp=numero,
            defaults={
                'cliente': cliente,
                'mensagem_final': texto,
                'status': 'pendente',
            },
        )
        if criado:
            criados += 1
        elif historico.status == 'pendente':
            campos = []
            if historico.cliente_id != (cliente.id if cliente else None):
                historico.cliente = cliente
                campos.append('cliente')
            if historico.mensagem_final != texto:
                historico.mensagem_final = texto
                campos.append('mensagem_final')
            if campos:
                historico.save(update_fields=campos)
    return criados


def _processar_envio_massa_em_background(campanha_id):
    """Executa o management command em uma thread do processo web.

    A campanha e seus destinatários já estão persistidos no banco. Se o processo
    web reiniciar, o agendador pode retomar os itens pendentes depois. Usar uma
    thread aqui evita diferenças de subprocesso entre Windows/Linux e mantém os
    erros no logger do Django em vez de descartá-los em DEVNULL.
    """
    close_old_connections()
    try:
        call_command('processar_envio_massa', campanha_id=campanha_id)
    except Exception:
        logger.exception('Falha no processador imediato da campanha %s', campanha_id)
        try:
            campanha = MensagemMassa.objects.filter(id=campanha_id).first()
            if campanha and campanha.status not in ('concluida', 'cancelada', 'falha'):
                campanha.status = 'falha'
                campanha.data_envio_fim = timezone.now()
                campanha.save(update_fields=['status', 'data_envio_fim'])
                campanha.historicos.filter(status='pendente').update(
                    status='falha',
                    mensagem_erro='O processador imediato encontrou um erro interno. Consulte o log do servidor.',
                )
        except Exception:
            logger.exception('Falha ao registrar erro da campanha %s', campanha_id)
    finally:
        close_old_connections()


@require_POST
@login_required
def api_filter_clients(request):
    clientes = filtrar_clientes_do_request(request)
    return JsonResponse({
        'success': True,
        'count': len(clientes),
        'clientes': [
            {
                'id': cliente.id,
                'nome': cliente.nome,
                'whatsapp': cliente.whatsapp or getattr(cliente, 'telefone', '') or '',
            }
            for cliente in clientes
        ],
    })


def criar_mensagem_do_request(request, status_inicial):
    texto = request.POST.get('mensagem', '').strip()
    if not texto:
        raise ValueError('Escreva a mensagem.')

    modo = request.POST.get('modo_destinatarios', 'clientes')
    if modo not in ('clientes', 'avulsos', 'ambos'):
        modo = 'clientes'

    clientes = filtrar_clientes_do_request(request)
    avulsos = normalizar_numeros_avulsos(request.POST.get('numeros_avulsos', ''))

    if modo == 'clientes':
        avulsos = []
    elif modo == 'avulsos':
        clientes = []

    if not clientes and not avulsos:
        raise ValueError('Nenhum destinatário foi selecionado.')

    data_agendamento = obter_data_agendamento(request)
    arquivo = request.FILES.get('midia')
    if arquivo and arquivo.size > LIMITE_MIDIA_BYTES:
        raise ValueError('O anexo ultrapassa 16 MB.')

    mensagem = MensagemMassa.objects.create(
        remetente=request.user,
        mensagem=texto,
        modo_destinatarios=modo,
        plano_filtro_id=request.POST.get('plano') or None,
        status_filtro=request.POST.get('status', ''),
        dias_vencido_filtro=(
            int(request.POST['dias_vencido'])
            if request.POST.get('dias_vencido', '').isdigit()
            else None
        ),
        numeros_avulsos='\n'.join(avulsos),
        data_agendamento=data_agendamento,
        agendada=bool(data_agendamento),
        midia=arquivo,
        tipo_midia=(arquivo.content_type if arquivo else ''),
        total_destinatarios=len(clientes) + len(avulsos),
        status=status_inicial,
    )
    mensagem.clientes.set(clientes)

    tag_ids = [int(tag) for tag in request.POST.getlist('tags[]') if str(tag).isdigit()]
    if tag_ids:
        tags_permitidas = Tag.objects.filter(
            Q(usuario=request.user) | Q(usuario__isnull=True),
            id__in=tag_ids,
        )
        mensagem.tags_filtro.set(tags_permitidas)

    # Campanhas agendadas precisam da fila persistida, pois o comando de
    # processamento trabalha sobre HistoricoEnvioMassa.
    if status_inicial == 'agendada' and data_agendamento:
        garantir_historicos_pendentes(mensagem)
        mensagem.total_destinatarios = mensagem.historicos.count()
        mensagem.save(update_fields=['total_destinatarios'])

    return mensagem


@require_POST
@login_required
@transaction.atomic
def api_save_mass_message(request):
    try:
        mensagem = criar_mensagem_do_request(request, 'rascunho')
        return JsonResponse({
            'success': True,
            'message': f'Rascunho salvo com {mensagem.total_destinatarios} destinatário(s).',
            'mensagem_id': mensagem.id,
        })
    except ValueError as erro:
        return JsonResponse({'success': False, 'message': str(erro)}, status=400)
    except Exception:
        logger.exception('Erro ao salvar campanha de envio em massa')
        return JsonResponse({'success': False, 'message': 'Não foi possível salvar a campanha.'}, status=500)


@require_POST
@login_required
def api_send_mass_message(request):
    """Agenda uma campanha ou dispara o processador imediatamente."""
    try:
        envio_programado = request.POST.get('agendamento') == 'horario'
        with transaction.atomic():
            mensagem = criar_mensagem_do_request(request, 'agendada')

            if not envio_programado:
                mensagem.data_agendamento = timezone.now()
                mensagem.agendada = True
                mensagem.status = 'agendada'
                mensagem.save(update_fields=['data_agendamento', 'agendada', 'status'])

            garantir_historicos_pendentes(mensagem)
            mensagem.total_destinatarios = mensagem.historicos.count()
            mensagem.save(update_fields=['total_destinatarios'])

        # A transação já foi confirmada aqui. O processo filho consegue enxergar
        # a campanha imediatamente, inclusive em PostgreSQL.
        if envio_programado:
            return JsonResponse({
                'success': True,
                'queued': True,
                'message': f'Campanha agendada para {timezone.localtime(mensagem.data_agendamento):%d/%m/%Y às %H:%M}.',
                'mensagem_id': mensagem.id,
                'total_destinatarios': mensagem.total_destinatarios,
            })

        # O clique em "Enviar agora" acorda o mesmo processador usado pelo
        # agendamento, mas dentro de uma thread controlada pelo Django. Isso funciona
        # da mesma forma no Windows e no Linux e preserva os logs de erro.
        try:
            worker = threading.Thread(
                target=_processar_envio_massa_em_background,
                args=(mensagem.id,),
                name=f'envio-massa-{mensagem.id}',
                daemon=True,
            )
            worker.start()
        except Exception:
            logger.exception('Falha ao iniciar thread da campanha %s', mensagem.id)
            mensagem.status = 'falha'
            mensagem.data_envio_fim = timezone.now()
            mensagem.save(update_fields=['status', 'data_envio_fim'])
            mensagem.historicos.filter(status='pendente').update(
                status='falha',
                mensagem_erro='Não foi possível iniciar o processador de envio imediato.',
            )
            return JsonResponse({
                'success': False,
                'message': 'Não foi possível iniciar o envio imediato no servidor.',
                'mensagem_id': mensagem.id,
            }, status=500)

        return JsonResponse({
            'success': True,
            'queued': True,
            'processing': True,
            'message': 'Processador iniciado. Acompanhe o status desta campanha.',
            'mensagem_id': mensagem.id,
            'total_destinatarios': mensagem.total_destinatarios,
        })
    except ValueError as erro:
        return JsonResponse({'success': False, 'message': str(erro)}, status=400)
    except Exception:
        logger.exception('Erro ao preparar envio em massa')
        return JsonResponse({'success': False, 'message': 'Erro interno ao preparar o envio.'}, status=500)


@login_required
def api_mass_message_status(request, mensagem_id):
    mensagem = get_object_or_404(MensagemMassa, id=mensagem_id, remetente=request.user)
    total = mensagem.historicos.count()
    falhas_qs = mensagem.historicos.filter(status='falha')
    ultimo_erro = (
        falhas_qs.exclude(mensagem_erro='').values_list('mensagem_erro', flat=True).first()
        or ''
    )
    erros = list(
        falhas_qs.exclude(mensagem_erro='')
        .select_related('cliente')
        .values('whatsapp', 'mensagem_erro', 'cliente__nome')[:5]
    )
    return JsonResponse({
        'success': True,
        'mensagem_id': mensagem.id,
        'status': mensagem.status,
        'total': total,
        'enviados': mensagem.historicos.filter(status__in=['enviado', 'entregue', 'lido']).count(),
        'falhas': falhas_qs.count(),
        'pendentes': mensagem.historicos.filter(status='pendente').count(),
        'message': ultimo_erro,
        'erros': erros,
    })


@login_required
def lista_mensagens_massa(request):
    """Lista todos os envios"""
    mensagens = MensagemMassa.objects.filter(remetente=request.user).order_by('-data_criacao')
    paginator = Paginator(mensagens, 20)
    page = request.GET.get('page')
    mensagens_pag = paginator.get_page(page)
    
    return render(request, 'whatsapp_integration/lista_mensagens_massa.html', {
        'mensagens': mensagens_pag
    })

@login_required
def detalhe_mensagem_massa(request, mensagem_id):
    """Detalhes do envio e histórico"""
    mensagem = get_object_or_404(MensagemMassa, id=mensagem_id, remetente=request.user)
    
    # Filtros
    historicos = mensagem.historicos.all().select_related('cliente').order_by('cliente__nome')
    
    search = request.GET.get('search')
    if search:
        historicos = historicos.filter(
            Q(cliente__nome__icontains=search) | Q(whatsapp__icontains=search)
        )

    # Paginação
    paginator = Paginator(historicos, 50)
    page = request.GET.get('page')
    try:
        historicos_pag = paginator.page(page)
    except PageNotAnInteger:
        historicos_pag = paginator.page(1)
    except EmptyPage:
        historicos_pag = paginator.page(paginator.num_pages)

    # Estatísticas
    stats = {
        'total': historicos.count(),
        'pendente': historicos.filter(status='pendente').count(),
        'enviado': historicos.filter(status='enviado').count(),
        'entregue': historicos.filter(status='entregue').count(),
        'lido': historicos.filter(status='lido').count(),
        'falha': historicos.filter(status='falha').count(),
    }

    # VARIÁVEIS DISPONÍVEIS
    variaveis = [
        {'nome': 'nome', 'descricao': 'Primeiro nome do cliente'},
        {'nome': 'nome_completo', 'descricao': 'Nome completo'},
        {'nome': 'whatsapp', 'descricao': 'Número do WhatsApp'},
        {'nome': 'plano', 'descricao': 'Nome do Plano/Serviço'},
        {'nome': 'data_vencimento', 'descricao': 'Data de Vencimento (DD/MM/AAAA)'},
        {'nome': 'valor_servico', 'descricao': 'Valor do Plano (R$)'},
        {'nome': 'usuario', 'descricao': 'Login/Usuário do sistema'},
        {'nome': 'senha', 'descricao': 'Senha do cliente'},
        {'nome': 'email', 'descricao': 'E-mail cadastrado'},
        {'nome': 'telefone', 'descricao': 'Telefone secundário'},
        {'nome': 'notas', 'descricao': 'Anotações do cliente'},
    ]

    return render(request, 'whatsapp_integration/detalhe_mensagem_massa.html', {
        'mensagem': mensagem,
        'historicos': historicos_pag,
        'stats_hist': stats,
        'variaveis': variaveis,
        'search_term': search
    })

@login_required
def cancelar_mensagem_massa(request, mensagem_id):
    msg = get_object_or_404(MensagemMassa, id=mensagem_id, remetente=request.user)
    if msg.status in ['agendada', 'rascunho']:
        msg.status = 'cancelada'
        msg.save()
    return redirect('integra:detalhe_mensagem_massa', mensagem_id=mensagem_id)

@login_required
def reenviar_mensagem_massa(request, mensagem_id):
    msg = get_object_or_404(MensagemMassa, id=mensagem_id, remetente=request.user)
    msg.status = 'agendada'
    msg.enviados_com_falha = 0
    msg.enviados_com_sucesso = 0
    msg.save()
    msg.historicos.update(status='pendente')
    return redirect('integra:detalhe_mensagem_massa', mensagem_id=mensagem_id)

@login_required
def duplicar_mensagem_massa(request, mensagem_id):
    """Duplica uma mensagem existente"""
    original = get_object_or_404(MensagemMassa, id=mensagem_id, remetente=request.user)
    
    nova = MensagemMassa.objects.create(
        remetente=request.user,
        mensagem=original.mensagem,
        data_agendamento=timezone.now(),
        status='rascunho',
        plano_filtro=original.plano_filtro,
        status_filtro=original.status_filtro
    )
    
    return redirect('integra:detalhe_mensagem_massa', mensagem_id=nova.id)

# =============================================
# VIEWS PARA HISTÓRICO DE MENSAGENS
# =============================================

@login_required
def historico_mensagens_view(request):
    """
    Exibe o histórico de mensagens automáticas.
    """
    User = get_user_model()
    user_tipo_usuario = getattr(request.user, 'tipo_usuario', None)
    
    # Determina se tem permissão para ações administrativas (excluir)
    is_owner_or_staff = (
        request.user.is_superuser or 
        request.user.is_staff or 
        (user_tipo_usuario in OWNER_USER_TYPES)
    )

    ctx = {
        'mensagens': [],
        'error_message': None,
        'is_owner_or_staff': is_owner_or_staff
    }

    try:
        # LÓGICA DE FILTRO
        if request.user.is_superuser:
            historico_list = HistoricoMensagemAutomatica.objects.all()
            
        elif user_tipo_usuario == 'cliente' or not hasattr(User, 'dono'):
            historico_list = HistoricoMensagemAutomatica.objects.filter(cliente=request.user)
            
        else:
            managed_clients_ids = User.objects.filter(dono=request.user).values_list('id', flat=True)
            historico_list = HistoricoMensagemAutomatica.objects.filter(cliente__id__in=managed_clients_ids)

        # Ordenação
        if hasattr(HistoricoMensagemAutomatica, 'data_tentativa'):
            historico_list = historico_list.order_by('-data_tentativa')
        elif hasattr(HistoricoMensagemAutomatica, 'data_envio'):
            historico_list = historico_list.order_by('-data_envio')
        else:
            historico_list = historico_list.order_by('-id')

        historico_list = historico_list.select_related('cliente', 'mensagem_configurada')
        ctx['mensagens'] = historico_list

    except Exception as e:
        logger.error(f"Erro crítico ao buscar histórico para {request.user.username}: {e}", exc_info=True)
        ctx['error_message'] = "Não foi possível carregar o histórico no momento."

    return render(request, 'whatsapp_integration/historico_mensagens.html', ctx)

@require_POST
@login_required
def remover_historico_mensagem_view(request, pk):
    """
    Remove um registro de histórico de mensagem com verificação de permissão.
    """
    try:
        historico_item = get_object_or_404(HistoricoMensagemAutomatica, pk=pk)
        User = get_user_model()
        can_delete = False
        user_tipo = getattr(request.user, 'tipo_usuario', None)

        client_owner = historico_item.cliente if hasattr(historico_item, 'cliente') else None

        if client_owner and request.user == client_owner:
            can_delete = True
        elif request.user.is_staff or request.user.is_superuser:
            can_delete = True
        elif user_tipo in OWNER_USER_TYPES and client_owner:
            if hasattr(User, 'dono'):
                try:
                    if User.objects.filter(pk=client_owner.pk, dono=request.user).exists():
                        can_delete = True
                except Exception as e:
                    logger.error(f"Error checking owner management for delete of history {pk}: {e}", exc_info=True)

        if not can_delete:
            logger.warning(f"User {request.user.username} denied permission to remove history ID {pk}")
            return JsonResponse({'success': False, 'message': 'Você não tem permissão para remover este registro.'}, status=403)

        logger.info(f"User {request.user.username} has permission. Attempting deletion of history ID {pk}.")
        try:
            with transaction.atomic():
                historico_item.delete()
                logger.info(f"History record ID {pk} successfully removed by user {request.user.username}.");
            return JsonResponse({'success': True, 'message': 'Registro de histórico removido com sucesso!'}, status=200)
        except Exception as e:
            logger.error(f"Error during history deletion (ID {pk}) by user {request.user.username}: {e}", exc_info=True);
            return JsonResponse({'success': False, 'message': f'Erro interno ao remover registro: {e}'}, status=500)

    except Http404:
        logger.warning(f"History record ID {pk} not found for removal by user {request.user.username}.")
        return JsonResponse({'success': False, 'message': 'Registro não encontrado.'}, status=404)
    except Exception as e:
        logger.critical(f"UNCAUGHT EXCEPTION processing history remove for ID {pk} by user {request.user.username}: {e}", exc_info=True);
        return JsonResponse({'success': False, 'message': f'Erro interno inesperado: {e}'}, status=500)

@login_required
@require_POST
def remover_todo_historico_view(request):
    """
    API AJAX para limpar todo o histórico VISÍVEL para o usuário.
    """
    try:
        user_tipo_usuario = getattr(request.user, 'tipo_usuario', None)
        
        if not (request.user.is_superuser or request.user.is_staff or user_tipo_usuario in OWNER_USER_TYPES):
             return JsonResponse({'success': False, 'message': 'Apenas administradores podem limpar o histórico.'}, status=403)

        count = 0
        if request.user.is_superuser:
            count, _ = HistoricoMensagemAutomatica.objects.all().delete()
        else:
            User = get_user_model()
            managed_clients_ids = User.objects.filter(dono=request.user).values_list('id', flat=True)
            count, _ = HistoricoMensagemAutomatica.objects.filter(cliente__id__in=managed_clients_ids).delete()
            
        return JsonResponse({'success': True, 'message': f'{count} registros excluídos.'})

    except Exception as e:
        logger.error(f"Erro ao limpar histórico: {e}")
        return JsonResponse({'success': False, 'message': 'Erro interno ao processar a solicitação.'}, status=500)

# =============================================
# VIEWS PARA AVATAR WHATSAPP
# =============================================

@require_GET
@login_required
def get_whatsapp_avatar(request, phone_number):
    """
    View pública para buscar avatar por número de telefone
    """
    return _get_whatsapp_avatar_internal(request, phone_number=phone_number)

@require_GET
@login_required
def get_user_avatar(request, user_id):
    try:
        cliente = CustomUser.objects.get(id=user_id, dono=request.user)
        
        # Verificar se tem WhatsApp
        if not cliente.whatsapp:
            return JsonResponse({
                'success': False,
                'status': 'no_whatsapp',
                'message': 'Cliente não tem WhatsApp cadastrado'
            })
        
        # Verificar se tem avatar válido
        if cliente.is_avatar_found():
            return JsonResponse({
                'success': True,
                'profilePicture': cliente.whatsapp_avatar_url,
                'cached': True,
                'status': 'found'
            })
        
        # Verificar status
        return JsonResponse({
            'success': True,
            'status': cliente.whatsapp_avatar_status,
            'message': cliente.whatsapp_avatar_error or 'Avatar não carregado',
            'has_whatsapp': bool(cliente.whatsapp)
        })
        
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente não encontrado ou sem permissão'
        }, status=404)

@require_POST
@login_required
def refresh_user_avatar(request, user_id):
    try:
        cliente = CustomUser.objects.get(id=user_id, dono=request.user)
        
        if not cliente.whatsapp:
            return JsonResponse({
                'success': False,
                'error': 'Cliente não tem WhatsApp cadastrado',
                'status': 'no_whatsapp'
            })
        
        # Limpar cache antigo
        cliente.whatsapp_avatar_url = None
        cliente.whatsapp_avatar_status = 'pending'
        cliente.whatsapp_avatar_error = None
        cliente.save()
        
        # Buscar novo avatar
        return _get_whatsapp_avatar_internal(request, user_id=user_id, cliente=cliente)
        
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente não encontrado'
        }, status=404)

@require_GET
@login_required
def check_avatar_status(request, user_id):
    try:
        cliente = CustomUser.objects.get(id=user_id, dono=request.user)
        
        # Verificar instância do usuário
        instance = _get_user_connected_instance(request)
        
        return JsonResponse({
            'success': True,
            'has_avatar': cliente.is_avatar_found(),
            'status': cliente.whatsapp_avatar_status,
            'is_valid': cliente.is_avatar_valid(),
            'has_whatsapp': bool(cliente.whatsapp),
            'instance_status': instance.status if instance else 'no_instance',
            'needs_instance': not instance or instance.status != 'connected'
        })
        
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente não encontrado'
        }, status=404)

@require_POST
@login_required
def clear_user_avatar(request, user_id):
    try:
        cliente = CustomUser.objects.get(id=user_id, dono=request.user)
        
        # Limpar todos os campos de avatar
        cliente.whatsapp_avatar_url = None
        cliente.whatsapp_avatar_base64 = None
        cliente.whatsapp_avatar_status = 'pending'
        cliente.whatsapp_avatar_error = None
        cliente.whatsapp_avatar_updated = None
        cliente.whatsapp_avatar_expires = None
        cliente.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cache do avatar limpo com sucesso'
        })
        
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cliente não encontrado ou sem permissão'
        }, status=404)

@require_GET
@login_required
def batch_check_avatars(request):
    try:
        clientes = CustomUser.objects.filter(dono=request.user)
        
        # Verificar instância do usuário
        instance = _get_user_connected_instance(request)
        
        avatars_data = []
        for cliente in clientes:
            avatars_data.append({
                'id': cliente.id,
                'nome': cliente.nome,
                'whatsapp': cliente.whatsapp,
                'has_avatar': cliente.is_avatar_found(),
                'status': cliente.whatsapp_avatar_status,
                'is_valid': cliente.is_avatar_valid(),
                'needs_instance': not instance or instance.status != 'connected'
            })
        
        return JsonResponse({
            'success': True,
            'count': len(avatars_data),
            'avatars': avatars_data,
            'instance_status': instance.status if instance else 'no_instance',
            'has_connected_instance': instance and instance.status == 'connected'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Erro interno ao processar a solicitação.'
        }, status=500)

# =============================================
# OUTRAS VIEWS
# =============================================

@login_required
def whatsapp_dashboard(request):
    # Busca do banco
    instances_query = UserInstance.objects.filter(user=request.user).order_by('-created_at')
    
    # Processa dados básicos para o template
    instances = []
    for instance in instances_query:
        instances.append({
            'id': instance.id,
            'instance_name': instance.instance_name,
            'status': instance.status,
            'profile_name': instance.profile_name,
            'owner_jid': instance.owner_jid,
            'last_check': instance.last_check,
            'created_at': instance.created_at,
        })

    context = {
        'user': request.user,
        'page_title': 'Conexão WhatsApp',
        'instances': instances, 
        'max_instances': 999 if (request.user.is_staff or request.user.is_superuser) else 1,
        'csrf_token': get_token(request),
    }
    
    return render(request, 'whatsapp_integration/connection.html', context)

@login_required
def configurar_instancia(request):
    return render(request, 'whatsapp_integration/connection.html')

@login_required
def minhas_instancias(request):
    """
    Lista as instâncias de WhatsApp do usuário
    """
    instancias = UserInstance.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    return render(request, 'whatsapp_integration/instancias.html', {
        'instancias': instancias
    })

@login_required
@require_http_methods(["GET"])
def legacy_manage_view(request):
    """View legada para compatibilidade"""
    return JsonResponse({
        'status': 'deprecated',
        'message': 'Esta endpoint está obsoleta. Use a nova API REST.',
        'api_endpoints': {
            'list_instances': '/whatsapp/api/instances/',
            'create_instance': '/whatsapp/api/instances/ (POST)',
            'connect': '/whatsapp/api/instances/{id}/connect/',
            'status': '/whatsapp/api/instances/{id}/status/'
        }
    }, status=410)



# No whatsapp_integration/views.py
# Esta é a função PRINCIPAL que deve ser usada

@login_required
def get_whatsapp_avatar_api(request, user_id=None, phone_number=None):
    """
    Função UNIFICADA para buscar avatar
    Usada por todas as outras views
    """
    from django.conf import settings
    
    try:
        # Determina o número a buscar
        if user_id:
            cliente = CustomUser.objects.get(id=user_id)
            phone_number = cliente.whatsapp
        
        if not phone_number:
            return JsonResponse({
                'success': False,
                'error': 'Número não fornecido'
            }, status=400)
        
        # Limpa e formata
        numero_limpo = re.sub(r'\D', '', str(phone_number))
        
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
        
        # Configurações da API
        BASE_URL = settings.EVOLUTION_API_BASE_URL.rstrip('/')
        API_KEY = settings.EVOLUTION_GLOBAL_API_KEY
        
        headers = {
            'apikey': API_KEY,
            'Content-Type': 'application/json'
        }
        
        # URL da API Evolution
        url = f"{BASE_URL}/chat/fetchProfilePictureUrl/gestor"
        
        payload = {"number": formatted_number}
        
        logger.info(f"📸 Avatar API: {url} - {formatted_number}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            profile_pic = data.get('profilePictureUrl')
            
            if profile_pic:
                return JsonResponse({
                    'success': True,
                    'profilePicture': profile_pic
                })
        
        return JsonResponse({
            'success': False,
            'message': 'Foto não encontrada'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro avatar: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Erro interno ao processar a solicitação.'
        }, status=500)
    


@login_required
def ai_manager_view(request):
    """Página de gerenciamento da IA - Redireciona conforme perfil"""
    user = request.user
    is_admin = user.is_staff or user.is_superuser or getattr(user, 'tipo_usuario', '') == 'admin'
    
    if is_admin:
        template = 'whatsapp_integration/ai_manager_admin.html'
    else:
        template = 'whatsapp_integration/ai_manager.html'
    
    return render(request, template, {
        'csrf_token': get_token(request),
        'user': user,
        'is_admin': is_admin,
    })


@csrf_exempt
@require_POST
def evolution_direct_webhook_view(request):
    """Alias legado do webhook unificado. Mantém URLs antigas sem duplicar lógica."""
    from .webhook_handler import webhook_receiver
    return webhook_receiver(request)

