# Central Administrativa de Solicitações e Empenhos

Base usada: `consulta-sementes-main-limpo-20261008`.

## Regras preservadas

- O fluxo do usuário normal continua com as mesmas permissões e travas por status.
- A Central Administrativa é separada e aceita somente superusuário, `is_staff` ou administrador funcional com as permissões de configurações + gerenciamento de usuários.
- Não foi copiado o projeto misturado por cima da versão limpa.
- Não há migration nova nesta alteração.

## Recursos administrativos adicionados

- Tela exclusiva em `/admin-operacional/empenhos/`.
- Pesquisa por carga/card, cliente, destino, produto e lote.
- Edição de título, tipo, cliente, destino, placa, motorista, quantidades, unidade, prioridade, coluna Kanban, observação e status.
- Edição dos dados do Empenho.
- Adição de lote ao empenho em qualquer status.
- Ao adicionar lote a um card concluído, ele volta para `MOVIMENTACAO_PARCIAL` e a meta é ampliada quando necessário.
- Remoção de item empenhado sem bloqueio por status.
- Alteração da quantidade de um item empenhado.
- Troca do lote/estoque de um item empenhado com ajuste correto da reserva física.
- Movimentação de item empenhado de um card para outro.
- Estorno da última movimentação do card.
- Estorno individual de transferência/expedição processada, restaurando saldo e recriando o ItemEmpenho.
- Correção do snapshot `endereco_destino` no fluxo normal de empenho.
- Botão `Admin` aparece na tela normal apenas para administradores.

## Proteção mantida no estorno

O status nunca bloqueia o administrador. A única trava mantida é de integridade física: um estorno não é aplicado se ele deixaria o estoque de destino com saldo menor que uma reserva posterior já existente. Nesse caso, primeiro é necessário mover ou remover a reserva posterior.

## Arquivos principais alterados

- `sapp/admin_operacional.py` (novo)
- `sapp/templates/sapp/admin_operacional_empenhos.html` (novo)
- `sapp/templates/sapp/admin_operacional_empenho_detalhe.html` (novo)
- `sapp/urls.py`
- `sapp/views.py`
- `sapp/templates/sapp/pagina_solicitacoes.html`

## Validação feita neste pacote

- Todos os 122 arquivos Python compilaram sem erro de sintaxe.
- As estruturas `{% if %}`, `{% for %}` e `{% block %}` dos dois templates novos foram verificadas e estão balanceadas.
- Não foi possível executar `manage.py check` neste ambiente porque o runtime disponível não possui Django instalado e não há acesso à internet para instalar a dependência. O projeto continua declarando Django 5.2 em `requirements.txt`.
## Correção v2 - modal normal de Empenho

- O modal de empenho da página normal de Solicitações agora reconhece administrador operacional.
- Admin não recebe a trava visual em `MOVIMENTACAO_PARCIAL`, `CONCLUIDO` ou `CANCELADO`.
- A API normal de adicionar/remover empenho também ignora a trava de status somente para admin.
- Usuário comum permanece com as travas anteriores.
- Admin pode acrescentar além da meta anterior; quando necessário a quantidade solicitada é ampliada.
- Ao acrescentar lote após movimentação/conclusão, o card retorna para `MOVIMENTACAO_PARCIAL`.
- Ao retirar o acréscimo e não restar pendência, um card já totalmente movimentado pode voltar para `CONCLUIDO`.
- O limite físico de saldo do lote continua obrigatório, inclusive para admin.

