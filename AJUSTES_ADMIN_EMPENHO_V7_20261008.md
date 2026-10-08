# Ajuste V7 - indicador regressivo pelo empenho pendente

A V7 restaura o comportamento original do indicador do card, sem reintroduzir o bug que somava movimentado + empenhado.

## Regra

- O numerador do card é a quantidade **ainda empenhada e pendente de movimentação**.
- O denominador é a quantidade solicitada.
- 8 solicitados / 8 empenhados pendentes = 8/8 (100%).
- Depois de transferir/expedir 1, restam 7 empenhados = 7/8 (88%).
- Depois de movimentar 4, restam 4 empenhados = 4/8 (50%).
- Ao movimentar tudo, o empenho pendente chega a 0 = 0/8 (0%).
- A linha separada continua mostrando `Movimentado` e `Empenhado pendente`.
- Se a solicitação ainda não foi totalmente empenhada, o indicador mostra apenas o que de fato está reservado, como no comportamento original.
- Ajustado na página de Solicitações e no Kanban.
- Nenhuma migration nova.
