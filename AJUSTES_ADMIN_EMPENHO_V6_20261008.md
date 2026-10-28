# Ajustes V6 - progresso dos cards por movimentação real

## Correção principal

A barra/progresso dos cards da tela de Solicitações e do Kanban passa a representar apenas a quantidade efetivamente movimentada (transferida/expedida), e não a soma de movimentado + empenhado pendente.

Exemplo:
- Quantidade solicitada: 8 BAG
- Movimentado: 1 BAG
- Empenhado pendente: 7 BAG
- Exibição correta: 1/8 BAG, 12,5% (arredondado visualmente para 13%)

O empenho pendente continua mostrado separadamente no card. Quando os 8 BAG forem de fato movimentados, a barra chega a 8/8 e 100%.

Também foi incluído `percentual_movimentado` na API de atualização de cards para manter a mesma regra após polling/atualização automática.

Não há migration nova nesta versão.
