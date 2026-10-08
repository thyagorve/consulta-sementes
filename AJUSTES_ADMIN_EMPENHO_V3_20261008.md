# Ajustes Admin / Empenho V3 - 08/10/2026

Base: versão limpa do projeto enviada pelo usuário. A versão antiga do GitHub com arquivos misturados não foi usada como base.

## 1. Quantidade solicitada liberada para administrador

- Administrador operacional pode editar a quantidade mesmo após empenho, movimentação, conclusão ou cancelamento.
- O campo de quantidade da carga deixa de ficar cinza/bloqueado para admin.
- O único piso da quantidade informada pelo admin é o que **ainda está empenhado/reservado**. O histórico já movimentado não bloqueia a correção da meta.
- Em CARGA, o admin também pode editar o total diretamente em "Quantidade total da carga". O backend distribui o ajuste pelas linhas sem reduzir nenhuma linha abaixo do que ainda está empenhado.
- Linhas de carga já utilizadas podem ser corrigidas pelo admin, mas linhas com histórico não são excluídas para preservar rastreabilidade.

## 2. Reabertura correta de card concluído

O status passa a considerar separadamente:

- quantidade solicitada (meta atual);
- quantidade já movimentada (histórico físico);
- quantidade ainda empenhada (reserva pendente).

Exemplo esperado:

1. 12 solicitados / 12 movimentados / 0 empenhados = **CONCLUÍDO**;
2. admin aumenta para 14 = **AGUARDANDO EMPENHO**;
3. admin/usuário empenha os 2 novos = **MOVIMENTAÇÃO PARCIAL**;
4. movimenta os 2 novos = **CONCLUÍDO** novamente.

O histórico antigo permanece intacto. Aumentar a meta não zera o que já foi movimentado.

## 3. Progresso dos cards

- O card não usa mais somente o empenho pendente para calcular progresso.
- O progresso operacional usa `movimentado + empenhado pendente` em relação à meta atual.
- A interface mostra separadamente o que já foi movimentado e o que continua empenhado.

## 4. Desfazer transferência / expedição

- Na própria janela de Transferência/Expedição, o admin recebe botão **Desfazer** nos itens já processados.
- A Central Administrativa também permite desfazer uma movimentação específica ou a última movimentação do card.
- O estorno é transacional: recompõe origem/destino, recria o ItemEmpenho e reduz a quantidade movimentada.
- Depois do estorno, status e workflow são recalculados.
- Se uma movimentação posterior tiver consumido/reservado estoque de forma que o estorno deixaria o saldo impossível, a restauração é recusada em vez de corromper o estoque.

## 5. Pontos de restauração

- Cada transferência/expedição de item empenhado cria automaticamente um ponto de restauração, independentemente de quem fez a movimentação.
- Somente administrador operacional pode executar a restauração.
- A migration cria pontos também para históricos de solicitações já existentes.
- A Central Administrativa exibe os pontos e permite restaurar os disponíveis.
- O Django Admin também lista esses pontos para auditoria.

## 6. Horário correto

- O projeto continua configurado com `TIME_ZONE = 'America/Sao_Paulo'` e `USE_TZ = True`.
- Formatações manuais das telas/APIs principais agora passam por `timezone.localtime()`.
- Rotinas do almoxarifado que usavam `datetime.now()`/`date.today()` foram alteradas para o horário/data local do Django, evitando o servidor aparecer 3 horas adiantado quando roda em UTC.
- Timestamps ISO retornados pelo backend passam a incluir o deslocamento local configurado.

## 7. Usuário normal

- As liberações administrativas não removem as travas do usuário normal.
- Usuário comum continua bloqueado nas situações antigas após o início da movimentação/conclusão.

## 8. Banco de dados

Esta versão adiciona a migration:

`0048_ponto_restauracao_movimentacao.py`

Depois de atualizar o projeto, execute:

```bash
python manage.py migrate
```

Recomendado também:

```bash
python manage.py check
```

## 9. Validação feita no pacote

- Compilação sintática de todos os arquivos Python.
- Verificação dos scripts JavaScript dos templates alterados.
- O ambiente de empacotamento não possui Django instalado, portanto `manage.py check` precisa ser executado no servidor/venv do projeto.
