# V9 — descrição por lote e movimentações recentes

Base: V8.

## Descrição por lote

- A descrição exibida no empenho e na impressão passa a pertencer ao lote/estoque daquela própria linha.
- A descrição da linha da carga não sobrescreve mais a descrição física de outros lotes.
- Quando existe Produto cadastrado pelo código do lote, sua descrição só prevalece se o cultivar configurado for compatível com o cultivar do estoque.
- Em caso de código vazio/incompatível, a descrição é montada pelos dados do próprio lote (espécie, cultivar, embalagem e tratamento).
- Novos snapshots de ItemEmpenho e HistoricoItemEmpenho guardam a descrição individual do lote.
- Relatórios antigos também tentam reconstruir a descrição pela origem física do lote, corrigindo visualmente snapshots antigos contaminados quando os dados do estoque ainda existem.

## Movimentações recentes do Dashboard

- Quantidade configurável: 20, 50, 100, 200 ou 500 registros.
- Filtro instantâneo geral por todos os campos.
- Filtro por tipo de movimentação.
- Filtro por origem operacional.
- Filtro por endereço de saída/destino.
- Novas colunas: Saída, Destino, Origem, Empresa / Cliente.
- A origem operacional usa `Estoque.origem_destino`, permitindo identificar Compra, Transferência e demais origens já cadastradas.
- Para históricos legados, os endereços de transferência são recuperados defensivamente a partir da descrição da movimentação.
- A tabela ganhou rolagem vertical e mantém o cabeçalho fixo para suportar listas grandes sem alongar demais o Dashboard.

## Banco de dados

- Nenhuma migration nova nesta versão.
