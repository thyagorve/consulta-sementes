# V17 - Cargas: visualização, ações compactas e performance

## Visualização de carga
- Dashboard: duplo clique no nome/número da carga abre o relatório da carga.
- Gestão de Cargas: duplo clique no título da carga abre o mesmo relatório.
- Histórico Geral: clique na coluna Carga abre o relatório quando o registro é uma expedição ativa.
- Nova rota de relatório por movimento: `/cargas/movimento/<id>/relatorio/`.

## Gestão de Cargas
- Ações em massa ficam recolhidas por padrão em painel semelhante aos filtros.
- Alertas e confirmações dessa tela não usam mais `alert()`/`confirm()` do navegador; usam modal e toast do sistema.
- A troca de lote passou a usar busca sob demanda. A página não injeta mais todos os estoques em cada `<select>`.
- Agrupamento usa `iterator()` e só materializa objetos completos dos movimentos das 10 cargas visíveis.
- Busca de estoque retorna no máximo 40 resultados por consulta.

## Integridade
- Não houve alteração nas regras de saldo, reversão, empenho ou exclusão segura já existentes.
- Não há migration nova.
