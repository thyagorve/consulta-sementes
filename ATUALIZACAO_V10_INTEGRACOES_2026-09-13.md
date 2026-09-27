# Atualização V10 — Integrações de Painel

## Entregue nesta versão

- Integração configurada por **Serviço/Servidor** em **Abastecer Créditos**.
- Cada serviço pode ter sua própria URL e credenciais.
- Tipos implementados:
  - **SIGMAN**
  - **UniTV / Resell Media**
- Políticas de renovação:
  - somente manual;
  - manual ou automático;
  - automático obrigatório.
- Renovação manual continua usando data e compartilhamento de usuário.
- Regra de crédito da renovação manual: sempre, nunca ou perguntar.
- Renovação automática troca a data por quantidade de meses.
- Antes de renovar, o sistema consulta e mostra uma prévia da conta externa.
- A conta externa é localizada usando os **dados atuais** do cliente. Nenhum ID externo fica preso permanentemente ao cliente.
- Contas compartilhadas renovam o painel apenas uma vez; **Outro já pagou** sincroniza o cadastro local sem repetir a chamada externa.
- Crédito/financeiro local são lançados apenas depois que o painel externo aceita a renovação.
- Operações possuem chave de idempotência para evitar clique/reenvio duplicado.
- Falha local depois de sucesso externo fica marcada como **Requer verificação**, sem reenviar automaticamente.
- Histórico das operações disponível na tela de abastecimento.

## SIGMAN

- Modo API oficial com `x-api-key` + `x-painel-token` quando API Key estiver configurada.
- Compatibilidade com fluxo web validado quando a instalação não usa API Key.
- Consulta de servidores/pacotes e usuários.
- Renovação automática.
- Criação de teste.
- Conversão de teste em cliente reutilizando a mesma rotina de renovação.

## UniTV / Resell Media

- Consulta de pacote.
- Localização da conta por usuário e senha atuais.
- Renovação automática, com foco de interface em **1 mês**.
- Tratamento do atraso informado pelo próprio painel para refletir a renovação, sem repetir o POST.
- Criação de usuário não foi habilitada nesta versão porque o fluxo de criação ainda não foi validado.

## Banco de dados

Foi adicionada a migration:

`clientes/migrations/0096_integracao_paineis_e_testes.py`

Após atualizar:

```bash
python manage.py migrate
python manage.py check
python manage.py collectstatic --noinput
```

Faça backup do banco antes da primeira migration em produção.
