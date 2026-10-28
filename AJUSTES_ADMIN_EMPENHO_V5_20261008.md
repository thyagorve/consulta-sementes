# Ajustes Admin / Empenho V5 - 08/10/2026

## Correção PostgreSQL: FOR UPDATE em LEFT OUTER JOIN

Corrigido erro ao remover item de empenho:

`FOR UPDATE não pode ser aplicado ao lado com valores nulos de uma junção externa`

### Causa
Algumas consultas usavam `select_for_update()` junto com `select_related()` de FKs anuláveis, especialmente `HistoricoItemEmpenho.estoque_destino`. O Django gerava `LEFT OUTER JOIN` e o PostgreSQL tentava aplicar o lock também ao lado anulável.

### Correção
As consultas administrativas/transacionais passam a usar `select_for_update(of=('self',))` quando há joins opcionais. Assim somente a linha principal é bloqueada. Estoques e demais registros que precisam de lock continuam sendo travados separadamente dentro da mesma `transaction.atomic()`.

### Pontos revisados
- Remoção de item do empenho com movimentação relacionada.
- Desfazer uma movimentação administrativa.
- Desfazer a última movimentação.
- Restaurar ponto de restauração.
- Editar/remover/mover ItemEmpenho quando há relação opcional `item_carga`.
- Leitura de Empenho com `solicitacao` anulável em fluxo transacional.

Não há migration nova nesta versão.
