from datetime import timedelta
import logging

import requests
import time

from django.conf import settings
from django.utils import timezone

from .models import Mensagem
from whatsapp_integration.models import UserInstance


from clientes.message_variables import (
    substituir_variaveis_mensagem,
)

logger = logging.getLogger(__name__)

def formatar_numero(numero):
    """
    Remove caracteres e adiciona o código do Brasil quando necessário.
    """

    if not numero:
        return ""

    numero = "".join(
        caractere
        for caractere in str(numero)
        if caractere.isdigit()
    )

    if len(numero) in (10, 11):
        numero = f"55{numero}"

    return numero


def get_api_details(usuario):
    """
    Busca a instância Evolution ativa e conectada do usuário.
    """

    instance = UserInstance.objects.filter(
        user=usuario,
        is_active=True,
        status="connected",
    ).first()

    if not instance:
        raise ValueError(
            "Instância WhatsApp não encontrada ou desconectada."
        )

    base_url = getattr(
        settings,
        "EVOLUTION_API_BASE_URL",
        "",
    ).rstrip("/")

    api_key = (
        instance.api_key
        or getattr(
            settings,
            "EVOLUTION_GLOBAL_API_KEY",
            "",
        )
    )

    if not base_url:
        raise ValueError(
            "EVOLUTION_API_BASE_URL não configurada."
        )

    if not api_key:
        raise ValueError(
            "Chave da Evolution API não configurada."
        )

    api_url = (
        f"{base_url}/message/sendText/"
        f"{instance.instance_name}"
    )

    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
    }

    return api_url, headers


def enviar_mensagem(
    request,
    cliente,
    mensagem_template,
    tipo_mensagem,
    dias_antes_vencimento=None,
):
    """
    Envia uma mensagem usando a Evolution API e a função
    centralizada de variáveis.
    """

    if not tipo_mensagem or not isinstance(
        tipo_mensagem,
        str,
    ):
        logger.warning("tipo_mensagem ausente ou inválido ao tentar enviar mensagem automática.")
        return None

    if not cliente:
        logger.warning("Cliente não informado ao tentar enviar mensagem automática.")
        return None

    agora = timezone.now()

    usuario_instancia = (
        request.user
        if request and hasattr(request, "user")
        else cliente.dono
    )

    if not usuario_instancia:
        logger.warning("Não foi possível identificar o dono da instância para envio automático.")
        return None

    try:
        api_url, headers = get_api_details(
            usuario_instancia
        )
    except ValueError as erro:
        logger.warning("Configuração da Evolution indisponível para envio automático: %s", erro)
        return None

    try:
        mensagem_conteudo = substituir_variaveis_mensagem(
            mensagem_template,
            cliente,
            variaveis_extras={
                "dias_antes_vencimento": (
                    dias_antes_vencimento
                    if dias_antes_vencimento is not None
                    else ""
                )
            },
        )

        if not mensagem_conteudo.strip():
            logger.warning("Mensagem automática ficou vazia após substituição das variáveis.")
            return None

        logger.debug("Mensagem automática montada para o cliente id=%s.", getattr(cliente, "id", None))

    except Exception as erro:
        nome_cliente = (
            getattr(cliente, "nome", "")
            or getattr(cliente, "username", "")
            or cliente.id
        )

        logger.exception("Erro ao montar mensagem automática para cliente id=%s.", getattr(cliente, "id", None))
        return None

    intervalo_tempo = agora - timedelta(hours=1)

    mensagem_existente = Mensagem.objects.filter(
        usuario=cliente,
        conteudo=mensagem_conteudo,
        data_envio__gte=intervalo_tempo,
    ).exists()

    if mensagem_existente:
        logger.info("Envio automático duplicado evitado para cliente id=%s e tipo=%s.", getattr(cliente, "id", None), tipo_mensagem)
        return None

    numero = formatar_numero(cliente.whatsapp)

    if not numero:
        logger.warning("WhatsApp inválido para envio automático. cliente_id=%s", getattr(cliente, "id", None))
        return None

    payload = {
        "number": numero,
        "text": mensagem_conteudo,
    }

    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        logger.info("Evolution respondeu ao envio automático com HTTP %s para cliente_id=%s.", response.status_code, getattr(cliente, "id", None))

    except requests.RequestException as erro:
        logger.warning("Falha de comunicação com a Evolution no envio automático para cliente_id=%s: %s", getattr(cliente, "id", None), erro)
        return None

    status_envio = (
        "Enviada"
        if response.status_code in (200, 201)
        else "Erro"
    )

    dados_mensagem = {
        "usuario": cliente,
        "numero": cliente.whatsapp,
        "conteudo": mensagem_conteudo,
        "status": status_envio,
        "data_envio": agora,
    }

    # Só adicione "tipo" se esse campo existir no model.
    campos_mensagem = {
        campo.name
        for campo in Mensagem._meta.get_fields()
    }

    if "tipo" in campos_mensagem:
        dados_mensagem["tipo"] = tipo_mensagem

    Mensagem.objects.create(**dados_mensagem)

    time.sleep(5)

    try:
        resposta_json = response.json()
    except ValueError:
        resposta_json = {
            "text": response.text
        }

    return response.status_code, resposta_json