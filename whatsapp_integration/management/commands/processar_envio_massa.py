# -*- coding: utf-8 -*-
import logging
import time
import re
from django.core.management.base import BaseCommand
from django.utils import timezone
import requests
from django.conf import settings
from django.db import connection
from django.core.cache import cache
from whatsapp_integration.models import MensagemMassa, HistoricoEnvioMassa, UserInstance

import os
import base64


from clientes.message_variables import (
    substituir_variaveis_mensagem,
)

logger = logging.getLogger(__name__)

# CONFIGURAÇÕES DE SEGURANÇA
class ConfigSeguranca:
    LIMITE_LOTE = 10
    DELAY_ENTRE_MSGS = 2
    JANELA_DUPLICIDADE = 30
    TIMEOUT_API = 30
    MAX_RETRIES = 3
    DELAY_RETRY = 5
    LOCK_ID = 847201553  # advisory lock PostgreSQL para impedir execuções simultâneas

class Command(BaseCommand):
    help = 'Processa mensagens em massa usando API centralizada do Evolution'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--campanha-id',
            type=int,
            help='Processar apenas campanha específica',
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=ConfigSeguranca.LIMITE_LOTE,
            help=f'Limite de mensagens por lote',
        )
        parser.add_argument(
            '--teste',
            action='store_true',
            help='Modo teste (não envia, apenas simula)',
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Modo debug com mais informações',
        )

    def handle(self, *args, **options):
        self.modo_teste = options['teste']
        self.limite_lote = options['limite']
        self.campanha_id = options['campanha_id']
        self.debug = options['debug']
        
        # Verifica configurações essenciais antes de adquirir o lock.
        if not self.verificar_configuracoes():
            self._falhar_campanha_inicial(
                'URL ou API Key da Evolution não configurada para esta instalação/instância.'
            )
            return

        if not self._adquirir_lock_global():
            motivo = 'Outro envio em massa já está sendo processado. Aguarde a conclusão e tente novamente.'
            self.stdout.write(motivo)
            self._falhar_campanha_inicial(motivo)
            return
        
        self.stdout.write(self.style.SUCCESS(
            f"[{timezone.now()}] --- INICIANDO PROCESSAMENTO ---"
        ))
        if self.modo_teste:
            self.stdout.write(self.style.WARNING("⚠️  MODO TESTE ATIVADO"))
        
        try:
            self.processar_campanhas()
        except Exception:
            logger.exception("Erro inesperado no processamento de envio em massa")
            motivo = 'Erro interno inesperado durante o envio. Consulte o log do servidor.'
            self._falhar_campanha_inicial(motivo)
            self.stdout.write(self.style.ERROR(motivo))
        finally:
            self._liberar_lock_global()

    def _falhar_campanha_inicial(self, motivo):
        """Registra falha antes do processamento para a interface poder exibi-la."""
        if not getattr(self, 'campanha_id', None):
            return
        try:
            campanha = MensagemMassa.objects.filter(id=self.campanha_id).first()
            if not campanha or campanha.status in ['concluida', 'cancelada']:
                return
            campanha.status = 'falha'
            campanha.data_envio_fim = timezone.now()
            campanha.save(update_fields=['status', 'data_envio_fim'])
            HistoricoEnvioMassa.objects.filter(
                mensagem_massa=campanha, status='pendente'
            ).update(status='falha', mensagem_erro=motivo)
        except Exception:
            logger.exception('Não foi possível registrar falha inicial da campanha %s', self.campanha_id)

    def _marcar_campanha_falha(self, campanha, motivo):
        campanha.status = 'falha'
        campanha.data_envio_fim = timezone.now()
        campanha.save(update_fields=['status', 'data_envio_fim'])
        HistoricoEnvioMassa.objects.filter(
            mensagem_massa=campanha, status='pendente'
        ).update(status='falha', mensagem_erro=motivo[:240])

    def _adquirir_lock_global(self):
        """Impede execuções simultâneas em PostgreSQL e outros bancos."""
        if connection.vendor == 'postgresql':
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_try_advisory_lock(%s)', [ConfigSeguranca.LOCK_ID])
                    row = cursor.fetchone()
                self._lock_backend = 'postgresql'
                return bool(row and row[0])
            except Exception as exc:
                logger.error('Não foi possível adquirir advisory lock: %s', exc)
                return False

        self._cache_lock_key = 'envio_massa:processador:lock'
        adquirido = cache.add(self._cache_lock_key, str(time.time()), timeout=60 * 60)
        self._lock_backend = 'cache' if adquirido else None
        return bool(adquirido)

    def _liberar_lock_global(self):
        try:
            if getattr(self, '_lock_backend', None) == 'postgresql':
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock(%s)', [ConfigSeguranca.LOCK_ID])
            elif getattr(self, '_lock_backend', None) == 'cache':
                cache.delete(getattr(self, '_cache_lock_key', 'envio_massa:processador:lock'))
        except Exception as exc:
            logger.warning('Não foi possível liberar lock do envio em massa: %s', exc)

    @staticmethod
    def _resolver_evolution(instancia=None):
        global_url = str(getattr(settings, 'EVOLUTION_API_BASE_URL', '') or '').strip().rstrip('/')
        global_key = str(getattr(settings, 'EVOLUTION_GLOBAL_API_KEY', '') or '').strip()
        instance_url = str(getattr(instancia, 'base_url', '') or '').strip().rstrip('/') if instancia else ''
        instance_key = str(getattr(instancia, 'api_key', '') or '').strip() if instancia else ''

        # localhost é o default legado do modelo. Se existe uma URL global real,
        # ela deve vencer esse placeholder. Para uma URL realmente específica da
        # instância, a chave específica continua tendo prioridade; caso contrário,
        # a configuração global é a fonte de verdade.
        placeholder = instance_url in {
            'http://localhost:8080', 'https://localhost:8080',
            'http://127.0.0.1:8080', 'https://127.0.0.1:8080'
        }
        usa_url_especifica = bool(instance_url and not placeholder and instance_url != global_url)
        base_url = instance_url if usa_url_especifica else (global_url or instance_url)
        api_key = (instance_key if usa_url_especifica and instance_key else None) or global_key or instance_key
        return base_url.rstrip('/'), api_key

    def verificar_configuracoes(self):
        """Aceita configuração global ou configuração válida na instância."""
        base_url, api_key = self._resolver_evolution()
        if base_url and api_key:
            return True

        for instancia in UserInstance.objects.filter(is_active=True, status='connected').only('base_url', 'api_key'):
            url_instancia, key_instancia = self._resolver_evolution(instancia)
            if url_instancia and key_instancia:
                return True

        self.stderr.write(self.style.ERROR(
            'Processamento cancelado. Configure a URL/API Key da Evolution globalmente ou na instância.'
        ))
        return False

    def processar_campanhas(self):
        """Busca e processa campanhas pendentes"""
        
        agora = timezone.now()
        
        query = MensagemMassa.objects.filter(
            status__in=['agendada', 'enviando'],
            data_agendamento__lte=agora
        )
        
        if self.campanha_id:
            query = query.filter(id=self.campanha_id)
            self.stdout.write(f"Processando campanha ID: {self.campanha_id}")
        
        campanhas = query.order_by('data_agendamento')
        
        if not campanhas.exists():
            self.stdout.write("✅ Nenhuma campanha pendente.")
            return
        
        self.stdout.write(f"📋 Encontradas {campanhas.count()} campanha(s)")
        
        total_processadas = 0
        for campanha in campanhas:
            try:
                if self.processar_campanha(campanha):
                    total_processadas += 1
            except Exception:
                logger.exception('Erro inesperado ao processar campanha %s', campanha.id)
                motivo = 'Erro interno inesperado durante o envio. Consulte o log do servidor.'
                self._marcar_campanha_falha(campanha, motivo)
                self.stdout.write(self.style.ERROR(f"❌ {motivo}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"✅ Concluído: {total_processadas} campanha(s) processada(s)"
        ))

    def processar_campanha(self, campanha):
        """Processa uma campanha"""
        
        self.stdout.write(f"\n🎯 Campanha ID: {campanha.id}")
        self.stdout.write(f"   📝 Remetente: {campanha.remetente}")
        self.stdout.write(f"   📅 Agendada para: {campanha.data_agendamento}")
        
        # Conta clientes
        total_clientes = HistoricoEnvioMassa.objects.filter(mensagem_massa=campanha).count()
        self.stdout.write(f"   👥 Clientes: {total_clientes}")
        
        if campanha.status in ['concluida', 'falha']:
            self.stdout.write(f"   ⏭️  Já finalizada ({campanha.status})")
            return False
        
        # Atualiza status
        if campanha.status == 'agendada':
            campanha.status = 'enviando'
            campanha.data_envio_inicio = timezone.now()
            campanha.save(update_fields=['status', 'data_envio_inicio'])
            self.stdout.write(f"   📤 Iniciando envio...")
        
        # Verifica instância
        instancia = UserInstance.objects.filter(
            user=campanha.remetente, 
            status='connected',
            is_active=True
        ).first()
        
        if not instancia:
            motivo = 'Instância do WhatsApp não encontrada ou desconectada.'
            self.stdout.write(self.style.ERROR(f"   ❌ {motivo}"))
            self._marcar_campanha_falha(campanha, motivo)
            return False
        
        self.stdout.write(f"   📱 Instância: {instancia.instance_name}")
        
        # Verifica conexão com API. Falhas precisam aparecer no status da
        # campanha para a interface não ficar presa em "Enviando".
        if not self.verificar_conexao_api(instancia):
            motivo = getattr(self, 'ultimo_erro_api', '') or 'Não foi possível conectar/autenticar na Evolution API.'
            self._marcar_campanha_falha(campanha, motivo)
            return False
        
        # Processa em lotes
        while True:
            itens_lote = self.obter_lote_pendentes(campanha)
            
            if not itens_lote:
                self.finalizar_campanha(campanha)
                return True
            
            self.stdout.write(f"\n   📨 Lote: {len(itens_lote)} mensagem(s)")
            
            resultados = self.processar_lote_mensagens(campanha, itens_lote, instancia)
            
            # Atualiza estatísticas
            self.atualizar_estatisticas(campanha, resultados)
            
            # Verifica se acabou
            pendentes = HistoricoEnvioMassa.objects.filter(
                mensagem_massa=campanha, 
                status='pendente'
            ).count()
            
            if pendentes == 0:
                self.finalizar_campanha(campanha)
                return True
            else:
                self.stdout.write(f"   ⏳ Aguardando... {pendentes} pendente(s)")
                time.sleep(5)

    def verificar_conexao_api(self, instancia):
        """Verifica a Evolution e guarda um erro amigável para a interface."""
        base_url, api_key_resolvida = self._resolver_evolution(instancia)
        self.ultimo_erro_api = ''

        if not base_url:
            self.ultimo_erro_api = 'URL da Evolution API não configurada.'
            self.stdout.write(self.style.ERROR(f"   ❌ {self.ultimo_erro_api}"))
            return False
        if not api_key_resolvida:
            self.ultimo_erro_api = 'API Key da Evolution não configurada.'
            self.stdout.write(self.style.ERROR(f"   ❌ {self.ultimo_erro_api}"))
            return False

        try:
            url = f"{base_url}/instance/fetchInstances"
            if self.debug:
                self.stdout.write(f"   🔗 Testando conexão: {base_url}")
            response = requests.get(url, headers={"apikey": api_key_resolvida}, timeout=10)

            if response.status_code == 200:
                self.stdout.write("   ✅ API conectada com sucesso")
                return True

            if response.status_code in (401, 403):
                self.ultimo_erro_api = f'API Key da Evolution recusada (HTTP {response.status_code}).'
            else:
                self.ultimo_erro_api = f'Evolution API respondeu HTTP {response.status_code}.'
            self.stdout.write(self.style.ERROR(f"   ❌ {self.ultimo_erro_api}"))
            return False
        except requests.exceptions.Timeout:
            self.ultimo_erro_api = 'A Evolution API demorou demais para responder.'
            self.stdout.write(self.style.ERROR(f"   ❌ {self.ultimo_erro_api}"))
            return False
        except requests.exceptions.ConnectionError:
            self.ultimo_erro_api = 'Não foi possível acessar a URL configurada da Evolution API.'
            self.stdout.write(self.style.ERROR(f"   ❌ {self.ultimo_erro_api}"))
            return False
        except requests.RequestException:
            self.ultimo_erro_api = 'Falha de comunicação com a Evolution API.'
            logger.exception('Erro HTTP ao verificar Evolution para campanha')
            return False
        except Exception:
            self.ultimo_erro_api = 'Erro interno ao verificar a conexão com a Evolution API.'
            logger.exception('Erro inesperado ao verificar Evolution')
            return False

    def obter_lote_pendentes(self, campanha):
        """Obtém lote de mensagens pendentes"""
        
        return HistoricoEnvioMassa.objects.filter(
            mensagem_massa=campanha,
            status='pendente'
        ).select_related('cliente')[:self.limite_lote]

    def processar_lote_mensagens(self, campanha, itens_lote, instancia):
        """Processa um lote de mensagens"""
        
        resultados = {'sucesso': 0, 'falha': 0, 'ignorado': 0}
        
        for index, item in enumerate(itens_lote):
            try:
                resultado = self.enviar_mensagem(item, campanha, instancia)
                resultados[resultado] += 1
            except Exception:
                logger.exception("Erro inesperado no item de envio %s", item.id)
                item.status = 'falha'
                item.mensagem_erro = 'Erro interno ao processar este destinatário.'
                item.save(update_fields=['status', 'mensagem_erro'])
                resultados['falha'] += 1
            
            # Delay entre mensagens
            if index < len(itens_lote) - 1:
                time.sleep(ConfigSeguranca.DELAY_ENTRE_MSGS)
        
        return resultados

    def enviar_mensagem(self, item, campanha, instancia):
        """Envia uma mensagem para cliente cadastrado ou número avulso."""

        nome_destinatario = (
            getattr(item.cliente, "nome", None)
            or getattr(item.cliente, "first_name", None)
            or "Número avulso"
        )

        # Cliente cadastrado recebe substituição de variáveis.
        # Número avulso recebe exatamente o texto digitado.
        if item.cliente_id:
            texto = substituir_variaveis_mensagem(
                campanha.mensagem,
                item.cliente
            )
        else:
            texto = campanha.mensagem

        numero = re.sub(r"\D", "", str(item.whatsapp or ""))

        if not numero:
            item.status = "falha"
            item.mensagem_erro = "Número inválido"
            item.save(update_fields=["status", "mensagem_erro"])
            return "ignorado"

        if not numero.startswith("55") and len(numero) in (10, 11):
            numero = f"55{numero}"

        if len(numero) < 12 or len(numero) > 15:
            item.status = "falha"
            item.mensagem_erro = "Número fora do padrão esperado"
            item.save(update_fields=["status", "mensagem_erro"])
            return "ignorado"

        if self.modo_teste:
            self.stdout.write(
                f"   🔸 TESTE: {nome_destinatario} ({numero})"
            )
            item.status = "enviado"
            item.data_confirmacao = timezone.now()
            item.mensagem_erro = ""
            item.save(
                update_fields=[
                    "status",
                    "data_confirmacao",
                    "mensagem_erro",
                ]
            )
            return "sucesso"

        if self.debug:
            self.stdout.write(
                f"\n   Processando histórico id={item.id} "
                f"cliente_id={item.cliente_id or 'avulso'}"
            )

        base_url, api_key = self._resolver_evolution(instancia)

        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
        }

        if campanha.midia:
            try:
                url = (
                    f"{base_url}/message/sendMedia/"
                    f"{instancia.instance_name}"
                )

                nome_arquivo = os.path.basename(campanha.midia.name)
                extensao = nome_arquivo.rsplit(".", 1)[-1].lower()
                tipo_media = self.determinar_tipo_midia(extensao)

                campanha.midia.open("rb")
                try:
                    conteudo_arquivo = campanha.midia.read()
                finally:
                    campanha.midia.close()

                media_base64 = base64.b64encode(
                    conteudo_arquivo
                ).decode("utf-8")

                payload = {
                    "number": numero,
                    "mediatype": tipo_media,
                    "media": media_base64,
                    "caption": texto,
                }

                if tipo_media == "document":
                    payload["fileName"] = nome_arquivo

            except Exception:
                logger.exception(
                    "Erro ao preparar mídia da campanha id=%s para histórico id=%s",
                    campanha.id,
                    item.id,
                )
                item.status = "falha"
                item.mensagem_erro = "Não foi possível preparar a mídia da campanha."
                item.save(update_fields=["status", "mensagem_erro"])
                return "falha"
        else:
            url = (
                f"{base_url}/message/sendText/"
                f"{instancia.instance_name}"
            )
            payload = {
                "number": numero,
                "text": texto,
            }

        if self.debug:
            self.stdout.write(
                f"   Endpoint preparado para instância={instancia.instance_name}; "
                f"mídia={'sim' if campanha.midia else 'não'}"
            )

        ultimo_erro = ""

        for tentativa in range(ConfigSeguranca.MAX_RETRIES):
            try:
                if self.debug:
                    self.stdout.write(
                        "   🔄 Tentativa "
                        f"{tentativa + 1}/"
                        f"{ConfigSeguranca.MAX_RETRIES}"
                    )

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=ConfigSeguranca.TIMEOUT_API,
                )

                if self.debug:
                    self.stdout.write(
                        f"   📡 Status HTTP: {response.status_code}"
                    )

                if response.status_code in (200, 201):
                    try:
                        resp_json = response.json()
                    except ValueError:
                        resp_json = {}

                    status_api = str(
                        resp_json.get("status", "")
                    ).upper()

                    # Algumas versões retornam sucesso sem campo status,
                    # mas trazem key.id ou id da mensagem.
                    message_id = (
                        resp_json.get("id")
                        or resp_json.get("messageId")
                        or resp_json.get("key", {}).get("id")
                        or resp_json.get("messageID")
                        or resp_json.get("_id")
                    )

                    sucesso_api = (
                        status_api in {
                            "SUCCESS",
                            "PENDING",
                            "SENT",
                            "DELIVERED",
                            "ACK",
                        }
                        or bool(message_id)
                        or response.status_code in (200, 201)
                    )

                    if sucesso_api:
                        item.status = "enviado"
                        item.data_confirmacao = timezone.now()
                        item.mensagem_erro = ""

                        if message_id:
                            item.message_id = str(message_id)

                        item.save(
                            update_fields=[
                                "status",
                                "data_confirmacao",
                                "mensagem_erro",
                                "message_id",
                            ]
                        )

                        self.stdout.write(
                            f"   ✅ {nome_destinatario}: enviado"
                        )
                        return "sucesso"

                    ultimo_erro = (
                        resp_json.get("message")
                        or f"Status inesperado: {status_api}"
                    )
                else:
                    ultimo_erro = (
                        f"HTTP {response.status_code}: "
                        f"{response.text[:200]}"
                    )

                if tentativa == 0 and "text" in payload:
                    payload = {
                        "number": numero,
                        "options": {
                            "delay": 500,
                            "waitForAck": False,
                        },
                        "textMessage": {
                            "text": texto,
                        },
                    }
                    self.stdout.write(
                        "   🔧 Tentando payload alternativo..."
                    )
                    continue

                if tentativa < ConfigSeguranca.MAX_RETRIES - 1:
                    time.sleep(ConfigSeguranca.DELAY_RETRY)

            except requests.exceptions.ConnectionError:
                ultimo_erro = "Não foi possível conectar à Evolution API."
            except requests.exceptions.Timeout:
                ultimo_erro = "Timeout na API"
            except Exception:
                logger.exception("Erro inesperado durante tentativa de envio do histórico %s", item.id)
                ultimo_erro = "Erro interno durante o envio."

            if tentativa < ConfigSeguranca.MAX_RETRIES - 1:
                time.sleep(ConfigSeguranca.DELAY_RETRY)

        item.status = "falha"
        item.mensagem_erro = (
            ultimo_erro[:500]
            or (
                "Falha após "
                f"{ConfigSeguranca.MAX_RETRIES} tentativas"
            )
        )
        item.save(update_fields=["status", "mensagem_erro"])

        self.stdout.write(
            f"   ❌ {nome_destinatario}: falha final"
        )
        return "falha"


    def obter_url_midia(self, arquivo_midia):
        """Obtém URL completa da mídia"""
        
        if not arquivo_midia:
            return ""
        
        try:
            # Usa SITE_URL das settings se existir
            if hasattr(settings, 'SITE_URL') and settings.SITE_URL:
                site_url = settings.SITE_URL.rstrip('/')
                media_path = arquivo_midia.url.lstrip('/')
                return f"{site_url}/{media_path}"
            else:
                return arquivo_midia.url
        except:
            return ""

    def determinar_tipo_midia(self, extensao):
        extensao = extensao.lower().replace(".", "")

        imagens = {
            "jpg", "jpeg", "png", "webp", "gif"
        }

        videos = {
            "mp4", "mov", "avi", "mkv", "webm"
        }

        audios = {
            "mp3", "ogg", "wav", "aac", "m4a", "opus"
        }

        if extensao in imagens:
            return "image"

        if extensao in videos:
            return "video"

        if extensao in audios:
            return "audio"

        return "document"

    
    def atualizar_estatisticas(self, campanha, resultados):
        """Atualiza estatísticas da campanha"""
        
        try:
            # Tenta atualizar campos se existirem
            if hasattr(campanha, 'enviados_com_sucesso'):
                campanha.enviados_com_sucesso += resultados['sucesso']
                campanha.save()
            
            self.stdout.write(f"   📊 Lote: ✅ {resultados['sucesso']} | ❌ {resultados['falha']}")
        except:
            self.stdout.write(f"   📊 Lote concluído")

    def finalizar_campanha(self, campanha):
        """Finaliza a campanha"""
        
        campanha.status = 'concluida'
        campanha.data_envio_fim = timezone.now()
        campanha.save(update_fields=['status', 'data_envio_fim'])
        
        # Conta estatísticas finais
        sucesso = HistoricoEnvioMassa.objects.filter(
            mensagem_massa=campanha, 
            status='enviado'
        ).count()
        
        total = HistoricoEnvioMassa.objects.filter(mensagem_massa=campanha).count()
        taxa = (sucesso / total * 100) if total > 0 else 0
        
        self.stdout.write(self.style.SUCCESS(
            f"   🏁 Campanha {campanha.id} CONCLUÍDA!"
        ))
        self.stdout.write(f"      📈 Sucesso: {sucesso}/{total} ({taxa:.1f}%)")