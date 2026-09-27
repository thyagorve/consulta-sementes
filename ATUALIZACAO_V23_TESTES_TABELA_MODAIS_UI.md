# Atualização V23 — Testes, tabela, modais e UI

## Testes de playlist
- Todos os testes continuam na mesma lista, independentemente de estarem ativos, agendados, desativados, convertidos ou com erro.
- Testes desativados ganharam tratamento visual diferente dos ativos.
- Quando a playlist vinculada foi excluída, o teste é preservado como histórico e passa para `desativado`.
- Testes sem playlist não exibem mais ações impossíveis como `Tentar novamente`, `Ativar teste`, `Migrar para cliente` ou `Ver no gerenciador`.
- O aviso de atenção do Gerenciador não mantém teste órfão pedindo nova tentativa.
- O contador de tempo aparece somente para estados em andamento/atenção, não para testes já desativados.

## Gerenciador de playlists
- A tabela passa a ocupar toda a altura útil da tela.
- A rolagem vertical e horizontal acontece dentro da tabela.
- O cabeçalho da tabela fica fixo durante a rolagem.
- O modal de `Mais ações` é movido para a raiz do documento para não ser cortado/escondido pela tabela ou por contêineres da página.
- Os demais modais da página usam o mesmo mecanismo de portal para a viewport.

## Login / temas
- Texto e placeholder dos campos agora respeitam as cores do tema.
- Hover de links usa a cor do tema em vez de azul fixo.
- Tipografia de inputs e botões foi uniformizada.

## Arquivos principais alterados
- `clientes/playlist_test_service.py`
- `clientes/views.py`
- `clientes/templates/clientes/testes_playlist.html`
- `clientes/templates/clientes/integracoes_playlist.html`
- `clientes/templates/registration/login.html`

## Validação feita neste pacote
- `clientes/views.py` e `clientes/playlist_test_service.py` compilados com `py_compile`.
- Estrutura dos blocos Django dos templates alterados verificada.
- `python manage.py check` não pôde ser executado no ambiente de edição porque o pacote Django não está instalado nele.
