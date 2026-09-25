# Revisão do Dashboard

Esta rodada foi aplicada sobre `painel-main-ajuste-modal-envio.zip` e preserva os ajustes anteriores de modais, static, temas, playlists, financeiro e envio em massa.

## Correções do Dashboard

- Corrigido erro JavaScript que interrompia os gráficos: `withAlpha()` era chamado mas não existia.
- Chart.js agora é carregado uma única vez pelo `base.html`, fixado no major `@4` para manter a API estável.
- Gráficos são recriados automaticamente ao trocar o tema, atualizando cores de linhas, textos, grid e bordas sem recarregar a página.
- Adicionado estado visual quando não existe movimentação para o gráfico, em vez de deixar um quadro vazio.
- Dados dos gráficos agora usam `json_script` do Django. Isso evita quebra do JavaScript com nomes contendo apóstrofos, aspas ou caracteres especiais e melhora a segurança.
- Corrigida a condição do gráfico "Top Clientes": a string JSON `"[]"` era considerada verdadeira pelo template e podia renderizar gráfico vazio.
- Removida dependência direta de `showPicker()` nos seletores de data/hora. O input nativo continua clicável e compatível com mais navegadores.
- Limite de data/hora passa a usar o horário do servidor, evitando diferenças de fuso do computador do usuário.
- Atalhos de teclado do Dashboard não interferem mais quando o foco está em input, select, textarea ou botão.

## Métricas e histórico

- Todos os relatórios financeiros continuam limitados ao instante exato selecionado.
- Clientes criados depois da hora escolhida no mesmo dia deixam de aparecer no snapshot.
- Compras de créditos e consumos também respeitam a hora selecionada.
- Em datas históricas, o saldo de créditos é reconstruído por lote usando quantidade comprada menos consumos registrados até o instante escolhido. Antes era usado `quantidade_restante` atual.
- Custo médio do crédito passa a ser ponderado pela quantidade restante dos lotes no instante consultado.
- Semana do Dashboard foi padronizada para domingo a sábado em Receita Semanal, Lucro Semanal, Ranking Semanal e Previsão Semanal.
- Crescimento mensal agora compara o mês atual até o dia selecionado com o mesmo intervalo do mês anterior, evitando comparar 7 dias contra um mês inteiro.
- Previsão líquida anual foi corrigida para somar o líquido já realizado e descontar apenas o custo da parte futura.
- Labels do gráfico de 12 meses agora usam abreviações em português de forma independente do locale do servidor.

## Clientes compartilhados

- Corrigido agrupamento de `login_externo` vazio. Antes todos os clientes com `login_externo=""` podiam ser tratados como um único cliente para custos/estoque.
- Compartilhamento agora é considerado por `login_externo + plano`, evitando juntar o mesmo username que exista em servidores/planos diferentes.
- Clientes sem login externo, nulo ou vazio, contam individualmente.

## Arquivos principais alterados

- `clientes/views.py`
- `clientes/templates/dashboard.html`
- `clientes/templates/base.html`

## Banco de dados

Nenhuma migration nova foi criada nesta rodada.
