import logging
from urllib.parse import urlparse, parse_qs

from django.db import transaction
from django.utils import timezone

from .integrations.playlists.factory import get_playlist_provider
from .models import Configuracao, PlaylistRemota, TestePlaylist

logger = logging.getLogger(__name__)


def _credenciais(playlist):
    dados = playlist.credenciais()
    return str(dados.get('usuario') or '').strip(), str(dados.get('senha') or '').strip()


def _montar_url(playlist, usuario, senha):
    url = str(playlist.url_playlist or '').strip()
    if url:
        return url
    dns = str(playlist.dns or playlist.integracao.dns or '').strip().rstrip('/')
    if not dns:
        return ''
    if not dns.startswith(('http://', 'https://')):
        dns = 'http://' + dns
    return f"{dns}/get.php?username={usuario}&password={senha}&type=m3u_plus&output=ts"


def payload_playlist(playlist):
    usuario, senha = _credenciais(playlist)
    modo = str(playlist.modo_envio or '').strip().lower()
    return {
        'nome_playlist': playlist.nome,
        'usuario': usuario,
        'senha': senha,
        'dns': playlist.dns or playlist.integracao.dns,
        'url_playlist': _montar_url(playlist, usuario, senha),
        'codigo': playlist.codigo or playlist.integracao.codigo,
        'proteger': playlist.protegida,
        'pin': playlist.pin_protecao,
        'modo_envio': 'codigo' if modo == 'parceria' else 'url',
    }


def ativar_playlist_objeto(playlist):
    if playlist.remote_id and playlist.status == 'ativo':
        return {'success': True, 'confirmed': True, 'message': 'A lista já está ativa.', 'remote_id': playlist.remote_id}
    provider = get_playlist_provider(playlist.integracao)
    resultado = provider.adicionar_playlist(**payload_playlist(playlist))
    if resultado.get('requires_captcha'):
        return resultado
    sucesso = bool(resultado.get('success'))
    confirmado = bool(resultado.get('confirmed', sucesso))
    remote_id = str(resultado.get('remote_id') or '').strip()
    playlist.remote_id = remote_id or playlist.remote_id
    playlist.status = 'ativo' if sucesso and confirmado else 'confirmacao_pendente' if sucesso else 'erro'
    playlist.ultima_mensagem = resultado.get('message', 'Operação concluída.')
    playlist.ultima_sincronizacao = timezone.now()
    dados_atuais = dict(playlist.dados_remotos or {})
    resposta_provider = resultado.get('data', {}) if isinstance(resultado.get('data'), dict) else {}
    dados_atuais['ultima_resposta_provider'] = resposta_provider
    dados_atuais['publicacao_confirmada'] = bool(sucesso and confirmado)
    dados_atuais['publicacao_falhou'] = bool(not sucesso)
    dados_atuais['ultima_publicacao_em'] = timezone.now().isoformat()
    playlist.dados_remotos = dados_atuais
    playlist.save()
    if sucesso and confirmado:
        playlist.integracao.status = 'ativo'
        playlist.integracao.ultima_mensagem = 'Lista ativa no aplicativo.'
        playlist.integracao.save(update_fields=['status', 'ultima_mensagem', 'atualizado_em'])
    return resultado


def desativar_playlist_objeto(playlist, pin=''):
    if not playlist.remote_id:
        if playlist.status == 'excluida':
            return {'success': True, 'confirmed': True, 'already_inactive': True, 'message': 'A lista já está desativada.'}
        return {'success': False, 'confirmed': False, 'message': 'A lista ainda não possui ID remoto.'}

    codigo_padrao = str(
        Configuracao.objects.filter(usuario=playlist.integracao.dono)
        .values_list('codigo_protecao_playlist', flat=True).first() or ''
    ).strip()
    pin = str(pin or '').strip() or str(playlist.pin_protecao or '').strip() or codigo_padrao
    remote_id = str(playlist.remote_id or '').strip()
    provider = get_playlist_provider(playlist.integracao)
    resultado = provider.excluir_playlist(remote_id=remote_id, pin=pin, protegida=playlist.protegida)
    if resultado.get('requires_captcha'):
        return resultado
    if not bool(resultado.get('success') and resultado.get('confirmed')):
        return resultado

    dados = dict(playlist.dados_remotos or {})
    dados['ultimo_remote_id_desativado'] = remote_id
    dados['desativada_em'] = timezone.now().isoformat()
    playlist.remote_id = ''
    playlist.status = 'excluida'
    playlist.encontrada_na_ultima_sync = False
    playlist.ultima_sincronizacao = timezone.now()
    playlist.ultima_mensagem = 'Lista desativada no aplicativo. Cadastro preservado no gestor.'
    playlist.dados_remotos = dados
    playlist.save()

    # Um dispositivo pode possuir várias listas. Desativar uma delas não deve
    # marcar o dispositivo inteiro como inativo quando ainda existem outras
    # playlists publicadas nele.
    outras_ativas = playlist.integracao.playlists.exclude(pk=playlist.pk).filter(
        status='ativo'
    ).exclude(remote_id='').count()
    playlist.integracao.status = 'ativo' if outras_ativas else 'configurado'
    playlist.integracao.ultima_mensagem = (
        f'Lista desativada. {outras_ativas} outra(s) lista(s) continuam ativas neste dispositivo.'
        if outras_ativas
        else 'Lista desativada. O cadastro pode ser reativado depois.'
    )
    playlist.integracao.save(update_fields=['status', 'ultima_mensagem', 'atualizado_em'])
    return {'success': True, 'confirmed': True, 'message': playlist.ultima_mensagem, 'remote_id': remote_id}


def _falha_publicacao_sem_remoto(playlist):
    """Identifica testes que nunca chegaram a existir no aplicativo.

    Esses registros não devem ficar eternamente como "teste vencido precisa de
    atenção", porque não há uma lista remota para excluir. Também reconhecemos
    mensagens antigas como "Device not found" para limpar registros criados por
    versões anteriores do gestor.
    """
    if not playlist or playlist.remote_id:
        return False
    dados = playlist.dados_remotos if isinstance(playlist.dados_remotos, dict) else {}
    if dados.get('publicacao_falhou') is True:
        return True
    mensagem = str(playlist.ultima_mensagem or '').strip().casefold()
    marcadores = (
        'device not found',
        'dispositivo não encontrado',
        'dispositivo nao encontrado',
        'falha na autenticação',
        'falha na autenticacao',
        'mac e device key são obrigatórios',
        'mac e device key sao obrigatorios',
    )
    return playlist.status in {'erro', 'rascunho'} and any(m in mensagem for m in marcadores)



def normalizar_testes_orfaos(dono=None):
    """Encerra testes que não possuem mais uma playlist utilizável.

    O TestePlaylist é histórico e deve continuar aparecendo na lista, mesmo
    depois que a PlaylistRemota for removida. O que não pode acontecer é o
    registro continuar como ativo/erro e oferecer uma ação remota impossível.
    """
    agora = timezone.now()
    estados_abertos = ['agendado', 'ativo', 'erro', 'aguardando_auth']

    sem_playlist = TestePlaylist.objects.filter(
        status__in=estados_abertos,
        playlist__isnull=True,
    )
    lista_ja_excluida = TestePlaylist.objects.filter(
        status__in=estados_abertos,
        playlist__isnull=False,
        playlist__status='excluida',
        playlist__remote_id='',
    )
    if dono is not None:
        sem_playlist = sem_playlist.filter(dono=dono)
        lista_ja_excluida = lista_ja_excluida.filter(dono=dono)

    qtd_sem = sem_playlist.update(
        status='desativado',
        ultima_mensagem='Teste encerrado. A playlist vinculada já foi removida do gestor.',
        ultima_tentativa=agora,
    )
    qtd_excluida = lista_ja_excluida.update(
        status='desativado',
        ultima_mensagem='Teste encerrado. A lista já está desativada no aplicativo.',
        ultima_tentativa=agora,
    )
    return qtd_sem + qtd_excluida

def processar_teste(teste):
    if teste.status in {'desativado', 'convertido'}:
        return {'success': True, 'message': 'Teste já finalizado.'}
    playlist = teste.playlist
    if not playlist:
        # A playlist já foi removida do gestor. Não existe mais nenhuma ação
        # remota a executar, então o teste deve ser encerrado silenciosamente
        # em vez de permanecer como erro exigindo "Tentar novamente".
        teste.status = 'desativado'
        teste.ultima_mensagem = 'Teste encerrado. A playlist vinculada já foi removida do gestor.'
        teste.ultima_tentativa = timezone.now()
        teste.tentativas += 1
        teste.save(update_fields=['status','ultima_mensagem','ultima_tentativa','tentativas','atualizado_em'])
        return {
            'success': True,
            'confirmed': True,
            'already_removed': True,
            'message': teste.ultima_mensagem,
        }
    if _falha_publicacao_sem_remoto(playlist):
        dados = dict(playlist.dados_remotos or {})
        dados['desativada_sem_publicacao'] = True
        dados['desativada_em'] = timezone.now().isoformat()
        playlist.status = 'excluida'
        playlist.encontrada_na_ultima_sync = False
        playlist.ultima_mensagem = (
            'Teste encerrado. A lista nunca chegou a ser publicada no aplicativo, '
            'então não havia nada remoto para excluir.'
        )
        playlist.dados_remotos = dados
        playlist.ultima_sincronizacao = timezone.now()
        playlist.save()
        teste.status = 'desativado'
        teste.ultima_mensagem = playlist.ultima_mensagem + ' Cadastro preservado.'
        teste.ultima_tentativa = timezone.now()
        teste.tentativas += 1
        teste.save(update_fields=['status','ultima_mensagem','ultima_tentativa','tentativas','atualizado_em'])
        return {'success': True, 'confirmed': True, 'nothing_remote': True, 'message': teste.ultima_mensagem}

    resultado = desativar_playlist_objeto(playlist)
    teste.ultima_tentativa = timezone.now()
    teste.tentativas += 1
    if resultado.get('success') and resultado.get('confirmed'):
        teste.status = 'desativado'
        teste.ultima_mensagem = 'Teste vencido e lista removida do aplicativo. Cadastro preservado.'
    elif resultado.get('requires_captcha'):
        teste.status = 'aguardando_auth'
        teste.ultima_mensagem = resultado.get('message') or 'O IBO precisa ser autenticado para concluir a desativação.'
    else:
        teste.status = 'erro'
        teste.ultima_mensagem = resultado.get('message') or 'Não foi possível excluir a lista do aplicativo.'
    teste.save(update_fields=['status','ultima_mensagem','ultima_tentativa','tentativas','atualizado_em'])
    return resultado


def processar_testes_vencidos(dono=None, limite=50):
    # Mantém o histórico coerente mesmo quando a playlist foi apagada antes do vencimento.
    normalizar_testes_orfaos(dono=dono)
    qs = TestePlaylist.objects.select_related('playlist__integracao', 'dono').filter(
        status__in=['agendado','ativo','erro','aguardando_auth'], vence_em__lte=timezone.now()
    )
    if dono is not None:
        qs = qs.filter(dono=dono)
    resultados = []
    for teste in qs.order_by('vence_em')[:limite]:
        # IBO aguardando CAPTCHA exige ação do operador. Erros reais também não
        # são martelados em loop, exceto falhas de publicação sem ID remoto: nesse
        # caso não existe nada para excluir e podemos encerrar o teste localmente.
        if teste.status == 'aguardando_auth':
            continue
        if teste.status == 'erro' and not _falha_publicacao_sem_remoto(teste.playlist):
            continue
        try:
            resultados.append((teste.id, processar_teste(teste)))
        except Exception as exc:
            logger.exception('Falha ao processar teste playlist %s', teste.id)
            teste.status = 'erro'
            teste.ultima_mensagem = str(exc)
            teste.ultima_tentativa = timezone.now()
            teste.tentativas += 1
            teste.save(update_fields=['status','ultima_mensagem','ultima_tentativa','tentativas','atualizado_em'])
    return resultados
