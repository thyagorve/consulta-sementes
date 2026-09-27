# V18 - Testes temporários, desativação e limpeza das integrações externas

## Gerenciador de playlists
- Todos os blocos CSS do gerenciador foram consolidados no topo do template para eliminar a troca visível de estilização durante o carregamento.
- A página fica oculta somente durante a montagem inicial e é revelada já com o layout final.
- Mensagens continuam acima dos modais.
- Alertas de testes vencidos com falha aparecem no topo do Gerenciador.
- Se o IBO precisar de CAPTCHA para concluir uma exclusão de teste, o botão **Autenticar e concluir** abre o CAPTCHA e retoma a operação.

## Desativar / Ativar
- Desativar remove a lista no aplicativo e preserva cadastro, credenciais, cliente e configurações no gestor.
- Ativar publica novamente usando o mesmo cadastro.
- FocoX e Lazer agora tentam as duas grafias conhecidas do endpoint de exclusão (`playlist_from_web` e `palylist_from_web`), com JSON e query-string como fallback, e só removem o ID local após confirmação.
- Fun Plays recebeu o mesmo tratamento de fallback e confirmação real.
- IBO mantém o fluxo de CAPTCHA e retomada automática.

## Criar teste
Nova página **Criar teste**:
- nome do teste/prospect;
- seleção do aplicativo/dispositivo já cadastrado;
- seleção opcional de um cliente existente para copiar automaticamente usuário e senha IPTV;
- usuário e senha podem ser informados manualmente;
- vencimento com data e hora;
- publicação imediata no aplicativo;
- desativação automática no vencimento;
- se a exclusão falhar, o teste fica destacado para ação do operador;
- botão para desativar imediatamente;
- botão para reativar teste com novo vencimento;
- botão **Ativar como cliente**, solicitando plano, vencimento, valor e custo e criando o cliente na tabela de clientes.

## Agendador
No `runserver` com `DEBUG=True`, o processo de testes roda automaticamente a cada 30 segundos.

Em produção, execute em um processo separado:

```bash
python manage.py processar_testes_playlist --watch
```

O Gerenciador também verifica vencimentos ao ser aberto, como camada extra de segurança.

## SIGMAN / UniTV
- Botões e páginas de integração externa foram removidos das rotas e da interface operacional.
- Renovação de cliente foi fixada no fluxo local/manual.
- O checkbox **Consumir crédito nesta renovação** foi retirado.
- Em acesso compartilhado, a decisão **Este cliente paga / Outro já pagou** passa a determinar a cobrança de crédito.
- Campos antigos no banco permanecem apenas por compatibilidade com migrações existentes, mas não participam mais do fluxo operacional.

## Banco de dados
Nova migration: `0097_testeplaylist.py`.

Após atualizar:

```bash
python manage.py migrate
```
