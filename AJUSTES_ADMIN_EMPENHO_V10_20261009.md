# Ajustes V10 - Dashboard / Movimentações recentes

## Endereço por tipo de movimentação
A tabela de Movimentações recentes agora possui apenas uma coluna **Endereço**.

- Transferência (Saída), Saída, Expedição e Baixa: mostra o endereço de saída/origem física.
- Transferência (Entrada) e Entrada: mostra o endereço de destino/entrada física.

A tabela não exibe mais Saída e Destino ao mesmo tempo para o mesmo registro.

## Filtros recolhidos
Os filtros de Movimentações recentes ficam fechados por padrão e são abertos pelo botão **Filtros**. Um contador informa quando há filtros ativos.

## Limite padrão
A listagem carrega **20 movimentações por padrão**. O seletor no cabeçalho permite trocar para 50, 100, 200 ou 500 registros.

A preferência escolhida é salva no navegador em uma chave nova, portanto instalações que tinham 50 salvo na versão anterior começam em 20 na V10.

## Validação
- Python: compileall sem erros.
- JavaScript inline do Dashboard: node --check sem erros após remoção das marcações de template Django.
- Sem migration nova.
