# V18 - Relatório de carga no padrão original

## Objetivo
Corrigir a visualização aberta a partir da Gestão de Cargas, Histórico e Dashboard para ficar no mesmo padrão visual do relatório de carga/expedição já usado nos cards.

## Ajustes
- Removido o layout alternativo criado na V17.
- Relatório histórico agora usa o mesmo desenho compacto do relatório original:
  - cabeçalho verde;
  - ID/card e nome da carga;
  - status;
  - quantidade solicitada, empenhada e movimentada;
  - equivalente em sacos;
  - motorista, placa, criação, atualização e finalização;
  - destino e observação;
  - tabela compacta de itens;
  - assinaturas de conferente e motorista;
  - rodapé e botões de imprimir/fechar.
- Para cargas GERADAS, recupera o vínculo com a solicitação/card através do HistoricoItemEmpenho.
- Os dados de lote das cargas geradas usam snapshots históricos do empenho quando disponíveis, evitando depender do cadastro atual do estoque.
- As movimentações ativas continuam sendo a fonte de verdade para definir quais itens pertencem à carga.
- Formatação brasileira de quantidade e peso.
- Nenhuma migration nova.

## Segurança
Nenhuma regra de saldo, empenho, exclusão de carga ou restauração foi alterada.
