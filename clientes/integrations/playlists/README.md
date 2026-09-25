# Gerenciador de Playlists V2

## O que este pacote implementa

- Um dispositivo/integração com várias playlists.
- Cadastro apenas do dispositivo.
- Puxar todas as playlists já existentes no painel.
- Importar sem duplicar, usando `remote_id`.
- Criar playlist localmente.
- Criar e subir playlist.
- Atualizar uma playlist específica a partir do painel.
- Editar dados somente no sistema.
- Substituir remotamente com confirmação.
- Excluir somente local, somente remoto ou ambos.
- Preservar nome local diferente do nome remoto.
- Marcar listas ausentes sem apagá-las.
- Histórico por integração e por playlist.
- Migração manual das playlists antigas.

## Arquivos

1. `models_playlist_v2.py`
   Substitua a seção atual dos models de integração.

2. `views_playlist_v2.py`
   Substitua as views atuais desse módulo e ajuste os imports em `views.py`.

3. `base_provider.py`
   Substitua o conteúdo de `clientes/integrations/playlists/base.py`.

4. `app_acesso_dual_additions.py`
   Copie os métodos para dentro da classe `AppAcessoDualProvider`.

5. `urls_playlist_v2.py`
   Substitua o bloco antigo de URLs.

6. `integracoes_playlist.html`
   Substitua o template atual.

## Ordem de implantação

```bash
python manage.py makemigrations clientes
python manage.py migrate
python manage.py check
```

Depois abra a página e, para integrações antigas que já possuíam uma playlist,
use temporariamente o endpoint de migração pelo botão ou via POST:

```text
/integracoes-playlist/ID/migrar-legada/
```

Você também pode migrar automaticamente no shell:

```bash
python manage.py shell
```

```python
from clientes.models import IntegracaoPlaylistCliente, PlaylistRemota

for i in IntegracaoPlaylistCliente.objects.all():
    if i.playlists.exists():
        continue
    if not (i.playlist_remote_id or i.nome_playlist or i.usuario_iptv):
        continue
    PlaylistRemota.objects.create(
        integracao=i,
        cliente=i.cliente,
        nome=i.nome_playlist or i.nome_exibicao,
        nome_remoto=i.nome_playlist or "",
        remote_id=i.playlist_remote_id or "",
        usuario_iptv=i.usuario_iptv,
        senha_iptv=i.senha_iptv,
        dns=i.dns,
        codigo=i.codigo,
        url_playlist=i.url_template,
        modo_envio=(i.dados_remotos or {}).get("modo_envio", "url"),
        protegida=i.proteger,
        pin_protecao=i.pin_protecao,
        pin_conhecido=bool(i.pin_protecao),
        status="ativo" if i.playlist_remote_id else "rascunho",
        dados_remotos=i.dados_remotos or {},
    )
```

## Observação crítica sobre edição remota

O código fornecido da API possui:

- autenticação;
- listagem;
- criação;
- exclusão.

Ele não mostra um endpoint real de edição.

Por isso este pacote não inventa uma URL. A edição remota é implementada por
substituição explícita:

1. exclui a antiga;
2. cria a nova;
3. salva o novo ID.

A interface mostra um aviso e exige confirmação. Como a operação não é atômica,
uma falha na criação depois da exclusão exige recriar a lista.

## Antes de publicar

Faça backup do banco e teste com um MAC de laboratório.
