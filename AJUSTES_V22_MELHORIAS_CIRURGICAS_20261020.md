# V22 — Melhorias cirúrgicas sobre a V21

Base: V21 (que por sua vez preserva o comportamento da V19).

## Princípio desta versão

Esta versão NÃO cria uma nova aba de Inventário e NÃO faz a reorganização ampla da antiga V20.
O objetivo é preservar o jeito atual de trabalhar e corrigir pontos específicos de organização,
consistência histórica, exclusão de cards, mapa, segurança e desempenho.

## Menu

- Gestão de Cargas foi movida para dentro do menu Estoque.
- Almoxarifado foi movido para dentro do menu Estoque.
- O Inventário existente do Almoxarifado continua onde já estava; nenhuma segunda aba foi criada.
- Mapa do Armazém permanece junto do Estoque.
- “Visualizar Estoque” passou a “Visualizar / Consultar Estoque”, sem trocar rota ou função.
- Solicitações continua separada com Cards, Nova Solicitação e Kanban.
- Nenhuma rota funcional foi alterada apenas por causa da mudança visual do menu.

## Cards e exclusão

A exclusão agora considera o estado físico real, e não um status antigo do card:

- card sem ItemEmpenho e sem transferência/expedição ativa pode ser excluído;
- histórico já marcado como removido/estornado não prende um card vazio;
- usuário comum não pode excluir um card que ainda tem reserva pendente;
- somente superusuário pode excluir um card apenas empenhado, liberando a reserva do estoque;
- card com transferência/expedição ativa continua bloqueado até a movimentação ser desfeita/restaurada;
- a listagem envia `pode_excluir` calculado pelo backend, evitando que um status stale esconda indevidamente o botão.

## Snapshot do empenho

Os dados do lote passam a ser tratados como históricos a partir do momento do empenho.

Para itens novos, a visualização/impressão prioriza os snapshots do ItemEmpenho/Histórico:

- lote;
- código e descrição;
- produto;
- cultivar;
- peneira;
- categoria;
- espécie;
- tratamento;
- embalagem;
- empresa/cliente;
- endereço de origem;
- AZ;
- peso unitário;
- observação e conferente.

Editar posteriormente Produto, tratamento, descrição, endereço ou outros dados do estoque não deve reescrever o passado do card. O estoque atual só é usado como fallback para registros legados sem snapshot.

Ao aumentar a quantidade de um ItemEmpenho que já existe, somente a quantidade é alterada. O snapshot antigo não é regravado.

## Admin de Solicitações

- Central Administrativa e modo administrativo dos cards agora são exclusivos de superusuário.
- `is_staff` isoladamente não libera a Central Admin.
- Combinações de permissões comuns não transformam usuário normal em administrador operacional.

## Mapa

Durante filtros/pesquisas:

- endereços ocupados continuam verdes;
- endereços que correspondem ao filtro ficam amarelos;
- verde e amarelo permanecem visíveis juntos;
- o contador informa quantos endereços estão destacados;
- duplo clique/tooltip continuam funcionando também nos endereços verdes não destacados.

## Segurança

Melhorias aplicadas sem mudar a operação normal:

- usuário que pode gerenciar usuários não pode conceder uma permissão que ele próprio não possui;
- usuário comum não pode editar/desativar/resetar conta staff/superuser nem conta com permissões superiores às suas;
- alterações do Workflow exigem `pode_configuracoes` também no backend;
- pesquisa/atualização do Kanban recebeu validação de permissão no backend;
- mover card e alterar/criar tags exige permissão de movimentação de solicitação;
- endpoints administrativos do editor de mapa deixaram de usar exceção CSRF e aceitam apenas POST onde aplicável;
- exportação administrativa do mapa permanece restrita a staff;
- integração HTTP externa do Almoxarifado continua removida conforme a V21;
- não há `verify=False`, `requests.*` externos ativos ou `@csrf_exempt` em `sapp`/`almoxarifado` nesta base.

## Correções e desempenho

- removidas definições top-level antigas duplicadas de `dashboard_data`, `api_dados_impressao_solicitacao`, `api_atualizar_status_sistemico` e `processar_item_ficha`; o comportamento efetivo (última definição) foi preservado;
- removidas rotas/names duplicados em `sapp/urls.py`;
- listagem de Solicitações passou a reaproveitar prefetch de históricos e itens, reduzindo consultas por card;
- cálculo de KG na listagem prioriza peso congelado do empenho;
- nenhuma aba Inventário adicional foi criada.

## Migrações

A V22 não adiciona migration nova.

A V21 já contém a migration do Almoxarifado adicionada naquela versão. Quem ainda não a aplicou deve executar normalmente:

    python manage.py migrate

Depois da atualização, recomenda-se:

    python manage.py check

