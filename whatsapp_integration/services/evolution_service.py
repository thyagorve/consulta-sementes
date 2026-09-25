# whatsapp_integration/services/evolution_service.py
import requests
import json
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class EvolutionAPIService:
    """Serviço para comunicação com a Evolution API"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'EVOLUTION_API_BASE_URL', 'http://localhost:8080')                
        self.api_key = getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', '')
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method, endpoint, data=None, timeout=30):
        """Método genérico para fazer requisições"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, params=data, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=timeout)
            else:
                raise ValueError(f"Método {method} não suportado")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Evolution API Error - {method} {endpoint}: {str(e)}")
            raise Exception(f"Erro na Evolution API: {str(e)}")
    
    def create_instance(self, instance_name):
        """Cria uma nova instância"""
        endpoint = "instance/create"
        payload = {
            "instanceName": instance_name,
            "token": f"{instance_name.upper().replace('_', '-')}-TOKEN",
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }
        
        return self._make_request('POST', endpoint, payload)
    
    def get_instance_status(self, instance_name):
        """Busca status de uma instância"""
        endpoint = "instance/fetchInstances"
        params = {"instanceName": instance_name}
        
        try:
            response = self._make_request('GET', endpoint, params)
            
            if isinstance(response, list) and len(response) > 0:
                return response[0]
            return None
        except:
            return None
    
    def generate_qr_code(self, instance_name, phone_number=None):
        """Solicita QR Code ou código de pareamento à Evolution API."""
        endpoint = f"instance/connect/{instance_name}"
        url = f"{self.base_url}/{endpoint}"
        params = {}
        if phone_number:
            params["number"] = str(phone_number)

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=params or None,
                timeout=90,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Resposta inválida ao solicitar conexão.")
            return data
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Falha ao solicitar conexão da instância %s: %s", instance_name, exc)
            raise Exception(f"Erro ao solicitar conexão do WhatsApp: {exc}") from exc
    
    def disconnect_instance(self, instance_name):
        """Desconecta uma instância"""
        endpoint = f"instance/logout/{instance_name}"
        return self._make_request('DELETE', endpoint)
    
    def delete_instance(self, instance_name):
        """Deleta uma instância permanentemente"""
        endpoint = f"instance/delete/{instance_name}"
        return self._make_request('DELETE', endpoint)
    
    def get_connection_info(self, instance_name):
        instance_data = self.get_instance_status(instance_name)
        
        if not instance_data:
            return {
                'connected': False,
                'status': 'not_found',
                'exists_in_api': False
            }
        
        owner_jid = instance_data.get('ownerJid')
        profile_name = instance_data.get('profileName')
        connection_status = instance_data.get('connectionStatus', '')
        
        # Se tem ownerJid OU status 'open' = conectado
        if owner_jid or connection_status == 'open':
            return {
                'connected': True,
                'status': 'connected',
                'exists_in_api': True,
                'profile_name': profile_name or 'Usuário WhatsApp',
                'profile_pic_url': instance_data.get('profilePicUrl'),
                'owner_jid': owner_jid or '',
                'connection_status': connection_status
            }

        return {
            'connected': False,
            'status': 'disconnected',
            'exists_in_api': True,
            'connection_status': connection_status
        }
# Singleton para uso em toda a aplicação
evolution_service = EvolutionAPIService()