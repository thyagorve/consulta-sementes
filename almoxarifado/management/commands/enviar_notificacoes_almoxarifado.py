# -*- coding: utf-8 -*-
import logging
import re
import requests
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from ...models import ConfiguracaoWhatsApp, HistoricoNotificacaoAlmoxarifado, Item, AgendamentoNotificacao
from ...services import get_notificacao_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Envia notificações agendadas do almoxarifado (estoque baixo/zerado)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--now',
            action='store_true',
            help='Envia notificações imediatamente (ignora agendamento)'
        )
        parser.add_argument(
            '--departamento',
            type=str,
            help='Envia apenas para um departamento específico'
        )
        parser.add_argument(
            '--tipo',
            type=str,
            choices=['baixo', 'zerado', 'reposicao', 'todos'],
            help='Tipo de notificação a enviar'
        )
        parser.add_argument(
            '--testar-conexao',
            type=str,
            help='Testa conexão com a API enviando mensagem para o número especificado'
        )

    def handle(self, *args, **options):
        logger.info("🚀 Iniciando comando de envio de notificações do almoxarifado")
        
        # Teste de conexão se solicitado
        if options.get('testar_conexao'):
            self.testar_conexao(options['testar_conexao'])
            return
        
        now = timezone.localtime(timezone.now())
        hora_atual = now.strftime('%H:%M')
        dia_semana = now.weekday()  # 0=segunda a 6=domingo
        
        # Obter configuração do banco de dados
        config = ConfiguracaoWhatsApp.get_config()
        
        tipo_envio = getattr(config, 'tipo_envio', 'tempo-real')
        
        self.stdout.write("=" * 60)
        self.stdout.write("📱 SISTEMA DE NOTIFICAÇÕES DO ALMOXARIFADO")
        self.stdout.write("=" * 60)
        self.stdout.write(f"📅 Data/Hora: {now.strftime('%d/%m/%Y %H:%M:%S')}")
        self.stdout.write(f"📱 Configuração:")
        self.stdout.write(f"   Ativo: {'✅ Sim' if config.ativo else '❌ Não'}")
        self.stdout.write(f"   Instance Name: {config.instance_name or '❌ Não configurada'}")
        self.stdout.write(f"   API URL: {config.api_url or '❌ Não configurada'}")
        self.stdout.write(f"   Tipo Envio: {tipo_envio}")
        self.stdout.write("=" * 60)
        
        # Validações básicas
        if not config.ativo:
            self.stdout.write(self.style.WARNING("⚠️ Sistema de notificações desativado. Ative nas configurações."))
            return
        
        if not config.instance_name:
            self.stdout.write(self.style.ERROR("❌ Nenhuma instância WhatsApp configurada! Configure no modal de WhatsApp."))
            return
        
        if not config.api_url:
            self.stdout.write(self.style.ERROR("❌ URL da API não configurada! Configure no modal de WhatsApp."))
            return
        
        # Verificar se deve enviar agora
        enviar_agora = options['now']
        
        if not enviar_agora:
            # Modo agendado - verificar múltiplos horários
            if tipo_envio == 'tempo-real':
                self.stdout.write(self.style.WARNING("⏭️ Modo apenas tempo real - não enviando via comando agendado"))
                self.stdout.write("   As notificações em tempo real são enviadas automaticamente quando o estoque muda.")
                return
            
            if tipo_envio in ['agendado', 'ambos']:
                # Obter todos os agendamentos ativos
                agendamentos = config.get_agendamentos_ativos()
                
                if not agendamentos.exists():
                    self.stdout.write(self.style.WARNING("⚠️ Nenhum horário agendado configurado!"))
                    self.stdout.write("   Adicione horários na aba 'Agendamento' do modal WhatsApp.")
                    return
                
                # Verificar se algum agendamento corresponde ao horário atual
                agendamento_encontrado = None
                
                for agendamento in agendamentos:
                    horario_ag = agendamento.horario.strftime('%H:%M')
                    
                    # Tolerância de 5 minutos para não perder o horário exato
                    try:
                        hora_agendada = datetime.strptime(horario_ag, '%H:%M')
                        hora_atual_obj = datetime.strptime(hora_atual, '%H:%M')
                        diff_minutos = abs((hora_atual_obj - hora_agendada).total_seconds() / 60)
                    except Exception as e:
                        self.stdout.write(f"⚠️ Erro ao processar horário {horario_ag}: {e}")
                        continue
                    
                    # Verificar se está dentro da janela de 5 minutos
                    if diff_minutos > 5:
                        continue
                    
                    # Verificar dias da semana (se configurado)
                    if agendamento.dias_semana and len(agendamento.dias_semana) > 0:
                        # No modelo: 0=domingo, 1=segunda... 6=sábado
                        # No Python: 0=segunda, 6=domingo
                        dia_ajustado = (dia_semana + 1) % 7  # Converte para o formato do modelo
                        if dia_ajustado not in agendamento.dias_semana:
                            self.stdout.write(f"⏭️ Horário {horario_ag} - Dia {dia_ajustado} não programado")
                            continue
                    
                    agendamento_encontrado = agendamento
                    self.stdout.write(f"✅ Horário correspondente: {horario_ag}")
                    break
                
                if not agendamento_encontrado:
                    self.stdout.write(f"⏭️ Nenhum horário agendado corresponde à {hora_atual}")
                    # Listar horários configurados para debug
                    horarios = [f"{a.horario.strftime('%H:%M')}" for a in agendamentos]
                    if horarios:
                        self.stdout.write(f"   Horários configurados: {', '.join(horarios)}")
                    return
                
                # Verificar repetição de notificações
                repetir_notificacoes = getattr(config, 'repetir_notificacoes', False)
                if not repetir_notificacoes:
                    ultima_notif = getattr(config, 'ultima_notificacao_agendada', None)
                    if ultima_notif:
                        diff_horas = (now - ultima_notif).total_seconds() / 3600
                        if diff_horas < 23:  # Menos de 23 horas
                            self.stdout.write(f"⏭️ Notificação já enviada há {diff_horas:.1f} horas")
                            self.stdout.write("   Ative 'Repetir Notificações' para enviar múltiplas vezes.")
                            return
        
        # Verificar status da instância WhatsApp
        self.stdout.write("🔌 Verificando status da instância...")
        service = get_notificacao_service()
        service._config = None
        service.config
        
        status = service.verificar_status_instancia(config.instance_name)
        if status != 'connected':
            self.stdout.write(self.style.WARNING(f"⚠️ Instância '{config.instance_name}' não está conectada! Status: {status}"))
            self.stdout.write("   Conecte o WhatsApp na aba 'Conexão' do modal.")
            if not enviar_agora:
                return
        
        self.stdout.write(f"✅ Instância conectada: {config.instance_name}")
        
        # Obter tipos de notificação ativos
        notificar_baixo = getattr(config, 'notificar_baixo', True)
        notificar_zerado = getattr(config, 'notificar_zerado', True)
        
        # Filtrar por tipo se especificado
        tipo_filtro = options.get('tipo')
        if tipo_filtro == 'baixo':
            notificar_zerado = False
        elif tipo_filtro == 'zerado':
            notificar_baixo = False
        
        # Obter departamentos ativos
        depts_ativos = getattr(config, 'departamentos_ativos', [])
        
        # Query base
        itens_query = Item.objects.filter(ativo=True)
        if depts_ativos:
            itens_query = itens_query.filter(departamento__in=depts_ativos)
        
        # Filtrar por departamento se especificado
        departamento_filtro = options.get('departamento')
        if departamento_filtro:
            itens_query = itens_query.filter(departamento=departamento_filtro)
        
        # Mapeamento dos departamentos para nomes legíveis
        dept_map = {
            'ADM': 'Administrativo',
            'PROD': 'Produção',
            'MAN': 'Manutenção',
            'TI': 'Tecnologia',
            'FAC': 'Facilities',
            'LAB': 'Laboratório',
            'LOG': 'Logística',
            'EPI': 'Segurança',
            'OUT': 'Outros',
        }
        
        # Classificar itens e agrupar por departamento
        itens_por_departamento = {}
        itens_baixo_total = 0
        itens_zerado_total = 0
        
        for item in itens_query:
            if item.quantidade <= 0 and notificar_zerado:
                if item.departamento not in itens_por_departamento:
                    itens_por_departamento[item.departamento] = {'baixo': [], 'zerado': []}
                itens_por_departamento[item.departamento]['zerado'].append(item)
                itens_zerado_total += 1
            elif item.quantidade <= item.estoque_minimo and notificar_baixo:
                if item.departamento not in itens_por_departamento:
                    itens_por_departamento[item.departamento] = {'baixo': [], 'zerado': []}
                itens_por_departamento[item.departamento]['baixo'].append(item)
                itens_baixo_total += 1
        
        self.stdout.write("\n📊 ITENS ENCONTRADOS:")
        self.stdout.write(f"   Estoque baixo: {itens_baixo_total}")
        self.stdout.write(f"   Estoque zerado: {itens_zerado_total}")
        
        if itens_baixo_total == 0 and itens_zerado_total == 0:
            self.stdout.write(self.style.SUCCESS("✅ Nenhum item com estoque crítico encontrado."))
            return
        
        # Enviar notificações AGRUPADAS por departamento
        resultados = []
        
        # Template de resumo
        template_resumo = getattr(config, 'template_resumo', None)
        
        # Para cada departamento com itens, enviar UMA mensagem
        for dept, itens in itens_por_departamento.items():
            if not itens['baixo'] and not itens['zerado']:
                continue
            
            # Obter números do departamento
            numeros = config.get_numeros_destino(dept)
            if not numeros:
                self.stdout.write(f"⚠️ Nenhum número configurado para o departamento {dept}")
                continue
            
            # Montar mensagem única
            dept_nome = dept_map.get(dept, dept)
            
            # Criar listas formatadas
            lista_baixo = []
            for item in itens['baixo']:
                lista_baixo.append(f"• *{item.nome}*\n  ➜ {float(item.quantidade):.0f} {item.get_unidade_display()} (mín: {float(item.estoque_minimo):.0f})")
            
            lista_zerado = []
            for item in itens['zerado']:
                lista_zerado.append(f"• *{item.nome}*\n  ➜ 0 {item.get_unidade_display()} 🚨")
            
            texto_baixo = '\n\n'.join(lista_baixo) if lista_baixo else '✅ Nenhum'
            texto_zerado = '\n\n'.join(lista_zerado) if lista_zerado else '✅ Nenhum'
            
            # Construir mensagem
            if template_resumo:
                mensagem = template_resumo
                contexto = {
                    'data': now.strftime('%d/%m/%Y %H:%M'),
                    'departamento': dept_nome,
                    'total_baixo': len(itens['baixo']),
                    'total_zerado': len(itens['zerado']),
                    'lista_baixo': texto_baixo,
                    'lista_zerado': texto_zerado,
                }
                for key, value in contexto.items():
                    mensagem = mensagem.replace(f"{{{key}}}", str(value))
            else:
                # Template padrão
                mensagem = f"""📊 *RESUMO DE ESTOQUE - {dept_nome}*
📅 {now.strftime('%d/%m/%Y %H:%M')}

━━━━━━━━━━━━━━━━━━━━

⚠️ *ESTOQUE BAIXO:* ({len(itens['baixo'])})
{texto_baixo}

🚨 *ITENS ZERADOS:* ({len(itens['zerado'])})
{texto_zerado}

━━━━━━━━━━━━━━━━━━━━
🔔 Este é um resumo automático do sistema de Almoxarifado.
📱 Para mais detalhes, acesse o sistema."""
            
            # Enviar para cada número do departamento
            for numero in numeros:
                try:
                    self.stdout.write(f"📤 Enviando para {numero} ({dept_nome})...")
                    
                    # Registrar no histórico
                    try:
                        HistoricoNotificacaoAlmoxarifado.objects.create(
                            item=itens['baixo'][0] if itens['baixo'] else itens['zerado'][0],
                            tipo='baixo' if itens['baixo'] else 'zerado',
                            destinatario=numero,
                            mensagem=mensagem[:500],
                            status='pendente'
                        )
                    except Exception as hist_error:
                        self.stdout.write(f"   ⚠️ Erro ao registrar histórico: {hist_error}")
                    
                    # Enviar mensagem
                    success, response = service.enviar_mensagem(numero, mensagem)
                    
                    if success:
                        resultados.append({'numero': numero, 'success': True})
                        self.stdout.write(self.style.SUCCESS(f"  ✅ Resumo enviado para {numero}"))
                        
                        # Atualizar histórico
                        try:
                            hist = HistoricoNotificacaoAlmoxarifado.objects.filter(
                                destinatario=numero,
                                status='pendente'
                            ).last()
                            if hist:
                                hist.status = 'enviado'
                                hist.enviado_em = timezone.now()
                                hist.save()
                        except:
                            pass
                    else:
                        self.stdout.write(self.style.ERROR(f"  ❌ Falha ao enviar para {numero}: {response}"))
                        
                        # Atualizar histórico com erro
                        try:
                            hist = HistoricoNotificacaoAlmoxarifado.objects.filter(
                                destinatario=numero,
                                status='pendente'
                            ).last()
                            if hist:
                                hist.status = 'erro'
                                hist.erro = str(response)[:500]
                                hist.save()
                        except:
                            pass
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Erro ao enviar para {numero}: {e}"))
        
        # Atualizar data da última notificação (apenas para modo agendado)
        if resultados and not enviar_agora and tipo_envio in ['agendado', 'ambos']:
            config.ultima_notificacao_agendada = now
            config.save()
            self.stdout.write(f"\n📝 Última notificação registrada: {now.strftime('%d/%m/%Y %H:%M:%S')}")
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(
            f"✅ ENVIO CONCLUÍDO! {len(resultados)} notificações enviadas."
        ))
        self.stdout.write("=" * 60)
        
        logger.info(f"🏁 Comando finalizado. {len(resultados)} notificações enviadas.")

    def testar_conexao(self, numero):
        """Testa a conexão com a API enviando uma mensagem de teste"""
        self.stdout.write("=" * 60)
        self.stdout.write("🧪 TESTE DE CONEXÃO WHATSAPP")
        self.stdout.write("=" * 60)
        
        config = ConfiguracaoWhatsApp.get_config()
        
        if not config.ativo:
            self.stdout.write(self.style.ERROR("❌ Sistema de notificações desativado"))
            return
        
        if not config.instance_name:
            self.stdout.write(self.style.ERROR("❌ Nenhuma instância configurada"))
            return
        
        if not config.api_url:
            self.stdout.write(self.style.ERROR("❌ URL da API não configurada"))
            return
        
        self.stdout.write(f"📱 Instância: {config.instance_name}")
        self.stdout.write(f"📞 Número de teste: {numero}")
        self.stdout.write("🔄 Enviando mensagem de teste...")
        
        service = get_notificacao_service()
        service._config = None
        service.config
        
        mensagem_teste = f"""🧪 *TESTE DE CONEXÃO - ALMOXARIFADO*

✅ Configuração funcionando corretamente!

📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
🔔 Sistema de notificações do Almoxarifado

📱 Instância: {config.instance_name}

---
*Se você recebeu esta mensagem, as notificações estão configuradas corretamente!*"""
        
        success, response = service.enviar_mensagem(numero, mensagem_teste)
        
        if success:
            self.stdout.write(self.style.SUCCESS("✅ Mensagem de teste enviada com sucesso!"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ Falha ao enviar: {response}"))
        
        self.stdout.write("=" * 60)