# clientes/views_backup.py - VERSÃO FINAL COMPLETA (TELEGRAM)
import os
import subprocess
import gzip
import tempfile
import requests
import platform
from datetime import datetime, timedelta
from pathlib import Path
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.conf import settings
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from .models import BackupSchedule, BackupHistory, Configuracao
import logging

logger = logging.getLogger(__name__)


# ============================================
# FUNÇÕES DO TELEGRAM
# ============================================

# clientes/views_backup.py - Substitua a função get_telegram_config

def get_telegram_config(user=None):
    """
    Busca configuração do Telegram
    REGRA: SEMPRE usa a configuração do admin (Tiago Lima)
    Ignora a config do usuário logado
    """
    from clientes.models import CustomUser
    
    # Buscar admin (Tiago Lima)
    admin = CustomUser.objects.filter(
        tipo_usuario='admin',
        is_active=True
    ).first()
    
    if admin:
        config = Configuracao.objects.filter(usuario=admin).first()
        if config and config.token_telegram and config.chave_telegram:
            logger.info(f"📱 Usando config do admin: {admin.username}")
            return config.token_telegram.strip(), config.chave_telegram.strip()
    
    # Fallback: configuração global (sem usuário)
    config = Configuracao.objects.filter(
        usuario__isnull=True,
        token_telegram__isnull=False
    ).exclude(token_telegram='').first()
    
    if config and config.token_telegram and config.chave_telegram:
        logger.info("📱 Usando config global (fallback)")
        return config.token_telegram.strip(), config.chave_telegram.strip()
    
    # Último fallback: qualquer config preenchida
    config = Configuracao.objects.filter(
        token_telegram__isnull=False
    ).exclude(token_telegram='').first()
    
    if config:
        logger.info(f"📱 Usando config de: {config.usuario or 'Global'} (fallback)")
        return config.token_telegram.strip(), config.chave_telegram.strip()
    
    logger.error("❌ Nenhuma configuração do Telegram encontrada!")
    return None, None


def enviar_para_telegram(filepath, caption, user=None):
    """
    Envia arquivo de backup para o Telegram
    
    Args:
        filepath: Caminho completo do arquivo .gz
        caption: Legenda da mensagem
        user: Usuário para buscar configuração
    
    Returns:
        message_id (str) ou None se falhar
    """
    token, chat_id = get_telegram_config(user)
    
    if not token or not chat_id:
        logger.error("❌ Telegram não configurado (token ou chat_id vazio)")
        return None
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        
        with open(filepath, 'rb') as f:
            files = {
                'document': (os.path.basename(filepath), f, 'application/gzip')
            }
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            logger.info(f"📤 Enviando backup para Telegram... ({os.path.basename(filepath)})")
            
            response = requests.post(url, files=files, data=data, timeout=120)  # 2 minutos
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    message_id = str(result['result']['message_id'])
                    logger.info(f"✅ Backup enviado para Telegram! msg_id: {message_id}")
                    return message_id
                else:
                    logger.error(f"❌ Telegram retornou erro: {result.get('description')}")
            else:
                logger.error(f"❌ Erro HTTP Telegram: {response.status_code} - {response.text[:300]}")
                
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout ao enviar para Telegram (120s)")
    except requests.exceptions.ConnectionError:
        logger.error("❌ Erro de conexão com API do Telegram")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar para Telegram: {e}", exc_info=True)
    
    return None


def enviar_mensagem_telegram(texto, user=None):
    """
    Envia mensagem de texto para o Telegram
    
    Args:
        texto: Mensagem em formato HTML
        user: Usuário para buscar configuração
    
    Returns:
        message_id (str) ou None
    """
    token, chat_id = get_telegram_config(user)
    
    if not token or not chat_id:
        return None
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': texto,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                return str(result['result']['message_id'])
                
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem Telegram: {e}")
    
    return None


# ============================================
# FUNÇÕES DO POSTGRESQL
# ============================================

def get_pg_tools_path():
    """Encontra o caminho das ferramentas PostgreSQL (Windows/Linux)"""
    sistema = platform.system()
    
    if sistema == 'Windows':
        possiveis_caminhos = [
            r'C:\Program Files\PostgreSQL\16\bin',
            r'C:\Program Files\PostgreSQL\15\bin',
            r'C:\Program Files\PostgreSQL\14\bin',
            r'C:\Program Files\PostgreSQL\13\bin',
        ]
        for caminho in possiveis_caminhos:
            if os.path.exists(os.path.join(caminho, 'pg_dump.exe')):
                return caminho
        return None
    else:
        # Linux/Mac - pg_dump já está no PATH
        return None


def executar_comando_pg(comando, timeout=300):
    """
    Executa um comando PostgreSQL com ambiente configurado
    Compatível com Windows, Linux (Easypanel) e Mac
    """
    db = settings.DATABASES['default']
    pg_path = get_pg_tools_path()
    
    env = os.environ.copy()
    env['PGPASSWORD'] = db['PASSWORD']
    
    if pg_path and platform.system() == 'Windows':
        env['PATH'] = pg_path + ';' + env.get('PATH', '')
        cmd = [os.path.join(pg_path, comando[0] + '.exe')] + list(comando[1:])
    else:
        cmd = comando
    
    # Log do comando (sem senha)
    cmd_log = ' '.join(str(c) for c in cmd)
    cmd_log = cmd_log.replace(db['PASSWORD'], '***') if db['PASSWORD'] else cmd_log
    logger.info(f"🔧 Executando: {cmd_log}")
    
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)


# ============================================
# VIEWS PRINCIPAIS
# ============================================

@login_required
def pagina_backup(request):
    """Página principal de gerenciamento de backup"""
    if request.user.tipo_usuario not in ['admin', 'revenda'] and not request.user.is_superuser:
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect('dashboard')
    
    # Verifica configuração do Telegram
    token, chat_id = get_telegram_config(request.user)
    telegram_configurado = bool(token and chat_id)
    
    # Schedule do usuário
    schedule, created = BackupSchedule.objects.get_or_create(
        usuario=request.user,
        defaults={
            'frequencia': '24h',
            'manter_ultimos': 7,
            'ativo': False
        }
    )
    
    # Lista de backups
    backups_list = BackupHistory.objects.filter(
        usuario=request.user
    ).order_by('-data_criacao')
    
    # Paginação
    paginator = Paginator(backups_list, 20)
    page = request.GET.get('page', 1)
    backups = paginator.get_page(page)
    
    # Espaço em disco
    backup_dir = settings.BASE_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    total_size = sum(f.stat().st_size for f in backup_dir.glob('*.gz'))
    total_backups = len(list(backup_dir.glob('*.gz')))
    
    context = {
        'schedule': schedule,
        'backups': backups,
        'total_backups': total_backups,
        'total_size': total_size,
        'total_size_mb': total_size / (1024 * 1024) if total_size > 0 else 0,
        'frequencias': BackupSchedule.FREQUENCIA_CHOICES,
        'telegram_configurado': telegram_configurado,
        'chat_id_mascarado': chat_id[:8] + '...' if chat_id else None,
    }
    
    return render(request, 'clientes/backup.html', context)


@login_required
@require_POST
def criar_backup_agora(request):
    """
    Cria backup manual e envia para o Telegram
    """
    if request.user.tipo_usuario not in ['admin', 'revenda'] and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Permissão negada'})
    
    history = None
    
    try:
        db = settings.DATABASES['default']
        backup_dir = settings.BASE_DIR / 'backups'
        backup_dir.mkdir(exist_ok=True)
        
        # Nome do arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.sql'
        filepath = backup_dir / filename
        
        # Cria histórico
        history = BackupHistory.objects.create(
            usuario=request.user,
            arquivo=filename,
            status='running'
        )
        
        # Comando pg_dump
        cmd = [
            'pg_dump',
            '-h', db['HOST'],
            '-p', str(db['PORT']),
            '-U', db['USER'],
            '-d', db['NAME'],
            '-f', str(filepath),
            '--no-owner',
            '--no-acl',
            '--clean',
        ]
        
        result = executar_comando_pg(cmd, timeout=300)
        
        if result.returncode != 0:
            raise Exception(f"pg_dump falhou: {result.stderr[:500]}")
        
        # Compacta o backup
        compressed_file = filepath.with_suffix('.sql.gz')
        with open(filepath, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb', compresslevel=9) as f_out:
                f_out.writelines(f_in)
        
        # Remove arquivo SQL original
        filepath.unlink()
        
        # Informações do arquivo
        tamanho = compressed_file.stat().st_size
        tamanho_mb = tamanho / (1024 * 1024)
        
        # 🔴 ENVIA PARA O TELEGRAM
        data_hora = datetime.now().strftime('%d/%m/%Y às %H:%M')
        caption = (
            f"🗄️ <b>BACKUP DO SISTEMA</b>\n\n"
            f"📅 <b>Data:</b> {data_hora}\n"
            f"📦 <b>Arquivo:</b> <code>{compressed_file.name}</code>\n"
            f"📏 <b>Tamanho:</b> {tamanho_mb:.2f} MB\n"
            f"👤 <b>Usuário:</b> {request.user.username}\n"
            f"🖥️ <b>Servidor:</b> Gestor TLS\n"
            f"🏷️ <b>Banco:</b> {db['NAME']}\n\n"
            f"<i>Backup gerado automaticamente</i>"
        )
        
        telegram_id = enviar_para_telegram(str(compressed_file), caption, request.user)
        
        # Atualiza histórico
        history.arquivo = compressed_file.name
        history.tamanho = tamanho
        history.status = 'success'
        history.telegram_message_id = telegram_id
        history.save()
        
        # Atualiza agendamento
        schedule = BackupSchedule.objects.filter(usuario=request.user).first()
        if schedule:
            schedule.ultimo_backup = timezone.now()
            schedule.proximo_backup = schedule.calcular_proximo_backup()
            schedule.save()
        
        # Limpa backups antigos
        limpar_backups_antigos(request.user)
        
        logger.info(f"✅ Backup criado e enviado para Telegram: {tamanho_mb:.2f} MB")
        
        return JsonResponse({
            'success': True,
            'message': f'✅ Backup criado e enviado para Telegram! ({tamanho_mb:.2f} MB)',
            'filename': compressed_file.name,
            'size': tamanho,
            'size_formatted': f'{tamanho_mb:.2f} MB',
            'telegram_enviado': bool(telegram_id)
        })
        
    except subprocess.TimeoutExpired:
        if history:
            history.status = 'error'
            history.erro = 'Timeout (5 minutos)'
            history.save()
        return JsonResponse({
            'success': False,
            'message': 'Timeout ao criar backup (limite de 5 minutos)'
        })
        
    except FileNotFoundError:
        if history:
            history.status = 'error'
            history.erro = 'pg_dump não encontrado'
            history.save()
        return JsonResponse({
            'success': False,
            'message': 'Ferramenta pg_dump não encontrada. Verifique a instalação do PostgreSQL.'
        })
        
    except Exception as e:
        logger.error(f"❌ Erro no backup: {e}", exc_info=True)
        if history:
            history.status = 'error'
            history.erro = str(e)[:500]
            history.save()
        return JsonResponse({
            'success': False,
            'message': f'Erro: {str(e)[:200]}'
        })


@login_required
def baixar_backup(request, backup_id):
    """Download do arquivo de backup"""
    try:
        history = BackupHistory.objects.get(id=backup_id, usuario=request.user)
        backup_dir = settings.BASE_DIR / 'backups'
        filepath = backup_dir / history.arquivo
        
        if filepath.exists():
            response = FileResponse(
                open(filepath, 'rb'),
                content_type='application/gzip',
                as_attachment=True,
                filename=history.arquivo
            )
            response['Content-Length'] = filepath.stat().st_size
            return response
        else:
            messages.error(request, "Arquivo de backup não encontrado.")
            return redirect('pagina_backup')
            
    except BackupHistory.DoesNotExist:
        messages.error(request, "Backup não encontrado.")
        return redirect('pagina_backup')


# clientes/views_backup.py - Atualize a função restaurar_backup

@login_required
@require_POST
def restaurar_backup(request):
    """
    Restaura backup a partir de arquivo enviado
    Com verificações de segurança e timeout adequado
    """
    if request.user.tipo_usuario not in ['admin', 'revenda'] and not request.user.is_superuser:
        messages.error(request, "Permissão negada.")
        return redirect('pagina_backup')
    
    if request.method == 'POST':
        arquivo = request.FILES.get('backup_file')
        
        if not arquivo:
            messages.error(request, "Selecione um arquivo de backup.")
            return redirect('pagina_backup')
        
        if not arquivo.name.endswith(('.sql', '.gz')):
            messages.error(request, "Formato inválido. Use .sql ou .gz")
            return redirect('pagina_backup')
        
        # Verifica tamanho do arquivo (máximo 100MB)
        if arquivo.size > 100 * 1024 * 1024:
            messages.error(request, "Arquivo muito grande (máximo 100MB).")
            return redirect('pagina_backup')
        
        tmp_path = None
        
        try:
            db = settings.DATABASES['default']
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix='.sql', mode='wb') as tmp:
                if arquivo.name.endswith('.gz'):
                    # Descompacta gzip
                    import gzip
                    tmp.write(gzip.decompress(arquivo.read()))
                else:
                    # Escreve diretamente
                    for chunk in arquivo.chunks():
                        tmp.write(chunk)
                tmp_path = tmp.name
            
            # Verifica se o arquivo SQL parece válido
            with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                if not first_line.startswith(('--', 'CREATE', 'ALTER', 'INSERT', 'COPY', 'SET', 'SELECT')):
                    os.unlink(tmp_path)
                    messages.error(request, "Arquivo SQL parece inválido.")
                    return redirect('pagina_backup')
            
            # 🔴 COMANDO CORRETO PARA RESTAURAÇÃO
            cmd = [
                'psql',
                '-h', db['HOST'],
                '-p', str(db['PORT']),
                '-U', db['USER'],
                '-d', db['NAME'],
                '-f', tmp_path,
                '--quiet',           # Modo silencioso
                '--single-transaction',  # Se falhar, faz rollback
                '-v', 'ON_ERROR_STOP=1',  # Para no primeiro erro
            ]
            
            # Configura ambiente com senha
            env = os.environ.copy()
            env['PGPASSWORD'] = db['PASSWORD']
            
            # Adiciona PATH do PostgreSQL no Windows
            pg_path = get_pg_tools_path()
            if pg_path and platform.system() == 'Windows':
                env['PATH'] = pg_path + ';' + env.get('PATH', '')
                cmd[0] = os.path.join(pg_path, 'psql.exe')
            
            logger.info(f"🔄 Iniciando restauração do banco...")
            logger.info(f"📦 Arquivo: {arquivo.name} ({arquivo.size / (1024*1024):.2f} MB)")
            
            # Executa com timeout maior (10 minutos)
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True, 
                timeout=600  # 10 minutos
            )
            
            # Remove arquivo temporário
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            if result.returncode == 0:
                messages.success(request, "✅ Banco de dados restaurado com sucesso!")
                logger.info(f"✅ Backup restaurado por {request.user.username}")
                
                # Notifica no Telegram
                try:
                    enviar_mensagem_telegram(
                        f"🔄 <b>RESTAURAÇÃO DE BACKUP</b>\n\n"
                        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                        f"👤 {request.user.username}\n"
                        f"📦 {arquivo.name}\n"
                        f"📏 {arquivo.size / (1024*1024):.2f} MB\n\n"
                        f"✅ Restauração concluída com sucesso!",
                        request.user
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Não foi possível notificar Telegram: {e}")
                
                # Registra log de atividade
                try:
                    LogAtividade.registrar(
                        request=request,
                        usuario=request.user,
                        tipo_acao='restauracao',
                        descricao=f"Banco restaurado do arquivo: {arquivo.name}",
                        status='sucesso'
                    )
                except:
                    pass
                    
            else:
                erro = result.stderr[:500] if result.stderr else 'Erro desconhecido'
                messages.error(request, f"❌ Erro na restauração. O banco NÃO foi alterado.")
                logger.error(f"❌ Erro na restauração: {erro}")
                
                # Notifica erro no Telegram
                try:
                    enviar_mensagem_telegram(
                        f"❌ <b>FALHA NA RESTAURAÇÃO</b>\n\n"
                        f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                        f"👤 {request.user.username}\n"
                        f"📦 {arquivo.name}\n"
                        f"📝 {erro[:200]}",
                        request.user
                    )
                except:
                    pass
                
        except subprocess.TimeoutExpired:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            messages.error(request, "⏰ Timeout na restauração (limite de 10 minutos). O banco NÃO foi alterado.")
            logger.error("❌ Timeout na restauração")
            
        except MemoryError:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            messages.error(request, "💾 Arquivo muito grande para processar. Tente um backup menor.")
            
        except Exception as e:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            messages.error(request, f"❌ Erro ao restaurar: {str(e)[:200]}")
            logger.error(f"❌ Erro na restauração: {e}", exc_info=True)
    
    return redirect('pagina_backup')

@login_required
@require_POST
def excluir_backup(request, backup_id):
    """Exclui um backup (local e registro)"""
    try:
        history = BackupHistory.objects.get(id=backup_id, usuario=request.user)
        backup_dir = settings.BASE_DIR / 'backups'
        filepath = backup_dir / history.arquivo
        
        # Remove arquivo local
        if filepath.exists():
            filepath.unlink()
        
        # Remove registro
        history.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Backup excluído com sucesso!'
        })
        
    except BackupHistory.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Backup não encontrado.'
        })


@login_required
@require_POST
def salvar_agendamento(request):
    """Salva configuração de agendamento de backup"""
    if request.method == 'POST':
        frequencia = request.POST.get('frequencia', '24h')
        manter = int(request.POST.get('manter_ultimos', 7))
        ativo = request.POST.get('ativo') == 'on'
        
        # Mapa de frequências
        frequencia_map = {
            '1h': timedelta(hours=1),
            '3h': timedelta(hours=3),
            '6h': timedelta(hours=6),
            '12h': timedelta(hours=12),
            '24h': timedelta(hours=24),
            '48h': timedelta(hours=48),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
        }
        
        proximo = None
        if ativo:
            delta = frequencia_map.get(frequencia, timedelta(hours=24))
            proximo = timezone.now() + delta
        
        schedule, created = BackupSchedule.objects.update_or_create(
            usuario=request.user,
            defaults={
                'frequencia': frequencia,
                'manter_ultimos': manter,
                'ativo': ativo,
                'proximo_backup': proximo
            }
        )
        
        if ativo:
            messages.success(request, f"✅ Backup agendado a cada {schedule.get_frequencia_display()}!")
        else:
            messages.info(request, "Agendamento pausado.")
    
    return redirect('pagina_backup')


@login_required
@require_POST
def testar_telegram(request):
    """Testa a conexão com o Telegram"""
    token, chat_id = get_telegram_config(request.user)
    
    if not token or not chat_id:
        return JsonResponse({
            'success': False,
            'message': 'Telegram não configurado. Configure token_telegram e chave_telegram nas configurações.'
        })
    
    try:
        msg_id = enviar_mensagem_telegram(
            f"✅ <b>Teste de Conexão</b>\n\n"
            f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"👤 {request.user.username}\n"
            f"🖥️ Gestor TLS\n\n"
            f"Conexão com Telegram funcionando perfeitamente!",
            request.user
        )
        
        if msg_id:
            return JsonResponse({
                'success': True,
                'message': '✅ Mensagem enviada com sucesso! Verifique seu Telegram.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Erro ao enviar mensagem. Verifique o token e chat_id.'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro: {str(e)[:200]}'
        })


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def limpar_backups_antigos(user):
    """Remove backups antigos mantendo apenas os N mais recentes"""
    try:
        schedule = BackupSchedule.objects.get(usuario=user)
        manter = schedule.manter_ultimos
    except BackupSchedule.DoesNotExist:
        manter = 7
    
    backup_dir = settings.BASE_DIR / 'backups'
    
    # Lista backups por data
    backups = sorted(
        backup_dir.glob('backup_*.sql.gz'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    removidos = 0
    for old in backups[manter:]:
        try:
            # Remove arquivo
            old.unlink()
            # Remove registro do banco
            BackupHistory.objects.filter(arquivo=old.name).delete()
            removidos += 1
            logger.info(f"🗑️ Backup antigo removido: {old.name}")
        except Exception as e:
            logger.error(f"❌ Erro ao remover {old.name}: {e}")
    
    if removidos > 0:
        logger.info(f"🧹 {removidos} backups antigos limpos")


# ============================================
# FUNÇÃO PARA CRON (AGENDAMENTO AUTOMÁTICO)
# ============================================
def executar_backup_agendado():
    """
    Executa backup automático para todos os agendamentos ativos
    Chamado via cron no Easypanel
    """
    agora = timezone.now()
    schedules = BackupSchedule.objects.filter(
        ativo=True,
        proximo_backup__lte=agora
    )
    
    if not schedules.exists():
        logger.info("ℹ️ Nenhum backup agendado para agora")
        return
    
    for schedule in schedules:
        try:
            user = schedule.usuario
            db = settings.DATABASES['default']
            backup_dir = settings.BASE_DIR / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'backup_auto_{timestamp}.sql'
            filepath = backup_dir / filename
            
            history = BackupHistory.objects.create(
                usuario=user,
                arquivo=filename,
                status='running'
            )
            
            # Executa pg_dump
            cmd = [
                'pg_dump', '-h', db['HOST'], '-p', str(db['PORT']),
                '-U', db['USER'], '-d', db['NAME'],
                '-f', str(filepath), '--no-owner', '--no-acl',
            ]
            
            result = executar_comando_pg(cmd, timeout=300)
            
            if result.returncode == 0:
                # Compacta
                compressed_file = filepath.with_suffix('.sql.gz')
                with open(filepath, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb', compresslevel=9) as f_out:
                        f_out.writelines(f_in)
                filepath.unlink()
                
                tamanho = compressed_file.stat().st_size
                tamanho_mb = tamanho / (1024 * 1024)
                
                # Envia para Telegram
                caption = (
                    f"🤖 <b>BACKUP AUTOMÁTICO</b>\n\n"
                    f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    f"📦 {compressed_file.name}\n"
                    f"📏 {tamanho_mb:.2f} MB\n"
                    f"👤 {user.username}\n"
                    f"⏰ Frequência: {schedule.get_frequencia_display()}"
                )
                
                telegram_id = enviar_para_telegram(str(compressed_file), caption, user)
                
                history.arquivo = compressed_file.name
                history.tamanho = tamanho
                history.status = 'success'
                history.telegram_message_id = telegram_id
                history.save()
                
                # Limpa antigos
                limpar_backups_antigos(user)
                
                logger.info(f"✅ Backup automático para {user.username}: {tamanho_mb:.2f} MB")
            else:
                history.status = 'error'
                history.erro = result.stderr[:500]
                history.save()
                
                # Notifica erro no Telegram
                enviar_mensagem_telegram(
                    f"❌ <b>ERRO NO BACKUP AUTOMÁTICO</b>\n\n"
                    f"👤 {user.username}\n"
                    f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
                    f"📝 {result.stderr[:200]}",
                    user
                )
            
            # Atualiza próximo backup
            schedule.ultimo_backup = agora
            schedule.proximo_backup = schedule.calcular_proximo_backup()
            schedule.save()
            
        except Exception as e:
            logger.error(f"❌ Erro backup automático para {schedule.usuario.username}: {e}", exc_info=True)
