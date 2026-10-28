# Histórico Geral V11 - 12/10/2026

## Objetivo
Transformar o Histórico Geral em um feed operacional semelhante a "Movimentações recentes", porém completo, com paginação real no banco e filtros avançados.

## Alterações
- Página padrão com 20 registros, opções de 50, 100 e 200.
- Paginação feita pelo Django/PostgreSQL antes da renderização, sem carregar o histórico inteiro em memória.
- Busca geral nos principais campos do estoque, movimentação, carga, transporte e usuário.
- Filtros rápidos por tipo e período.
- Painel "Mais filtros" recolhido, com filtros de lote, produto, cultivar, categoria, peneira, espécie, embalagem, endereço, AZ, origem, empresa, cliente, carga, origem de carga, motorista, placa, ordem de entrega e usuário.
- Filtros específicos para carga gerada no card, carga avulsa e registros sem carga.
- Tabela geral com Data/Hora, Tipo, Lote, Produto, Cultivar/Classificação, Endereço, Origem, Empresa/Cliente, Embalagem, Quantidade, Carga, Transporte, O.E. e Usuário.
- Endereço único por linha, seguindo a lógica de Movimentações recentes: entrada mostra o endereço de entrada; saída/expedição mostra o endereço de saída.
- Detalhes expansíveis por registro, preservando descrição/observação original e informações complementares.
- Cabeçalho fixo e rolagem interna para facilitar consultas extensas.
- Resumo superior com registros filtrados, movimentos do dia, transferências e cargas encontradas.

## Banco de dados
Nenhuma migration nova é necessária.
