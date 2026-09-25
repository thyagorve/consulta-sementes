from django.core.exceptions import ObjectDoesNotExist

def get_whatsapp_api_and_headers(usuario):
    """
    Obtém as configurações do WhatsApp da instância do usuário.
    """
    try:
        # Obtém a instância associada ao usuário
        instance = usuario.instance

        if not instance.host or not instance.token or not instance.connection_key:
            raise ValueError("Configurações do WhatsApp não encontradas para este usuário.")

        # Define a URL base e os headers com o token
        base_url = instance.host
        headers = {
            "Authorization": f"Bearer {instance.token}",
            "Content-Type": "application/json"
        }
        return base_url, instance.connection_key, headers
    except ObjectDoesNotExist:
        raise ValueError("Instância não configurada para este usuário.")
