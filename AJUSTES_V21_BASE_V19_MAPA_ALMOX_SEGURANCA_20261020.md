# V21 — Base V19 + Mapa no Estoque + Almoxarifado local/seguro

Esta versão foi construída **sobre a V19**, preservando o comportamento e o menu original fora dos pontos abaixo. A reforma ampla da V20 não foi reaplicada.

## Menu
- Mapa saiu do nível principal.
- Mapa do Armazém agora fica dentro do menu **Estoque**.
- Quem possui somente a permissão de mapa continua enxergando o menu Estoque com a opção Mapa do Armazém.
- Nenhum outro agrupamento do menu foi reorganizado.

## Almoxarifado — integração externa removida
- Removidas as rotas de configuração/listagem/criação/status/QR/deleção de instâncias externas.
- Removido o painel de WhatsApp/Evolution da tela principal.
- Removidas chamadas HTTP externas e todo uso de `verify=False` no app `almoxarifado`.
- O serviço antigo permanece apenas como stub local para compatibilidade com imports antigos; nunca acessa rede.
- Comandos antigos de notificação permanecem como no-op para não quebrar crons/agendadores esquecidos.
- O Dockerfile não instala/inicia mais cron para notificações externas.
- `requests` deixou de ser dependência direta do projeto porque não há mais uso direto no código Python.

## Migração 0024
Ao rodar `python manage.py migrate`:
- desativa configuração externa antiga;
- limpa URL, API key e nome de instância antigos;
- limpa números de destino antigos da configuração externa;
- desativa agendamentos externos;
- remove registros de instâncias antigas;
- remove carrinhos legados identificados como `anonimo`.

O histórico operacional de estoque e saídas não é apagado.

## Segurança do Almoxarifado
As rotas do app agora se protegem na própria view, sem depender apenas do menu ou middleware:
- listagem e consultas exigem permissão de visualizar/gerenciar;
- CRUD, baixas e carrinho exigem permissão de gerenciar;
- exportações exigem acesso ao Almoxarifado;
- endpoints de alteração aceitam somente POST quando apropriado.

## Correções de consistência
- Carrinho agora é separado pelo usuário autenticado, eliminando o fallback compartilhado `anonimo`.
- A quantidade total no carrinho não pode superar o saldo disponível.
- Baixa individual usa transação e bloqueio do registro do item.
- Finalização do carrinho usa transação e bloqueia os itens antes de descontar saldo.
- Uma falha durante a finalização não deixa metade dos itens baixados.
- Quantidade e estoque mínimo negativos são recusados.
- Ao desativar um item, referências temporárias de carrinho daquele item são removidas.
- Item inativo reencontrado ao somar quantidade é reativado corretamente.

## Performance
- `dados_validade` é carregado com `select_related`, evitando uma consulta por linha da tabela.
- Contadores e totais do topo foram consolidados em menos consultas agregadas.
- A remoção do grande módulo de WhatsApp reduz HTML/JavaScript da tela principal do Almoxarifado.
- O cron externo foi removido do container.

## Interface
- Almoxarifado passa a indicar "Operação local • sem API externa".
- Usuário apenas de visualização não recebe botões de alteração/carrinho.
- Confirmações/quantidade do carrinho usam diálogo visual do próprio sistema, em vez de `prompt()`/`confirm()` do navegador.

## Validação realizada
- Todos os arquivos Python compilados com `compileall`.
- JavaScript principal do Almoxarifado validado com `node --check` após substituição das tags Django usadas no script.
- Busca por `verify=False`, `requests.*`, URLs externas e chamadas de rede no app `almoxarifado`: nenhuma ocorrência ativa.

## Após instalar
Execute:

```bash
python manage.py migrate
python manage.py check
```

Em produção, reinicie o processo do Django/Gunicorn após a atualização.
