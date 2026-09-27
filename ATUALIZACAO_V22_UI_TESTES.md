# V22 - Limpeza de testes e acabamento visual

## Correções funcionais

- Testes cuja playlist já foi removida do gestor deixam de aparecer como erro pendente.
- Ao abrir o Gerenciador, registros órfãos em `erro`/`aguardando_auth` são encerrados como `desativado` quando não existe mais playlist vinculada.
- Se a playlist ainda existe, mas já está com status `excluida` e sem `remote_id`, o teste também é finalizado automaticamente.
- `processar_teste()` passa a considerar playlist já removida como encerramento confirmado, e não como erro.

## Gerenciador de playlists

- A área da tabela ocupa o restante da altura visível da página, inclusive quando existem poucas linhas.
- O botão **Mais** não usa mais um dropdown preso dentro da célula da tabela.
- **Mais ações** agora abre um modal global acima da tabela, evitando corte por scroll, última linha ou overflow.
- Mantido o formato de uma playlist por linha.

## UI global

- Nova camada `ui-v22.css` aplicada por último no `base.html`.
- Cards, painéis, tabelas, inputs, botões, alertas e modais receberam acabamento mais arredondado e espaçamento consistente.
- Todos os ajustes usam as variáveis do tema atual em vez de cores fixas.
- Melhorias em contraste de texto, placeholder, select e autofill.
- Dashboard recebe acabamento adicional em KPIs e cards.

## Login

- Login também carrega `ui-v22.css`.
- Campos agora respeitam cor de texto, fundo, borda, placeholder e autofill em todos os temas.
- Avisos, divisores, cabeçalho e formulário foram harmonizados com o tema selecionado.

## Banco de dados

- Nenhuma migration nova nesta versão.
