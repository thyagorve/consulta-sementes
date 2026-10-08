# Ajustes V8 - trava de quantidade comprometida

## Regra central
A quantidade solicitada de uma solicitação com meta finita nunca pode ser menor que a soma de:

- quantidade já movimentada e ainda válida no histórico; mais
- quantidade ainda pendente no empenho.

Exemplo: 2 BAG pendentes + 1 BAG expedido = mínimo permitido de 3 BAG.
Para reduzir a meta para 2 BAG, o administrador deve primeiro desfazer a movimentação ou remover corretamente uma reserva pendente.

## Onde a trava foi aplicada
- formulário normal de edição usado pelo administrador;
- linhas individuais de cargas;
- total geral de cargas;
- Central Administrativa;
- validação de backend, independentemente do atributo `min` do HTML.

## Reparação de inconsistências antigas
A sincronização da solicitação passa a reparar metas finitas antigas que estejam abaixo do total fisicamente comprometido. Assim, um card salvo anteriormente como 2 solicitados, mas com 2 pendentes + 1 movimentado, é corrigido para 3 ao ser reconciliado.

Cargas abertas (quantidade solicitada igual a zero) continuam com a semântica de carga aberta.

## Interface
O campo de quantidade do admin mostra como mínimo o total `movimentado + empenho pendente`. Em cargas, cada linha utilizada também recebe seu próprio mínimo físico.

## Banco
Esta versão não adiciona migration.
