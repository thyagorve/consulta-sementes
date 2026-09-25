# Integração de painéis: SIGMAN e UniTV / Resell Media

## Objetivo
Cada `Servico` do gestor pode ter a sua própria URL e credencial de painel. A renovação continua podendo ser manual, facultativa ou automática obrigatória.

## Configuração
Abra **Serviços > Abastecer Créditos** no servidor desejado e configure a seção **Integração do servidor**.

Campos principais:
- Ativar integração
- Tipo: SIGMAN ou UniTV / Resell Media
- Política: somente manual, manual ou automático, automático obrigatório
- URL do painel/API
- Token e, quando aplicável, API Key/identificador da revenda
- servidor externo e pacote de 1 mês
- pacote de teste (SIGMAN)
- regra de consumo de crédito na renovação manual

Use **Salvar integração**, depois **Testar conexão** e **Buscar planos**.

## Renovação
### Manual
Mantém o fluxo de data do gestor e o tratamento de compartilhamento. A regra do servidor pode definir se consome crédito sempre, nunca ou pergunta no momento da renovação.

### Automática
1. O gestor usa o usuário/senha atuais do cliente.
2. Consulta o painel e bloqueia resultados ausentes/ambíguos.
3. Mostra uma prévia com conta, plano, vencimento e créditos necessários.
4. Só após confirmação envia a renovação externa.
5. O crédito local e o financeiro são lançados somente após o painel aceitar a operação.
6. Em compartilhamento, **Outro já pagou** apenas sincroniza o cadastro local e não renova o painel novamente.

O ID externo encontrado durante a consulta não é salvo como vínculo permanente no cliente.

## SIGMAN
Suporta:
- consulta de servidores/pacotes
- consulta segura de cliente
- cálculo prévio dos créditos
- renovação
- criação de teste
- conversão do teste em cliente pela mesma rotina de renovação

### Modos de acesso SIGMAN
Quando **API Key** e **Token** estão configurados, o gestor usa a API oficial com os headers `x-api-key` e `x-painel-token`, incluindo os fluxos `/users`, `/user-renew` e `/user`.

Se a instalação SIGMAN não disponibilizar API Key, o adaptador mantém um modo de compatibilidade baseado no fluxo web validado no HAR, usando os endpoints de clientes/renovação do próprio painel. O campo **Compatibilidade do token** só é relevante nesse modo sem API Key.

## UniTV / Resell Media
Suporta nesta versão:
- consulta de pacotes
- localização da conta por usuário/senha
- renovação, com foco inicial em 1 mês

O painel pode informar que a renovação demora alguns minutos para aparecer. Quando aceita, o gestor registra a operação e não repete automaticamente a chamada.

Criação de usuário UniTV não foi habilitada porque o fluxo de criação ainda não foi fornecido/validado por HAR.

## Segurança e auditoria
A tabela `OperacaoIntegracaoPainel` registra as operações e a chave de idempotência impede repetir a mesma renovação por clique duplo/reenvio. Se houver incerteza depois de uma chamada externa, o status fica como **Requer verificação** em vez de reenviar automaticamente.

As últimas operações ficam disponíveis em **Abastecer Créditos > Ver últimas operações da integração**.

## Banco de dados
Após atualizar o projeto:

```bash
python manage.py migrate
python manage.py check
python manage.py collectstatic --noinput
```

A migration adicionada é `0096_integracao_paineis_e_testes.py`.
