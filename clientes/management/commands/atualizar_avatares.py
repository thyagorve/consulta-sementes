import requests
import time
import base64
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from clientes.models import CustomUser
from whatsapp_integration.models import UserInstance
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Atualiza avatares do WhatsApp usando a instância de cada revenda'

    def add_arguments(self, parser):
        parser.add_argument('--todos', action='store_true', help='Atualiza todos os clientes')
        parser.add_argument('--limite', type=int, default=20, help='Limite de clientes por execução')
        parser.add_argument('--validar', action='store_true', help='Apenas validar fotos existentes')

    def handle(self, *args, **options):
        if options['validar']:
            self.validar_fotos_existentes()
            return
        
        self.stdout.write('🔄 Iniciando atualização de avatares...')
        
        queryset = CustomUser.objects.filter(
            tipo_usuario='cliente',
            whatsapp__isnull=False,
            is_active=True
        ).exclude(whatsapp='')
        
        if not options['todos']:
            agora = timezone.now()
            queryset = queryset.filter(
                Q(whatsapp_avatar_expires__isnull=True) |
                Q(whatsapp_avatar_expires__lt=agora) |
                Q(whatsapp_avatar_status='pending') |
                Q(whatsapp_avatar_status='error') |
                Q(whatsapp_avatar_status='invalid_url')  # Nova verificação
            )
        
        total = queryset.count()
        limite = options['limite']
        clientes = queryset[:limite]
        
        self.stdout.write(f'📊 {total} clientes precisam de atualização')
        self.stdout.write(f'⚡ Atualizando {len(clientes)} nesta execução...')
        
        atualizados = 0
        erros = 0
        quebradas = 0
        
        for cliente in clientes:
            try:
                resultado = self.buscar_avatar_cliente(cliente)
                if resultado == 'ok':
                    atualizados += 1
                elif resultado == 'quebrada':
                    quebradas += 1
                else:
                    erros += 1
                time.sleep(2)
            except Exception as e:
                logger.error(f'Erro ao atualizar avatar de {cliente.id}: {e}')
                erros += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'✅ Concluído! {atualizados} atualizados, {quebradas} quebradas, {erros} erros'
        ))

    def validar_fotos_existentes(self):
        """Apenas valida fotos já salvas"""
        self.stdout.write('🔍 Validando fotos existentes...')
        
        clientes_com_foto = CustomUser.objects.filter(
            whatsapp_avatar_status='found'
        ).exclude(whatsapp_avatar_url__isnull=True)
        
        total = clientes_com_foto.count()
        validas = 0
        quebradas = []
        
        for cliente in clientes_com_foto:
            url = cliente.whatsapp_avatar_url
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    # Verificar content-type
                    content_type = response.headers.get('content-type', '')
                    if 'image' in content_type:
                        validas += 1
                    else:
                        quebradas.append((cliente.nome, f"Tipo inválido: {content_type}"))
                        cliente.whatsapp_avatar_status = 'invalid_url'
                        cliente.whatsapp_avatar_error = f"Tipo inválido: {content_type}"
                        cliente.save()
                else:
                    quebradas.append((cliente.nome, f"HTTP {response.status_code}"))
                    cliente.whatsapp_avatar_status = 'invalid_url'
                    cliente.whatsapp_avatar_error = f"HTTP {response.status_code}"
                    cliente.save()
            except Exception as e:
                quebradas.append((cliente.nome, str(e)[:50]))
                cliente.whatsapp_avatar_status = 'invalid_url'
                cliente.whatsapp_avatar_error = str(e)[:200]
                cliente.save()
        
        self.stdout.write(f'✅ Válidas: {validas}')
        self.stdout.write(f'❌ Quebradas: {len(quebradas)}')
        for nome, erro in quebradas:
            self.stdout.write(f'  - {nome}: {erro}')

    def obter_instancia_para_cliente(self, cliente):
        if cliente.dono:
            instancia = UserInstance.objects.filter(
                user=cliente.dono,
                status='connected',
                is_active=True
            ).first()
            if instancia:
                return instancia
        
        return UserInstance.objects.filter(
            instance_name='gestor',
            status='connected',
            is_active=True
        ).first()

    def buscar_avatar_cliente(self, cliente):
        numero = ''.join(filter(str.isdigit, cliente.whatsapp))
        if len(numero) < 10:
            cliente.whatsapp_avatar_status = 'no_whatsapp'
            cliente.save(update_fields=['whatsapp_avatar_status'])
            return 'erro'
        
        if len(numero) in [10, 11]:
            formatted = f"55{numero}"
        elif numero.startswith('55'):
            formatted = numero
        else:
            formatted = f"55{numero}"
        
        if formatted.startswith('5555'):
            formatted = formatted[2:]
        
        instancia = self.obter_instancia_para_cliente(cliente)
        
        if not instancia:
            self.stdout.write(f'  ❌ {cliente.nome}: Nenhuma instância conectada')
            cliente.whatsapp_avatar_status = 'error'
            cliente.whatsapp_avatar_error = 'Nenhuma instância conectada'
            cliente.save()
            return 'erro'
        
        instance_name = instancia.instance_name
        base_url = (getattr(settings, 'EVOLUTION_API_BASE_URL', '') or instancia.base_url or '').rstrip('/')
        api_key = instancia.api_key or getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', '')
        
        self.stdout.write(f'  📱 {cliente.nome} | Instância: {instance_name} | Número: {formatted}')
        
        # Buscar URL da foto
        foto_url = self.obter_url_foto(formatted, base_url, api_key, instance_name)
        
        if not foto_url and instance_name != 'gestor':
            self.stdout.write(f'    ⚠️ Falhou com {instance_name}, tentando gestor...')
            instancia_gestor = UserInstance.objects.filter(
                instance_name='gestor', status='connected', is_active=True
            ).first()
            if instancia_gestor:
                foto_url = self.obter_url_foto(
                    formatted, 
                    (getattr(settings, 'EVOLUTION_API_BASE_URL', '') or instancia_gestor.base_url or '').rstrip('/'),
                    instancia_gestor.api_key or getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', ''), 
                    'gestor'
                )
        
        if not foto_url:
            cliente.whatsapp_avatar_status = 'not_found'
            cliente.whatsapp_avatar_updated = timezone.now()
            cliente.save()
            self.stdout.write(f'    ⚠️ Sem foto')
            return 'erro'
        
        # Validar e baixar a foto
        if self.validar_e_salvar_foto(cliente, foto_url):
            return 'ok'
        else:
            return 'quebrada'

    def obter_url_foto(self, numero, base_url, api_key, instance_name):
        url = f"{base_url}/chat/fetchProfilePictureUrl/{instance_name}"
        headers = {'apikey': api_key, 'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, json={"number": numero}, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get('profilePictureUrl')
        except Exception as e:
            self.stdout.write(f'    ❌ Erro API: {str(e)[:100]}')
        return None

    def validar_e_salvar_foto(self, cliente, foto_url):
        """Valida se a foto é acessível e é uma imagem real"""
        try:
            # Verificar se a URL é acessível
            response = requests.get(foto_url, timeout=10, stream=True)
            
            if response.status_code != 200:
                self.stdout.write(f'    ❌ Foto inacessível: HTTP {response.status_code}')
                cliente.whatsapp_avatar_status = 'invalid_url'
                cliente.whatsapp_avatar_error = f'URL inacessível: HTTP {response.status_code}'
                cliente.save()
                return False
            
            # Verificar content-type
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                self.stdout.write(f'    ❌ Não é imagem: {content_type}')
                cliente.whatsapp_avatar_status = 'invalid_url'
                cliente.whatsapp_avatar_error = f'Tipo inválido: {content_type}'
                cliente.save()
                return False
            
            # Verificar tamanho (máximo 500KB)
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 500000:
                self.stdout.write(f'    ⚠️ Foto muito grande: {int(content_length)/1024:.0f}KB')
            
            # Baixar e converter para base64 (para cache local)
            try:
                image_data = response.content
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # Salvar URL e base64
                cliente.whatsapp_avatar_url = foto_url
                cliente.whatsapp_avatar_base64 = image_base64
                cliente.whatsapp_avatar_status = 'found'
                cliente.whatsapp_avatar_updated = timezone.now()
                cliente.whatsapp_avatar_expires = timezone.now() + timedelta(days=7)
                cliente.whatsapp_avatar_error = None
                cliente.save(update_fields=[
                    'whatsapp_avatar_url', 'whatsapp_avatar_base64',
                    'whatsapp_avatar_status', 'whatsapp_avatar_updated',
                    'whatsapp_avatar_expires', 'whatsapp_avatar_error'
                ])
                
                self.stdout.write(f'    ✅ Foto válida ({len(image_data)/1024:.0f}KB)')
                return True
                
            except Exception as e:
                self.stdout.write(f'    ❌ Erro ao baixar: {str(e)[:100]}')
                # Salvar só a URL mesmo assim
                cliente.whatsapp_avatar_url = foto_url
                cliente.whatsapp_avatar_status = 'found'
                cliente.whatsapp_avatar_updated = timezone.now()
                cliente.whatsapp_avatar_expires = timezone.now() + timedelta(days=7)
                cliente.whatsapp_avatar_error = f'Download falhou: {str(e)[:200]}'
                cliente.save()
                return True  # URL existe, mas não conseguiu baixar
                
        except Exception as e:
            self.stdout.write(f'    ❌ Erro validação: {str(e)[:100]}')
            cliente.whatsapp_avatar_status = 'invalid_url'
            cliente.whatsapp_avatar_error = str(e)[:200]
            cliente.save()
            return False
