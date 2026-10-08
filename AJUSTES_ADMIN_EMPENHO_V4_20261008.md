# Infinity Stock — Ajustes V4 (08/10/2026)

Base: `consulta-sementes-admin-empenho-v3-20261008.zip`, que por sua vez foi criada sobre a versão limpa do projeto.

## 1. Filtros do modal de empenho

- Corrigido o erro em que pesquisar uma opção e selecionar a única opção visível fazia o sistema interpretar como “todos” e remover o filtro.
- Todas as colunas de dados filtráveis usam o mesmo motor de filtro encadeado.
- Sem filtro ativo, todas as opções aparecem marcadas.
- `Todos` = remove a restrição da coluna.
- `Nenhum` = retorna realmente nenhuma linha.
- Valores vazios podem ser filtrados por `(vazio)`.
- O popup fica ancorado imediatamente abaixo do cabeçalho da coluna e respeita a altura visível da tabela; não pula mais para o topo da tela.
- Ao rolar horizontal/verticalmente a tabela ou redimensionar a janela, o popup fecha para não ficar solto sobre outra coluna.

## 2. Fonte da verdade dos contadores

Foi criada reconciliação central:

- `quantidade_empenhada` = soma dos `ItemEmpenho` ainda pendentes.
- `quantidade_movimentada` = soma dos `HistoricoItemEmpenho` ainda válidos.
- Movimentações restauradas deixam de contar porque o histórico operacional correspondente é removido no estorno.
- Para KG, a conta considera quantidade x peso unitário.

A reconciliação é executada antes de:

- abrir o modal de empenho;
- empenhar novos lotes;
- remover lote do empenho;
- transferir/expedir;
- editar solicitação;
- gerar relatório/impressão.

Isso corrige casos legados em que havia linha `EXPEDIDO` ou `TRANSFERIDO`, mas o card mostrava `Movimentado 0`.

## 3. Excluir lote que já foi movimentado

Para administrador:

1. Ao clicar na lixeira de um lote que possui movimentação ativa do mesmo estoque/linha, a API não exclui silenciosamente.
2. A interface informa quantas movimentações e quantas unidades já saíram.
3. Confirmando `Desfazer e excluir`, o sistema, em transação:
   - desfaz as movimentações relacionadas da mais recente para a mais antiga;
   - corrige estoque de origem/destino;
   - devolve a quantidade ao empenho;
   - atualiza os pontos de restauração;
   - só depois remove a reserva inteira do card;
   - recalcula empenhado, movimentado e status.
4. Se o estorno quebraria a integridade do estoque por existir uso posterior no destino, a operação é bloqueada e nada é excluído.

Usuário normal mantém as travas anteriores.

## 4. Pontos de restauração e botão Desfazer

Mantidos os recursos da V3:

- ponto de restauração automático em transferências/expedições;
- restauração somente por administrador;
- botão `Desfazer` nas movimentações processadas;
- estorno transacional de origem, destino, empenho e progresso do card.

## 5. Horário

O projeto continua configurado com:

- `TIME_ZONE = 'America/Sao_Paulo'`
- `USE_TZ = True`

As respostas de data/hora relevantes usam `timezone.localtime`, evitando a apresentação em UTC (+3 horas em relação ao horário de Brasília).

## 6. Migration

Nova migration de dados:

`0049_reconciliar_contadores_solicitacao.py`

Ela recalcula os contadores dos cards já existentes usando os itens pendentes e os históricos físicos válidos. Não cria novas tabelas nem remove dados.

Após atualizar o servidor:

```bash
python manage.py migrate
python manage.py check
```

## Validações realizadas no pacote

- `compileall` em `sapp`, `sementes` e `almoxarifado`: OK.
- JavaScript de `pagina_solicitacoes.html` validado com `node --check`: OK.
- Django não está instalado no ambiente de montagem do pacote, portanto `manage.py check` deve ser executado no servidor/ambiente virtual do projeto.
