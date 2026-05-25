# -*- coding: utf-8 -*-
import logging
import re
import requests
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.db import transaction

from ...models import ConfiguracaoWhatsApp, HistoricoNotificacaoAlmoxarifado, Item
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

    def handle(self, *args, **options):
        logger.info("🚀 Iniciando comando de envio de notificações do almoxarifado")
        
        now = timezone.localtime(timezone.now())
        hora_atual = now.strftime('%H:%M')
        dia_semana = now.weekday()
        dia_semana_django = 0 if dia_semana == 6 else dia_semana + 1
        
        # Obter configuração do banco de dados
        config = ConfiguracaoWhatsApp.get_config()
        
        # Converter horario_agendado para string se for objeto time
        horario_raw = getattr(config, 'horario_agendado', '08:00')
        if hasattr(horario_raw, 'strftime'):
            horario_agendado = horario_raw.strftime('%H:%M')
        else:
            horario_agendado = str(horario_raw)
        
        tipo_envio = getattr(config, 'tipo_envio', 'tempo-real')
        dias_semana = getattr(config, 'dias_semana', [1, 2, 3, 4, 5])
        
        self.stdout.write(f"📱 Configuração carregada:")
        self.stdout.write(f"   Ativo: {config.ativo}")
        self.stdout.write(f"   Instance Name: {config.instance_name}")
        self.stdout.write(f"   API URL: {config.api_url}")
        self.stdout.write(f"   Tipo Envio: {tipo_envio}")
        self.stdout.write(f"   Horário Agendado: {horario_agendado}")
        self.stdout.write(f"   Dias Semana: {dias_semana}")
        
        if not config.ativo:
            self.stdout.write("⚠️ Sistema de notificações desativado")
            return
        
        if not config.instance_name:
            self.stdout.write("❌ Nenhuma instância WhatsApp configurada! Configure no modal.")
            return
        
        if not config.api_url:
            self.stdout.write("❌ URL da API não configurada! Configure no modal.")
            return
        
        # Verificar se deve enviar agora (agendamento)
        enviar_agora = options['now']
        
        if not enviar_agora:
            if tipo_envio == 'tempo-real':
                self.stdout.write("⏭️ Modo apenas tempo real - não enviando via comando")
                return
            
            if tipo_envio in ['agendado', 'ambos']:
                # Tolerância de 30 minutos
                try:
                    hora_agendada = datetime.strptime(horario_agendado, '%H:%M')
                    hora_atual_obj = datetime.strptime(hora_atual, '%H:%M')
                    diff_minutos = abs((hora_atual_obj - hora_agendada).total_seconds() / 60)
                except Exception as e:
                    self.stdout.write(f"⚠️ Erro ao processar horário: {e}")
                    diff_minutos = 999
                
                if diff_minutos > 30:
                    self.stdout.write(f"⏭️ Horário não corresponde: {hora_atual} != {horario_agendado} (dif: {diff_minutos:.0f}min)")
                    return
                
                if dia_semana_django not in dias_semana:
                    self.stdout.write(f"⏭️ Dia não está na programação: {dia_semana_django}")
                    return
                
                # Verificar se já enviou nesta janela
                ultima_notif = getattr(config, 'ultima_notificacao_agendada', None)
                if ultima_notif:
                    diff_horas = (now - ultima_notif).total_seconds() / 3600
                    intervalo_repeticao = getattr(config, 'intervalo_repeticao', 24)
                    if diff_horas < intervalo_repeticao:
                        self.stdout.write(f"⏭️ Notificação já enviada há {diff_horas:.1f} horas")
                        return
        
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
            if item.quantidade <= 0:
                if item.departamento not in itens_por_departamento:
                    itens_por_departamento[item.departamento] = {'baixo': [], 'zerado': []}
                itens_por_departamento[item.departamento]['zerado'].append(item)
                itens_zerado_total += 1
            elif item.quantidade <= item.estoque_minimo:
                if item.departamento not in itens_por_departamento:
                    itens_por_departamento[item.departamento] = {'baixo': [], 'zerado': []}
                itens_por_departamento[item.departamento]['baixo'].append(item)
                itens_baixo_total += 1
        
        self.stdout.write(f"📊 Itens encontrados:")
        self.stdout.write(f"   Estoque baixo: {itens_baixo_total}")
        self.stdout.write(f"   Estoque zerado: {itens_zerado_total}")
        
        if itens_baixo_total == 0 and itens_zerado_total == 0:
            self.stdout.write("✅ Nenhum item com estoque crítico encontrado.")
            return
        
        # Enviar notificações AGRUPADAS por departamento
        service = get_notificacao_service()
        service._config = None
        service.config
        
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
                lista_baixo.append(f"{item.nome}\n➜ {float(item.quantidade):.0f} {item.get_unidade_display()}\n")
            
            lista_zerado = []
            for item in itens['zerado']:
                lista_zerado.append(f"{item.nome}\n➜ 0 {item.get_unidade_display()}\n")
            
            texto_baixo = '\n'.join(lista_baixo) if lista_baixo else 'Nenhum'
            texto_zerado = '\n'.join(lista_zerado) if lista_zerado else 'Nenhum'
            
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
                mensagem = f"""📊 *RESUMO DE ESTOQUE - {dept_nome}*
📅 {now.strftime('%d/%m/%Y %H:%M')}

⚠️ *ESTOQUE BAIXO:*
{texto_baixo}

🚨 *ITENS ZERADOS:*
{texto_zerado}

━━━━━━━━━━━━━━━━━━━━
📌 Total: {len(itens['baixo'])} baixo | {len(itens['zerado'])} zerado"""
            
            # Enviar para cada número do departamento
            for numero in numeros:
                try:
                    success, response = service.enviar_mensagem(numero, mensagem)
                    if success:
                        resultados.append({'numero': numero, 'success': True})
                        self.stdout.write(f"  ✅ Resumo enviado para {numero} ({dept_nome}) - {len(itens['baixo'])+len(itens['zerado'])} itens")
                    else:
                        self.stdout.write(f"  ❌ Falha ao enviar para {numero}: {response}")
                except Exception as e:
                    self.stdout.write(f"  ❌ Erro ao enviar para {numero}: {e}")
        
        # Atualizar data da última notificação
        if resultados and not enviar_agora and tipo_envio in ['agendado', 'ambos']:
            config.ultima_notificacao_agendada = now
            config.save()
            self.stdout.write(f"📝 Última notificação registrada: {now.strftime('%d/%m/%Y %H:%M:%S')}")
        
        self.stdout.write(self.style.SUCCESS(
            f"✅ Envio concluído! {len(resultados)} notificações enviadas."
        ))
        logger.info(f"🏁 Comando finalizado. {len(resultados)} notificações enviadas.")