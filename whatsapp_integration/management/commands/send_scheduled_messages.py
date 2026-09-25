# -*- coding: utf-8 -*-
import logging
import re
import requests
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.timezone import make_aware

from clientes.models import MensagemConfigurada, ConfiguracaoMensagem
from whatsapp_integration.models import (
    HistoricoMensagemAutomatica,
    UserInstance
)

logger = logging.getLogger(__name__)

EVO_BASE_URL = getattr(settings, 'EVOLUTION_API_BASE_URL', 'http://localhost:8080')
EVO_HEADERS = getattr(settings, 'EVOLUTION_API_HEADERS', {})
EVO_TIMEOUT_SECONDS = getattr(settings, 'EVOLUTION_API_TIMEOUT_SECONDS', 45)


def formatar_numero_whatsapp(numero):
    """
    Formata número para padrão internacional aceito pela Evolution API.
    
    Suporta múltiplos formatos:
    - 11999999999 → +5511999999999
    - 11 99999-9999 → +5511999999999
    - 5511999999999 → +5511999999999
    - +5511999999999 → +5511999999999 (já está correto)
    - +1 (212) 555-1234 → +12125551234 (números internacionais)
    - 447911123456 → +447911123456 (Reino Unido)
    
    Retorna None se não conseguir formatar.
    """
    if not numero or not isinstance(numero, str):
        return None
    
    # Remove todos os caracteres não numéricos, exceto o +
    numero_limpo = re.sub(r'[^\d\+]', '', numero.strip())
    
    # Se já começar com +, verifica se tem dígitos suficientes
    if numero_limpo.startswith('+'):
        # Remove o + para contar dígitos
        digitos = numero_limpo[1:]
        # WhatsApp requer pelo menos 10 dígitos (incluindo código do país)
        if len(digitos) >= 10 and digitos.isdigit():
            return numero_limpo  # Já está no formato correto
    
    # Se não tem +, processa o número
    elif numero_limpo.isdigit():
        # Se já tem código do país (BR: 55 seguido de 10-11 dígitos)
        if numero_limpo.startswith('55'):
            if len(numero_limpo) in [12, 13]:  # 55 + DDD (2) + número (8 ou 9)
                return f"+{numero_limpo}"
        
        # Se parece número brasileiro sem código (11 dígitos: DDD(2) + número(9))
        elif len(numero_limpo) == 11:
            ddd = numero_limpo[:2]
            # Verifica se é um DDD válido no Brasil
            if ddd in ['11', '12', '13', '14', '15', '16', '17', '18', '19',
                      '21', '22', '24', '27', '28', 
                      '31', '32', '33', '34', '35', '37', '38', 
                      '41', '42', '43', '44', '45', '46', '47', '48', '49',
                      '51', '53', '54', '55', '61', '62', '63', '64', '65', 
                      '66', '67', '68', '69', '71', '73', '74', '75', '77', 
                      '79', '81', '82', '83', '84', '85', '86', '87', '88', 
                      '89', '91', '92', '93', '94', '95', '96', '97', '98', '99']:
                return f"+55{numero_limpo}"
        
        # Para números internacionais sem + (ex: 447911123456 - UK)
        elif 10 <= len(numero_limpo) <= 15:
            # Tenta identificar código do país
            # Códigos de país começam com 1-3 dígitos
            # Lista de códigos de país comuns
            country_codes = ['1', '7', '20', '27', '30', '31', '32', '33', '34',
                           '36', '39', '40', '41', '43', '44', '45', '46', '47',
                           '48', '49', '51', '52', '53', '54', '55', '56', '57',
                           '58', '60', '61', '62', '63', '64', '65', '66', '81',
                           '82', '84', '86', '90', '91', '92', '93', '94', '95',
                           '98', '212', '213', '216', '218', '220', '221', '222',
                           '223', '224', '225', '226', '227', '228', '229', '230',
                           '231', '232', '233', '234', '235', '236', '237', '238',
                           '239', '240', '241', '242', '243', '244', '245', '246',
                           '247', '248', '249', '250', '251', '252', '253', '254',
                           '255', '256', '257', '258', '260', '261', '262', '263',
                           '264', '265', '266', '267', '268', '269', '290', '291',
                           '297', '298', '299', '350', '351', '352', '353', '354',
                           '355', '356', '357', '358', '359', '370', '371', '372',
                           '373', '374', '375', '376', '377', '378', '379', '380',
                           '381', '382', '383', '385', '386', '387', '389', '420',
                           '421', '423', '500', '501', '502', '503', '504', '505',
                           '506', '507', '508', '509', '590', '591', '592', '593',
                           '594', '595', '596', '597', '598', '599', '670', '672',
                           '673', '674', '675', '676', '677', '678', '679', '680',
                           '681', '682', '683', '685', '686', '687', '688', '689',
                           '690', '691', '692', '850', '852', '853', '855', '856',
                           '880', '881', '882', '883', '886', '960', '961', '962',
                           '963', '964', '965', '966', '967', '968', '970', '971',
                           '972', '973', '974', '975', '976', '977', '992', '993',
                           '994', '995', '996', '998']
            
            for code in sorted(country_codes, key=len, reverse=True):
                if numero_limpo.startswith(code) and len(numero_limpo) > len(code):
                    return f"+{numero_limpo}"
    
    # Se chegou aqui, não conseguiu formatar
    logger.warning("Número não pôde ser formatado (final %s)", str(numero)[-4:])
    return None


def validar_e_formatar_numero(numero):
    """
    Valida e formata número para envio.
    Retorna (numero_formatado, mensagem_erro)
    Se válido: (numero_formatado, None)
    Se inválido: (None, mensagem_erro)
    """
    if not numero:
        return None, "Número está vazio"
    
    # Remove espaços extras
    numero = str(numero).strip()
    
    # Verifica se já está no formato correto (começa com + e tem dígitos)
    if numero.startswith('+'):
        # Verifica se tem pelo menos 10 dígitos após o +
        digitos = re.sub(r'\D', '', numero[1:])
        if len(digitos) >= 10:
            return numero, None
        else:
            return None, f"Número muito curto: {numero}"
    
    # Tenta formatar
    numero_formatado = formatar_numero_whatsapp(numero)
    
    if numero_formatado:
        return numero_formatado, None
    else:
        return None, f"Número inválido ou formato não reconhecido: {numero}"


class Command(BaseCommand):
    help = 'Envia mensagens automáticas agendadas para clientes conforme critério de dias e horário.'

    def handle(self, *args, **options):
        logger.info("🚀 Iniciando comando de envio de mensagens agendadas")

        now = timezone.localtime(timezone.now())
        today = now.date()
        janela_inicio = now - timedelta(minutes=15)

        User = get_user_model()

        # 🔹 BUSCA TODOS OS REVENDEDORES ATIVOS
        revendedores = User.objects.filter(
            is_active=True,
            tipo_usuario__in=['revenda', 'admin']
        )

        mensagens_configuradas = MensagemConfigurada.objects.none()

        for revendedor in revendedores:
            config = ConfiguracaoMensagem.objects.filter(usuario=revendedor).first()
            if config:
                mensagens_configuradas |= MensagemConfigurada.objects.filter(
                    configuracao=config
                )

        if not mensagens_configuradas.exists():
            self.stdout.write("✅ Nenhuma mensagem configurada encontrada.")
            return

        # 🔹 FILTRA MENSAGENS PELO HORÁRIO
        mensagens_para_enviar = []
        for msg in mensagens_configuradas:
            if not msg.horario_envio:
                continue

            horario_hoje = make_aware(datetime.combine(today, msg.horario_envio))
            if janela_inicio <= horario_hoje <= now:
                mensagens_para_enviar.append(msg)

        if not mensagens_para_enviar:
            self.stdout.write("⏭️ Nenhuma mensagem elegível no horário.")
            return

        # 🔹 PROCESSA CADA CONFIGURAÇÃO
        for msg_config in mensagens_para_enviar:
            dono = msg_config.configuracao.usuario
            data_alvo = today + timedelta(days=msg_config.criterio_dias)

            clientes = User.objects.filter(
                data_vencimento=data_alvo,
                is_active=True,
                whatsapp__isnull=False,
                whatsapp__gt='',
                tipo_usuario__in=['cliente', 'revenda'],
                dono=dono,
                dono__is_active=True,
            ).select_related(
                'dono'
            ).prefetch_related(
                'dono__whatsapp_instances'
            )

            if not clientes.exists():
                continue

            for cliente in clientes:
                # 🔹 OBTÉM INSTÂNCIA CONECTADA DO DONO
                instancia = cliente.dono.whatsapp_instances.filter(
                    status='connected',
                    is_active=True
                ).first()

                if not instancia:
                    HistoricoMensagemAutomatica.objects.create(
                        cliente=cliente,
                        mensagem_configurada=msg_config,
                        data_tentativa=now,
                        status='SEM_INSTANCIA',
                        detalhes='Dono sem instância WhatsApp conectada'
                    )
                    continue

                # 🔹 EVITA DUPLICIDADE
                ja_enviado = HistoricoMensagemAutomatica.objects.filter(
                    cliente=cliente,
                    mensagem_configurada=msg_config,
                    data_tentativa__gte=janela_inicio
                ).exists()

                if ja_enviado:
                    continue

                # 🔹 TENTA SUBSTITUIR VARIÁVEIS (ANTES DE CRIAR HISTÓRICO)
                try:
                    mensagem = msg_config.substituir_variaveis(cliente)
                    
                    if not mensagem or not mensagem.strip():
                        # Registra falha específica para mensagem vazia
                        HistoricoMensagemAutomatica.objects.create(
                            cliente=cliente,
                            mensagem_configurada=msg_config,
                            data_tentativa=now,
                            status='FALHA_VARIAVEIS',
                            detalhes='Mensagem vazia após substituição de variáveis'
                        )
                        continue
                        
                except KeyError as e:
                    # ⚠️ VARIÁVEL FALTANTE: Tenta gerar mensagem sem a variável
                    try:
                        # Extrai o nome da variável faltante
                        error_msg = str(e)
                        missing_var_match = re.search(r"Variável '(.+?)'", error_msg)
                        
                        if missing_var_match:
                            missing_var = missing_var_match.group(1)
                            logger.warning(f"⚠️ Variável '{missing_var}' não encontrada para cliente {cliente.id}. Removendo do template.")
                            
                            # Tenta criar a mensagem sem a variável problemática
                            mensagem_template = msg_config.mensagem_texto
                            
                            # Remove a variável faltante do template
                            placeholder = f"{{{missing_var}}}"
                            mensagem_template = mensagem_template.replace(placeholder, "")
                            
                            # Remove espaços extras que podem ter ficado
                            mensagem_template = mensagem_template.replace("  ", " ").strip()
                            
                            # Tenta formatar novamente com o template corrigido
                            hora_atual = timezone.localtime(timezone.now()).hour
                            
                            if 5 <= hora_atual < 12:
                                saudacao = "Bom dia"
                            elif 12 <= hora_atual < 18:
                                saudacao = "Boa tarde"
                            else:
                                saudacao = "Boa noite"
                            
                            # Contexto básico
                            context = {
                                'nome': cliente.nome or cliente.username,
                                'data_vencimento': cliente.data_vencimento.strftime('%d/%m/%Y') if cliente.data_vencimento else '',
                                'saudacao': saudacao,
                                'whatsapp': cliente.whatsapp or '',
                                'usuario': cliente.username,
                            }
                            
                            # Substitui variáveis básicas
                            mensagem = mensagem_template
                            for key, value in context.items():
                                placeholder = f"{{{key}}}"
                                mensagem = mensagem.replace(placeholder, str(value))
                            
                            if not mensagem.strip():
                                raise ValueError("Mensagem vazia após remoção da variável")
                                
                            # Registra que a variável foi removida
                            detalhes = f"Variável '{missing_var}' removida (não encontrada)"
                            
                        else:
                            # Se não conseguir identificar a variável, usa fallback
                            raise e
                            
                    except Exception as fallback_error:
                        # Se não conseguir gerar mensagem alternativa, registra falha
                        HistoricoMensagemAutomatica.objects.create(
                            cliente=cliente,
                            mensagem_configurada=msg_config,
                            data_tentativa=now,
                            status='FALHA_VARIAVEIS',
                            detalhes=f'Erro ao gerar mensagem: {fallback_error}'
                        )
                        continue
                        
                except Exception as e:
                    # Outro erro na substituição de variáveis
                    HistoricoMensagemAutomatica.objects.create(
                        cliente=cliente,
                        mensagem_configurada=msg_config,
                        data_tentativa=now,
                        status='FALHA_VARIAVEIS',
                        detalhes=f'Erro ao processar variáveis: {str(e)}'
                    )
                    continue

                # 🔹 VALIDA E FORMATA O NÚMERO DE TELEFONE
                numero_formatado, erro_numero = validar_e_formatar_numero(cliente.whatsapp)
                
                if not numero_formatado:
                    # Registra falha se o número for inválido
                    HistoricoMensagemAutomatica.objects.create(
                        cliente=cliente,
                        mensagem_configurada=msg_config,
                        data_tentativa=now,
                        status='NUMERO_INVALIDO',
                        detalhes=erro_numero
                    )
                    continue

                # 🔹 SÓ CHEGA AQUI SE A MENSAGEM FOI GERADA E NÚMERO É VÁLIDO
                with transaction.atomic():
                    historico = HistoricoMensagemAutomatica.objects.create(
                        cliente=cliente,
                        mensagem_configurada=msg_config,
                        data_tentativa=now,
                        status='ENVIANDO',
                        mensagem_final_enviada=mensagem  # Já salva a mensagem gerada
                    )

                    # Adiciona detalhes se houve remoção de variável
                    if 'detalhes' in locals():
                        historico.detalhes = detalhes

                    try:
                        url = f"{EVO_BASE_URL}/message/sendText/{instancia.instance_name}"
                        payload = {
                            "number": numero_formatado,  # ✅ Usa número formatado
                            "options": {"delay": 500, "waitForAck": False},
                            "text": mensagem
                        }

                        response = requests.post(
                            url,
                            json=payload,
                            headers=EVO_HEADERS,
                            timeout=EVO_TIMEOUT_SECONDS
                        )
                        response.raise_for_status()
                        data = response.json()

                        historico.status = 'ENVIADO'
                        historico.api_message_id = (
                            data.get('id')
                            or data.get('messageId')
                            or data.get('key', {}).get('id')
                        )
                        historico.data_envio = timezone.now()
                        historico.save()

                    except Exception as e:
                        historico.status = 'FALHA'
                        historico.detalhes = str(e)
                        historico.save()

        self.stdout.write(self.style.SUCCESS("✅ Envio de mensagens agendadas finalizado com sucesso."))
        logger.info("🏁 Comando finalizado")
