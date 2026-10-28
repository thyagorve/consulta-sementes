# V14 — Transição de páginas, ações em massa nas cargas e data de movimentação

Base: V13 (Central de Sincronização).

## 1. Transição global entre páginas

Foi adicionado em `sapp/templates/sapp/base.html` um overlay global de carregamento.

- links internos exibem imediatamente uma animação de carregamento;
- formulários tradicionais exibem `Salvando e carregando...`;
- navegações disparadas por JavaScript/refresh também são cobertas pelo `beforeunload`;
- links externos, downloads, nova aba, dropdowns/modais Bootstrap e navegação por âncora não acionam o overlay;
- `pageshow`/`load` removem o overlay para não ficar preso quando o navegador usa BFCache.

Não há mudança na lógica do backend por causa desse recurso.

## 2. Gestão de Cargas — edição em massa

Nova rota:

`POST /cargas/acao-massa/`

Na página Gestão de Cargas cada carga ganhou um checkbox. É possível selecionar as cargas da página e aplicar em massa:

- Data da carga;
- Placa;
- Motorista;
- Cliente;
- Ordem de entrega.

Cada campo possui uma caixa `Trocar ...`. Campo não marcado permanece intacto. Nos campos de texto, marcar e deixar vazio significa limpar aquele valor.

Toda ação em massa exige motivo e cria `CargaAjusteLog` por movimento alterado.

### Segurança da seleção

A tela pode estar filtrada por lote/cliente/data. Por isso o backend não confia apenas nas linhas visíveis. Os IDs enviados são usados como sementes para identificar a carga e o servidor expande a seleção para **todas as movimentações ativas daquela carga** antes de alterar/excluir.

## 3. Exclusão de cargas em massa

O botão `Excluir cargas selecionadas` executa tudo dentro de `transaction.atomic()`.

Para cada movimento:

1. trava o histórico com `SELECT FOR UPDATE`;
2. trava o estoque físico relacionado;
3. reverte `saida` pela quantidade expedida;
4. salva o estoque para recalcular saldo/status/peso;
5. valida integridade do estoque;
6. preserva a linha histórica mudando o tipo para `Carga removida`;
7. grava `CargaAjusteLog`;
8. incrementa a versão de sincronização do lote.

Em cargas geradas, também marca o `HistoricoItemEmpenho` correspondente como removido e, ao final da operação inteira, executa `sincronizar_quantidades_reais()` nas solicitações afetadas para reconstruir quantidade empenhada, movimentada e status a partir da verdade física.

Se qualquer lote falhar na reversão, toda a seleção é revertida pelo banco.

## 4. Movimentar Estoque — coluna Data mov.

A tabela `Movimentar Estoque` ganhou a coluna `Data mov.` exibindo `Estoque.data_ultima_movimentacao` em `dd/mm/AAAA HH:mm`.

A coluna também entra no gerenciador de colunas e acompanha a ordenação atual da tela, que já prioriza os lotes modificados/movimentados mais recentemente.

## Arquivos principais alterados

- `sapp/templates/sapp/base.html`
- `sapp/templates/sapp/gestao_cargas.html`
- `sapp/templates/sapp/gestao_estoque.html`
- `sapp/views.py`
- `sapp/urls.py`

## Banco de dados

Não foi criada migration nesta versão.
