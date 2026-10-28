# V22 — Estoque, Cards, Snapshot e Mapa

Base: V21 (que por sua vez preserva a estrutura visual/funcional da V19).

## Menu e organização

- Gestão de Cargas foi movida para o menu **Estoque**.
- Mapa do Armazém permanece dentro de **Estoque**.
- Almoxarifado e Inventário do Almoxarifado ficam dentro do bloco **Estoque**.
- Solicitações permanece separada, contendo Cards, Nova Solicitação e Kanban.
- O rótulo da consulta de estoque passa a ser **Visualizar / Movimentar Estoque** para quem possui permissão de movimentação; usuário somente consulta continua vendo **Visualizar Estoque**.
- As permissões de cada item continuam independentes. Mover um item no menu não concede acesso novo.

## Exclusão de cards pela verdade física

- Antes de excluir, o card é reconciliado a partir dos ItemEmpenho e HistoricoItemEmpenho reais.
- Card sem reserva pendente e sem transferência/expedição válida pode ser excluído mesmo se o status antigo tiver ficado concluído/cancelado.
- Histórico legado do tipo `removido` não é tratado como movimentação física e não bloqueia a exclusão.
- Card com reserva pendente só pode ser excluído diretamente pelo superadministrador; ItemEmpenho.delete() libera a reserva no estoque.
- Card com transferência/expedição válida continua bloqueado. É necessário desfazer a movimentação administrativa primeiro.

## Snapshot imutável no empenho

O lote selecionado passa a ser tratado como um documento histórico do momento do empenho.

Depois de empenhado, alterações posteriores no cadastro do Estoque/Produto não reescrevem no card:

- lote;
- descrição;
- produto;
- cultivar;
- peneira;
- categoria;
- espécie;
- tratamento;
- embalagem;
- empresa/cliente;
- endereço e AZ de origem;
- peso unitário;
- observação;
- conferente.

Apenas os dados físicos necessários à operação, como saldo/disponível/status atual, continuam sendo lidos do Estoque atual.

- Aumentar/reduzir a quantidade de um ItemEmpenho existente não atualiza o snapshot.
- O relatório/impressão e a transferência/expedição usam o snapshot original.
- Histórico de movimentação recebe os dados do snapshot, e não os dados atuais editados do lote.
- Restauração administrativa reaplica o snapshot histórico após recriar o ItemEmpenho.
- Trocar explicitamente o lote pela Central Administrativa cria um novo snapshot do novo lote, pois é uma escolha administrativa intencional.

Registros antigos que nunca tiveram determinado campo salvo no snapshot usam fallback do estoque atual somente para o campo ausente. O sistema não inventa um valor histórico que não foi armazenado.

## Admin das Solicitações

- Botão/Modo Admin das Solicitações e Central Administrativa passam a ser exclusivos de **superusuário**.
- Permissões funcionais comuns e `is_staff` não promovem o usuário para esse modo.
- A validação existe no backend, não apenas no botão da tela.

## Mapa do armazém

- Filtros não apagam mais os endereços ocupados do mapa.
- Endereço ocupado normal permanece **verde**.
- Endereço/lote que corresponde ao filtro fica **amarelo**.
- A legenda explica verde x amarelo durante filtro ativo.
- Duplo clique/abrir lote usa `estoque_id` quando disponível, abrindo exatamente o registro físico/endereço selecionado.

## Inventário de Estoque

- A tela ganhou filtros locais rápidos por busca/status e opção "Só diferenças" sem novas requisições ao servidor.
- Mostra contador de resultados filtrados.
- Cada linha encontrada pode abrir exatamente o registro físico no Estoque por `estoque_id`.
- Atalhos para **Inventário do Almoxarifado** e **Almoxarifado** foram incorporados à tela.

## Performance

- A API do modal de empenho carrega relações do estoque via `select_related`, evitando consultas extras por lote ao mostrar snapshots.
- Descrição de lote não é recalculada ao apenas alterar quantidade de um empenho já existente.
- Listagem dos cards calcula empenhado/movimentado pela verdade física usando relações prefetched, sem consulta adicional por card.
- Filtros do inventário de comparação são client-side e usam cache do texto normalizado das linhas.

## Banco de dados

- Nenhuma migration nova nesta versão.
- Não altera esquema do banco.
