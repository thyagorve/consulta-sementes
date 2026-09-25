# whatsapp_integration/api/views.py

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone
import json
import re
import logging
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()  # Isso pega o modelo de usuário correto
from whatsapp_integration.models import (
    AIConfig, 
    AIClientSettings, 
    AIConversation, 
    AIQuickReply,
    AIRevendaSettings
)

# Certifique-se que o caminho dos imports está correto para o seu projeto
from whatsapp_integration.models import UserInstance
from whatsapp_integration.services.evolution_service import evolution_service

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class LoginRequiredMixin:
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    

logger = logging.getLogger(__name__)

@method_decorator(csrf_protect, name='dispatch')
class InstanceAPIView(APIView):
    """API para gerenciar instâncias WhatsApp"""
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Lista todas as instâncias do usuário"""
        try:
            instances = UserInstance.objects.filter(
                user=request.user, 
                is_active=True
            ).order_by('-created_at')
            
            instances_data = []
            for instance in instances:
                # Dados base do banco
                data = {
                    'id': instance.id,
                    'instance_name': instance.instance_name,
                    'status': instance.status,
                    'display_status': instance.display_status,
                    'profile_name': instance.profile_name,
                    'profile_pic_url': instance.profile_pic_url,
                    'last_check': instance.last_check.isoformat() if instance.last_check else None,
                    'created_at': instance.created_at.isoformat() if instance.created_at else None,
                    'can_connect': instance.can_connect(request.user),
                    'can_delete': instance.can_delete(request.user),
                    'qr_expired': False,
                    'owner_jid': instance.owner_jid
                }

                # Tenta sincronizar com a Evolution (se falhar, não quebra a lista)
                try:
                    if instance.status in ['connected', 'scanning_qr']:
                        api_info = evolution_service.get_connection_info(instance.instance_name)
                        
                        if api_info.get('connected'):
                            instance.mark_as_connected(
                                profile_name=api_info.get('profile_name'),
                                profile_pic_url=api_info.get('profile_pic_url'),
                                owner_jid=api_info.get('owner_jid')
                            )
                            data['status'] = 'connected'
                            data['display_status'] = 'Conectado'
                            data['profile_name'] = api_info.get('profile_name')
                        
                        elif instance.status == 'scanning_qr':
                            if instance.qr_expired():
                                instance.mark_as_disconnected()
                                data['status'] = 'disconnected'
                                data['qr_expired'] = True
                except Exception as e:
                    logger.warning(f"Erro ao sincronizar instância {instance.id}: {e}")
                
                instances_data.append(data)
            
            return Response({
                'success': True,
                'instances': instances_data
            })
            
        except Exception as e:
            logger.error(f"Erro ao listar instâncias: {str(e)}")
            return Response({
                'success': False,
                'error': 'Erro interno ao processar a solicitação.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Cria uma nova instância"""
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
            
            instance_name = data.get('instance_name', '').strip()
            
            if not instance_name:
                return Response({'success': False, 'error': 'Nome obrigatório'}, status=400)
            
            if UserInstance.objects.filter(instance_name=instance_name).exists():
                return Response({'success': False, 'error': 'Nome já existe'}, status=400)
            
            if not all(c.isalnum() or c == '_' for c in instance_name):
                return Response({'success': False, 'error': 'Apenas letras e números'}, status=400)
            
            # Cria na Evolution API
            try:
                evolution_service.create_instance(instance_name)
            except Exception as e:
                logger.error(f"Erro Evolution Create: {e}")
                return Response({'success': False, 'error': 'Não foi possível comunicar com a Evolution API.'}, status=502)
            
            # Salva no Banco
            instance = UserInstance.objects.create(
                user=request.user,
                instance_name=instance_name,
                status='created'
            )
            
            return Response({
                'success': True,
                'message': 'Instância criada!',
                'instance': {'id': instance.id, 'instance_name': instance.instance_name}
            })
            
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)

@method_decorator(csrf_protect, name='dispatch')
class InstanceDetailAPIView(APIView):
    """API para deletar instância"""
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, instance_id):
        try:
            instance = UserInstance.objects.get(id=instance_id, user=request.user)
            try:
                evolution_service.delete_instance(instance.instance_name)
            except Exception:
                pass
            instance.delete()
            return Response({'success': True, 'message': 'Deletado'})
        except UserInstance.DoesNotExist:
            return Response({'success': False, 'error': 'Não encontrado'}, status=404)
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)

@method_decorator(csrf_protect, name='dispatch')
class ConnectionAPIView(APIView):
    """API para conectar/desconectar"""
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, instance_id):
        try:
            instance = get_object_or_404(UserInstance, id=instance_id, user=request.user)
            
            # PRIMEIRO: Verifica se já está conectado
            try:
                api_info = evolution_service.get_connection_info(instance.instance_name)
                
                # Se já está conectado, atualiza e retorna
                if api_info.get('connected'):
                    instance.mark_as_connected(
                        profile_name=api_info.get('profile_name'),
                        profile_pic_url=api_info.get('profile_pic_url'),
                        owner_jid=api_info.get('owner_jid')
                    )
                    return Response({
                        'success': True,
                        'status': 'connected',
                        'message': 'Já está conectado',
                        'connected': True
                    })
            except Exception as e:
                logger.warning(f"Erro ao verificar conexão: {e}")
                # Continua para gerar QR
            
            # SEGUNDO: solicita QR Code ou código de pareamento.
            try:
                phone_number = ""
                try:
                    phone_number = str(request.data.get("phone_number") or "")
                except Exception:
                    phone_number = str(request.POST.get("phone_number") or "")
                phone_number = re.sub(r"\D", "", phone_number)
                if phone_number and not phone_number.startswith("55") and len(phone_number) in (10, 11):
                    phone_number = f"55{phone_number}"
                if phone_number and not 12 <= len(phone_number) <= 15:
                    return Response({
                        "success": False,
                        "error": "Número inválido para código de pareamento.",
                    }, status=400)

                connect_response = evolution_service.generate_qr_code(
                    instance.instance_name,
                    phone_number=phone_number or None,
                )

                qr_data = None
                pairing_code = None
                if isinstance(connect_response, dict):
                    qr_data = (
                        connect_response.get("base64")
                        or connect_response.get("qr")
                        or connect_response.get("qrcode")
                        or connect_response.get("base64QRCode")
                    )
                    pairing_code = (
                        connect_response.get("pairingCode")
                        or connect_response.get("pairing_code")
                    )

                if not qr_data and not pairing_code:
                    api_info = evolution_service.get_connection_info(instance.instance_name)
                    if api_info.get("connected"):
                        instance.mark_as_connected(
                            profile_name=api_info.get("profile_name"),
                            profile_pic_url=api_info.get("profile_pic_url"),
                            owner_jid=api_info.get("owner_jid"),
                        )
                        return Response({
                            "success": True,
                            "status": "connected",
                            "message": "WhatsApp já está conectado.",
                            "connected": True,
                        })
                    return Response({
                        "success": False,
                        "error": "A Evolution não retornou QR Code nem código de pareamento.",
                    }, status=400)

                # O mesmo status de espera serve para QR e pairing code.
                instance.qr_code_data = qr_data or ""
                instance.mark_as_scanning()

                payload = {
                    "success": True,
                    "status": "scanning",
                    "instance_name": instance.instance_name,
                    "qr_expires_at": (timezone.now() + timezone.timedelta(minutes=5)).isoformat(),
                }
                if qr_data:
                    payload["connection_method"] = "qr"
                    payload["qr_data"] = qr_data
                if pairing_code:
                    payload["connection_method"] = "pairing_code"
                    payload["pairing_code"] = str(pairing_code)
                return Response(payload)

            except Exception as e:
                error_msg = str(e).lower()
                if "already" in error_msg or "connected" in error_msg or "in use" in error_msg:
                    try:
                        api_info = evolution_service.get_connection_info(instance.instance_name)
                        if api_info.get("connected"):
                            instance.mark_as_connected(
                                profile_name=api_info.get("profile_name"),
                                profile_pic_url=api_info.get("profile_pic_url"),
                                owner_jid=api_info.get("owner_jid"),
                            )
                            return Response({
                                "success": True,
                                "status": "connected",
                                "message": "WhatsApp já está conectado.",
                                "connected": True,
                            })
                    except Exception:
                        pass
                logger.error("Erro ao solicitar conexão da instância %s", instance.instance_name, exc_info=True)
                return Response({
                    "success": False,
                    "error": "Não foi possível iniciar o pareamento. Verifique a conexão com a Evolution API.",
                }, status=500)
            
        except Exception as e:
            logger.error(f"Erro em connect: {str(e)}", exc_info=True)
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)

    def delete(self, request, instance_id):
        """Desconecta a instância sem apagar o cadastro local."""
        instance = get_object_or_404(UserInstance, id=instance_id, user=request.user)
        try:
            evolution_service.disconnect_instance(instance.instance_name)
        except Exception as exc:
            logger.warning("Falha ao desconectar %s na Evolution: %s", instance.instance_name, exc)
        instance.mark_as_disconnected()
        return Response({"success": True, "message": "WhatsApp desconectado."})


class StatusAPIView(APIView):
    """API para checar status"""
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, instance_id):
        try:
            instance = get_object_or_404(UserInstance, id=instance_id, user=request.user)
            api_info = evolution_service.get_connection_info(instance.instance_name)
            
            if api_info.get('connected'):
                instance.mark_as_connected(
                    profile_name=api_info.get('profile_name'),
                    profile_pic_url=api_info.get('profile_pic_url'),
                    owner_jid=api_info.get('owner_jid')
                )
            
            return Response({
                'success': True,
                'connected': api_info.get('connected', False),
                'status': instance.status
            })
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)
        

###########################  IA  ########################################

# =============================================
# VIEWS DE IA - ADICIONE NO FINAL DO ARQUIVO
# =============================================

class AIConversationDetailView(LoginRequiredMixin, APIView):
    """Ver detalhes de uma conversa específica"""
    
    def get(self, request, pk):
        try:
            conversation = get_object_or_404(AIConversation, pk=pk, revenda=request.user)
            
            return Response({
                'success': True,
                'conversation': {
                    'id': conversation.id,
                    'cliente_nome': conversation.cliente.nome,
                    'cliente_id': conversation.cliente.id,
                    'status': conversation.status,
                    'total_messages': conversation.total_messages,
                    'ai_messages': conversation.ai_messages,
                    'human_messages': conversation.human_messages,
                    'messages': conversation.messages[-50:],  # Últimas 50 mensagens
                    'first_message_at': conversation.first_message_at.isoformat(),
                    'last_message_at': conversation.last_message_at.isoformat(),
                    'closed_at': conversation.closed_at.isoformat() if conversation.closed_at else None,
                    'tags': conversation.tags,
                }
            })
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)

# whatsapp_integration/api/views.py

# whatsapp_integration/api/views.py

class AIConfigView(LoginRequiredMixin, APIView):
    
    def get(self, request):
        user = request.user
        is_admin = user.is_staff or user.is_superuser or getattr(user, 'tipo_usuario', '') == 'admin'
        
        if is_admin:
            revenda_id = request.GET.get('revenda_id')
            if revenda_id:
                config = AIConfig.objects.filter(revenda_id=revenda_id).first()
            else:
                config = AIConfig.objects.filter(revenda__isnull=True).first()
            
            return Response({
                'success': True,
                'is_admin': True,
                'config': {
                    'nome': config.nome if config else 'Padrão',
                    'provider': config.provider if config else 'groq',
                    'system_prompt': config.system_prompt if config else '',
                    'max_messages': config.max_messages_per_day if config else 200,
                    'max_history': config.max_history_messages if config else 10,
                    'response_delay': config.response_delay if config else 2,
                    'is_active': config.is_active if config else True,
                } if config else {}
            })
        
        # Revenda
        personal, _ = AIRevendaSettings.objects.get_or_create(revenda=user)
        ai_config = AIConfig.get_config(revenda=user)
        
        return Response({
            'success': True,
            'is_admin': False,
            'config': {
                'ia_ativada': personal.ia_ativada,
                'pausado': personal.pausado_ate and personal.pausado_ate > timezone.now(),
                'bot_name': personal.bot_name,
                'prompt_personalizado': personal.prompt_personalizado,
                'mensagem_saudacao': personal.mensagem_saudacao,
                'horario_inicio': str(personal.horario_inicio) if personal.horario_inicio else None,
                'horario_fim': str(personal.horario_fim) if personal.horario_fim else None,
                'max_messages': ai_config.max_messages_per_day if ai_config else 200,
                'messages_today': ai_config.messages_sent_today if hasattr(ai_config, 'messages_sent_today') else 0,
                                # No GET da revenda, adicione:
                'responder_privado': personal.responder_privado,
                'responder_grupos': personal.responder_grupos,
                'precisa_marcacao': personal.precisa_marcacao,
                'bot_marcacao': personal.bot_marcacao,
                'palavras_ativacao': personal.palavras_ativacao,
            }
        })
    
    def post(self, request):
        user = request.user
        is_admin = user.is_staff or user.is_superuser or getattr(user, 'tipo_usuario', '') == 'admin'
        
        if is_admin:
            revenda_id = request.data.get('revenda_id')
            if revenda_id:
                revenda = get_object_or_404(User, id=revenda_id)
                config, _ = AIConfig.objects.get_or_create(revenda=revenda)
                if not config.admin_id:
                    config.admin = user
            else:
                config, _ = AIConfig.objects.get_or_create(revenda__isnull=True)
                if not config.admin_id:
                    config.admin = user
            
            if 'nome' in request.data: config.nome = request.data['nome']
            if 'provider' in request.data: config.provider = request.data['provider']
            if 'system_prompt' in request.data: config.system_prompt = request.data['system_prompt']
            if 'max_messages' in request.data: config.max_messages_per_day = request.data['max_messages']
            if 'max_history' in request.data: config.max_history_messages = request.data['max_history']
            if 'response_delay' in request.data: config.response_delay = request.data['response_delay']
            if 'is_active' in request.data: config.is_active = request.data['is_active']
            if 'api_key' in request.data: config.api_key = request.data['api_key']
            
            config.save()
            return Response({'success': True, 'message': 'Configuração salva!'})
        
        # Revenda salva config pessoal
        # Revenda salva config pessoal
        personal, _ = AIRevendaSettings.objects.get_or_create(revenda=user)

        if 'ia_ativada' in request.data:
            personal.ia_ativada = request.data['ia_ativada']
        if 'bot_name' in request.data:
            personal.bot_name = request.data['bot_name']
        if 'prompt_personalizado' in request.data:
            personal.prompt_personalizado = request.data['prompt_personalizado']
        if 'mensagem_saudacao' in request.data:
            personal.mensagem_saudacao = request.data['mensagem_saudacao']
        if 'horario_inicio' in request.data:
            personal.horario_inicio = request.data['horario_inicio'] or None
        if 'horario_fim' in request.data:
            personal.horario_fim = request.data['horario_fim'] or None

        # NOVOS CAMPOS DE REGRAS
        if 'responder_privado' in request.data:
            personal.responder_privado = request.data['responder_privado']
        if 'responder_grupos' in request.data:
            personal.responder_grupos = request.data['responder_grupos']
        if 'precisa_marcacao' in request.data:
            personal.precisa_marcacao = request.data['precisa_marcacao']
        if 'bot_marcacao' in request.data:
            personal.bot_marcacao = request.data['bot_marcacao']
        if 'palavras_ativacao' in request.data:
            personal.palavras_ativacao = request.data['palavras_ativacao']

        personal.save()

        return Response({'success': True, 'message': 'Configurações salvas!'})

class AIConversationsListView(LoginRequiredMixin, APIView):
    """Listar conversas"""
    
    def get(self, request):
        try:
            conversations = AIConversation.objects.filter(
                revenda=request.user
            ).select_related('cliente').order_by('-last_message_at')
            
            # Filtros
            status_filter = request.GET.get('status')
            if status_filter:
                conversations = conversations.filter(status=status_filter)
            
            search = request.GET.get('search')
            if search:
                conversations = conversations.filter(cliente__nome__icontains=search)
            
            data = []
            for conv in conversations[:50]:  # Limitar a 50
                last_msg = conv.messages[-1] if conv.messages else None
                data.append({
                    'id': conv.id,
                    'cliente_nome': conv.cliente.nome,
                    'cliente_id': conv.cliente.id,
                    'status': conv.status,
                    'total_messages': conv.total_messages,
                    'ai_messages': conv.ai_messages,
                    'human_messages': conv.human_messages,
                    'last_message': last_msg['content'][:100] if last_msg else '',
                    'last_message_at': conv.last_message_at.isoformat(),
                    'tags': conv.tags,
                })
            
            return Response({'success': True, 'conversations': data})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)


class AIPauseConversationView(LoginRequiredMixin, APIView):
    """Pausar/Retomar conversa"""
    
    def post(self, request, pk):
        try:
            conversation = get_object_or_404(AIConversation, pk=pk, revenda=request.user)
            
            if conversation.status == 'paused':
                conversation.status = 'active'
                message = 'Conversa retomada'
            else:
                conversation.status = 'paused'
                message = 'Conversa pausada'
            
            conversation.save()
            
            return Response({'success': True, 'message': message, 'status': conversation.status})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)


class AICloseConversationView(LoginRequiredMixin, APIView):
    """Encerrar conversa"""
    
    def post(self, request, pk):
        try:
            conversation = get_object_or_404(AIConversation, pk=pk, revenda=request.user)
            
            conversation.status = 'closed'
            conversation.closed_at = timezone.now()
            conversation.save()
            
            return Response({'success': True, 'message': 'Conversa encerrada'})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)


class AIClientSettingsView(LoginRequiredMixin, APIView):
    """Configuração de IA por cliente"""
    
    
    def get(self, request, client_id=None):
        try:
            if client_id:
                settings_obj = get_object_or_404(
                    AIClientSettings, 
                    revenda=request.user, 
                    cliente_id=client_id
                )
                return Response({
                    'success': True,
                    'settings': {
                        'is_enabled': settings_obj.is_enabled,
                        'is_paused': settings_obj.is_paused,
                        'ignore_client': settings_obj.ignore_client,
                        'custom_prompt': settings_obj.custom_prompt,
                        'notes': settings_obj.notes,
                        'max_messages': settings_obj.max_messages_this_client,
                        'messages_sent': settings_obj.messages_sent,
                    }
                })
            
            # Listar todos
            settings_list = AIClientSettings.objects.filter(
                revenda=request.user
            ).select_related('cliente')
            
            data = []
            for s in settings_list:
                data.append({
                    'client_id': s.cliente.id,
                    'client_name': s.cliente.nome,
                    'is_enabled': s.is_enabled,
                    'is_paused': s.is_paused,
                    'ignore_client': s.ignore_client,
                })
            
            return Response({'success': True, 'clients': data})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)
    
    def post(self, request, client_id):
        try:
            cliente = get_object_or_404(CustomUser, id=client_id, dono=request.user)
            settings_obj, created = AIClientSettings.objects.get_or_create(
                revenda=request.user,
                cliente=cliente
            )
            
            if 'is_enabled' in request.data:
                settings_obj.is_enabled = request.data['is_enabled']
            if 'is_paused' in request.data:
                settings_obj.is_paused = request.data['is_paused']
            if 'custom_prompt' in request.data:
                settings_obj.custom_prompt = request.data['custom_prompt']
            if 'notes' in request.data:
                settings_obj.notes = request.data['notes']
            if 'max_messages' in request.data:
                settings_obj.max_messages_this_client = request.data['max_messages']
            
            settings_obj.save()
            
            return Response({'success': True, 'message': 'Configuração salva!'})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)


class AIIgnoreClientView(LoginRequiredMixin, APIView):
    """Ignorar/Designorar cliente"""
    
    def post(self, request, client_id):
        try:
            cliente = get_object_or_404(CustomUser, id=client_id, dono=request.user)
            settings_obj, created = AIClientSettings.objects.get_or_create(
                revenda=request.user,
                cliente=cliente
            )
            
            settings_obj.ignore_client = not settings_obj.ignore_client
            settings_obj.save()
            
            return Response({
                'success': True,
                'ignore_client': settings_obj.ignore_client,
                'message': f"Cliente {'ignorado' if settings_obj.ignore_client else 'reativado'}!"
            })
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)


class AIPauseAllView(LoginRequiredMixin, APIView):
    """Pausar/Retomar TODAS as IAs"""
    
    def post(self, request):
        try:
            ai_config = get_object_or_404(AIConfig, revenda=request.user)
            
            if ai_config.pause_until and ai_config.pause_until > timezone.now():
                ai_config.pause_until = None
                message = 'IA reativada para todos'
            else:
                minutes = request.data.get('minutes', 30)
                ai_config.pause_until = timezone.now() + timedelta(minutes=int(minutes))
                message = f'IA pausada por {minutes} minutos'
            
            ai_config.save()
            
            return Response({'success': True, 'message': message})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)


class AIStatsView(LoginRequiredMixin, APIView):
    """Estatísticas da IA"""
    
    def get(self, request):
        try:
            ai_config = AIConfig.objects.filter(revenda=request.user).first()
            conversations = AIConversation.objects.filter(revenda=request.user)
            
            stats = {
                'total_conversations': conversations.count(),
                'active_conversations': conversations.filter(status='active').count(),
                'paused_conversations': conversations.filter(status='paused').count(),
                'closed_conversations': conversations.filter(status='closed').count(),
                'total_messages_today': ai_config.messages_sent_today if ai_config else 0,
                'max_messages': ai_config.max_messages_per_day if ai_config else 200,
                'is_active': ai_config.is_active if ai_config else False,
                'is_paused': ai_config.pause_until and ai_config.pause_until > timezone.now() if ai_config else False,
                'ignored_clients': AIClientSettings.objects.filter(revenda=request.user, ignore_client=True).count(),
            }
            
            return Response({'success': True, 'stats': stats})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)


class AIQuickReplyView(LoginRequiredMixin, APIView):
    """Respostas rápidas"""
    
    def get(self, request):
        try:
            replies = AIQuickReply.objects.filter(revenda=request.user, is_active=True)
            data = [{
                'id': r.id,
                'trigger': r.trigger,
                'reply': r.reply,
                'priority': r.priority,
            } for r in replies]
            
            return Response({'success': True, 'replies': data})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)
    
    def post(self, request):
        try:
            reply = AIQuickReply.objects.create(
                revenda=request.user,
                trigger=request.data.get('trigger', ''),
                reply=request.data.get('reply', ''),
                priority=request.data.get('priority', 0),
            )
            
            return Response({'success': True, 'reply': {'id': reply.id, 'trigger': reply.trigger}})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)
    
    def delete(self, request, pk):
        try:
            reply = get_object_or_404(AIQuickReply, pk=pk, revenda=request.user)
            reply.delete()
            
            return Response({'success': True, 'message': 'Resposta rápida removida'})
        except Exception as e:
            return Response({'success': False, 'error': 'Erro interno ao processar a solicitação.'}, status=500)
        


# whatsapp_integration/api/views.py

class AIAdminRevendasView(LoginRequiredMixin, APIView):
    def get(self, request):
        if not (request.user.is_staff or request.user.is_superuser or getattr(request.user, 'tipo_usuario', '') == 'admin'):
            return Response({'success': False, 'error': 'Acesso negado'}, status=403)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        revendas = User.objects.filter(tipo_usuario='revenda')
        
        data = []
        for rev in revendas:
            config = AIConfig.objects.filter(revenda=rev).first()
            data.append({
                'id': rev.id,
                'nome': rev.nome or rev.username,
                'email': rev.email or '',
                'username': rev.username,
                'tem_config': config is not None,
                'config_ativa': config.is_active if config else False,
            })
        
        return Response({'success': True, 'revendas': data})
    

# whatsapp_integration/services/ai_service.py

class IsolatedAIService:
    
    def should_respond(self, message_data, instance_name):
        """
        Verifica se a IA DEVE responder a esta mensagem
        
        Retorna: (True/False, motivo)
        """
        from whatsapp_integration.models import AIRevendaSettings
        
        # Buscar configurações da revenda
        instance = UserInstance.objects.filter(instance_name=instance_name).first()
        if not instance:
            return False, "Instância não encontrada"
        
        revenda = instance.user
        settings = AIRevendaSettings.objects.filter(revenda=revenda, ia_ativada=True).first()
        
        if not settings:
            return False, "IA não ativada"
        
        # Pegar dados da mensagem
        sender = message_data.get('key', {}).get('remoteJid', '')
        is_group = '@g.us' in sender
        text = message_data.get('message', {}).get('conversation', '') or \
               message_data.get('message', {}).get('extendedTextMessage', {}).get('text', '')
        
        # Se não tem texto, ignora
        if not text:
            return False, "Sem texto"
        
        # Se é mensagem enviada por NÓS (fromMe), ignora
        if message_data.get('key', {}).get('fromMe'):
            return False, "Mensagem própria"
        
        # ==========================================
        # REGRA 1: CONVERSA PRIVADA
        # ==========================================
        if not is_group:
            if settings.responder_privado:
                # Verificar palavras de ativação
                if self._check_activation_words(text, settings):
                    return True, "Conversa privada com palavra-chave"
                elif not settings.palavras_ativacao:
                    return True, "Conversa privada (responde tudo)"
                else:
                    return False, "Palavra-chave não detectada"
            return False, "Resposta privada desativada"
        
        # ==========================================
        # REGRA 2: GRUPO
        # ==========================================
        if is_group:
            if not settings.responder_grupos:
                return False, "Resposta em grupos desativada"
            
            # Verificar se precisa de marcação
            if settings.precisa_marcacao:
                marcacao = settings.bot_marcacao or '@bot'
                if marcacao.lower() not in text.lower():
                    return False, f"Bot não foi marcado ({marcacao})"
            
            # Verificar palavras de ativação
            if settings.palavras_ativacao:
                if not self._check_activation_words(text, settings):
                    return False, "Palavra-chave não detectada no grupo"
            
            return True, "Mensagem em grupo válida"
        
        return False, "Regra não identificada"
    
    def _check_activation_words(self, text, settings):
        """Verifica se o texto contém palavras de ativação"""
        if not settings.palavras_ativacao:
            return True  # Se não tem palavras definidas, responde tudo
        
        palavras = [p.strip().lower() for p in settings.palavras_ativacao.split(',') if p.strip()]
        text_lower = text.lower()
        
        for palavra in palavras:
            if palavra in text_lower:
                return True
        
        # Verificar também palavras-chave da empresa
        if settings.palavras_chave_empresa:
            palavras_empresa = [p.strip().lower() for p in settings.palavras_chave_empresa.split(',') if p.strip()]
            for palavra in palavras_empresa:
                if palavra in text_lower:
                    return True
        
        return False