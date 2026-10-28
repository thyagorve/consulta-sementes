# V16 - Hotfix do filtro Data mov.

Correção pontual sobre a V15.

## Erro corrigido
`AttributeError: 'method_descriptor' object has no attribute 'fromisoformat'`
na função `_aplicar_filtro_data_movimentacao`.

O arquivo `views.py` contém tanto `import datetime` quanto imports posteriores
`from datetime import datetime`. Como o nome global `datetime` termina apontando
para a classe, o código novo da V15 não podia usar `datetime.date` e
`datetime.datetime` como se `datetime` ainda fosse o módulo.

## Solução
O filtro agora usa apenas APIs da classe já importada:
- `datetime.strptime(...).date()`
- `datetime.combine(...)`
- `datetime.min.time()`
- `timedelta(days=1)`

Não há alteração de banco, estoque, empenho ou regras operacionais.
Não há migration nova.
