# Revisão: modais, setas, arquivos estáticos e envio em massa

## Causa principal encontrada no log
O navegador estava recebendo HTTP 404 para os arquivos que continham a maior parte do acabamento visual novo:
- `/static/css/ui-polish.css`
- `/static/css/theme-system-final.css`
- `/static/css/listar_clientes.css`
- `/static/logo.png`
- `/static/js/service-worker.js`

O projeto usa `whitenoise.runserver_nostatic`, enquanto `DJANGO_DEBUG` pode estar `False` no ambiente local. Nessa combinação o `runserver` não entregava os arquivos-fonte sem `collectstatic`.

### Correção
- `WHITENOISE_USE_FINDERS` e `WHITENOISE_AUTOREFRESH` ficam ativos durante `runserver`.
- Foi adicionada uma rota de desenvolvimento que usa os static finders do Django com `insecure=True` somente quando o comando executado é `runserver`.
- Em produção com Gunicorn o comportamento permanece o normal de WhiteNoise/collectstatic.
- Mantido um pequeno fallback visual crítico dentro do `base.html` para seta de detalhes e tamanho dos modais.

## Seta de detalhes
- A seta de clientes não depende mais do desenho do Font Awesome.
- O botão possui uma seta CSS própria, herda a cor do tema e anima ao expandir/recolher.
- `aria-expanded` agora acompanha o estado aberto/fechado.
- A seta do Gerenciador de Playlists recebeu o mesmo padrão.

## Modais
Padrão adotado:
- modal comum: até 520 px;
- modal largo/complexo: até 680 px;
- AppUI: até 420 px;
- celular: margem de 12 px e altura máxima de 84dvh;
- rolagem acontece no corpo, não transformando o painel em tela inteira.

Foram padronizados cabeçalho, corpo, rodapé, botão fechar, bordas, raio, sombra e cores de tema para Bootstrap e modais legados/customizados.

### Modal de Tags
O modal de Tags foi refeito e isolado das classes `.modal` e `.modal-content` do Bootstrap. Agora usa classes próprias (`tls-tags-*`), painel de 520 px, corpo rolável, rodapé fixo e layout móvel compacto. Isso elimina a colisão que fazia o modal deformar.

## Envio em massa - Enviar agora
O endpoint HTTP estava respondendo 200, mas o processador era aberto como subprocesso com `stdout` e `stderr` em `DEVNULL`. Uma falha depois do clique ficava praticamente invisível.

### Correção
- O envio imediato agora inicia o mesmo management command em uma thread do processo Django.
- A fila continua persistida no banco e pode ser retomada pelo agendador.
- Erros permanecem no logger do Django e o status da campanha recebe a causa amigável.
- Conexões de banco são abertas/fechadas corretamente para a thread.
- A configuração global da Evolution passa a vencer credenciais legadas da instância quando a instância usa a URL padrão/local.
- URL/chave específicas continuam sendo usadas quando a instância realmente aponta para um servidor próprio.
- `data_envio_inicio` e `data_envio_fim` passam a ser gravadas corretamente.

## URLs
O namespace `integra` estava incluído duas vezes (`/integra/` e `/whatsapp/`). O alias `/whatsapp/` foi preservado, porém com namespace próprio `integra_legacy`, removendo a colisão sem quebrar o caminho antigo.

## Ajuste adicional no Dashboard
Foi corrigido o filtro de `LoteEstoque.data_compra` para usar `__date__gte` quando o valor de comparação é uma data. Isso elimina o warning de datetime ingênuo observado no log. Um `traceback.print_exc()` residual também foi substituído por logger.

## Observação para produção
O Dockerfile já executa `collectstatic` durante o build. Caso a implantação não use o Dockerfile, execute `python manage.py collectstatic --noinput` antes de servir com Gunicorn/WhiteNoise.
