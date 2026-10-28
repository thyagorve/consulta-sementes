# V15 — Data de movimentação + performance da Gestão de Estoque

Base: V14.

## Data mov.

- A coluna `Data mov.` agora mostra somente `dd/mm/AAAA`, sem horário.
- Ela fica oculta/desmarcada por padrão no gerenciador de colunas.
- Na primeira abertura da V15, navegadores que vieram da V14 também recebem esse novo padrão uma única vez. Depois disso, a escolha do usuário é respeitada.
- A coluna continua opcional e pode ser ativada a qualquer momento.
- O cabeçalho ganhou filtro por intervalo (`De` / `Até`) e atalhos `Hoje`, `7 dias` e `30 dias`.
- Os filtros aparecem nos badges de filtros ativos e podem ser limpos como os demais.
- A exportação Excel também respeita o intervalo de data selecionado.

## Performance

A Gestão de Estoque foi ajustada para evitar trabalho desnecessário no carregamento:

1. As opções de filtros deixaram de ser calculadas antecipadamente com vários `SELECT DISTINCT`. Agora são carregadas somente quando o usuário abre o filtro da coluna.
2. Os cartões/indicadores quantitativos passaram a usar uma única consulta agregada, em vez de vários `SUM()` separados.
3. O `COUNT(*)` do paginador é reaproveitado para `total_itens`, evitando uma contagem duplicada.
4. O filtro por data usa limites `>= início` e `< dia seguinte`, em vez de `__date`, para permitir uso eficiente do índice PostgreSQL.
5. Foi criado índice composto em `Estoque(data_ultima_movimentacao DESC, id DESC)`, que atende a ordenação principal da tela e os filtros por período.

## Migration

Foi adicionada:

`0050_estoque_indice_data_movimentacao.py`

Executar após atualizar:

```bash
python manage.py migrate
```

Nenhuma regra de saldo, empenho, transferência, carga ou restauração foi alterada nesta versão.
