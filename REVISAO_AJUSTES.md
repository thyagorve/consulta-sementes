# Revisão do Painel

Esta versão concentra os ajustes solicitados para envio em massa, WhatsApp, gerenciador de playlists, experiência visual e segurança.

## Principais alterações

### Envio em massa
- Rotas antigas conflitantes foram separadas das rotas canônicas.
- Rascunho, envio imediato e agendado usam a mesma fila persistente de `HistoricoEnvioMassa`.
- O botão **Enviar agora** coloca a campanha na fila com execução imediata pelo processador, evitando prender o worker HTTP durante lotes grandes.
- O processador usa advisory lock do PostgreSQL para impedir duas execuções simultâneas do mesmo cron.
- Uma campanha exige `EVOLUTION_API_BASE_URL` e `EVOLUTION_GLOBAL_API_KEY` antes de iniciar.
- Falha ao preparar mídia agora falha aquele envio. O sistema não transforma silenciosamente um envio com mídia em mensagem somente de texto.
- O processador oficial é `python manage.py processar_envio_massa`. Foi removido o processador duplicado que existia em `views.py`.

### Pareamento WhatsApp
- O fluxo aceita QR Code e `pairingCode` quando a Evolution utilizada oferecer esse retorno.
- O pareamento por número normaliza o telefone e valida o formato antes da chamada.
- Exceções internas da Evolution não são mais devolvidas diretamente ao navegador.
- A desconexão usa o endpoint/view correto sem apagar o cadastro local por engano.

### Gerenciador de playlists
- Dispositivo e primeira playlist podem ser cadastrados no mesmo modal/operação.
- Foi adicionada configuração de **Device Key padrão** para novos cadastros.
- Credenciais e detalhes sensíveis são buscados somente ao clicar em **Ver detalhes**, com autenticação, filtro pelo dono e `Cache-Control: no-store`.
- A lista de clientes ganhou acesso direto para cadastrar um aplicativo já associado ao cliente.
- A troca de DNS em massa aceita seleção de playlists.
- No IBO, quando a autenticação expira, o backend devolve uma fila de aparelhos que precisam de CAPTCHA e a interface percorre essa fila sequencialmente.
- Quando um provedor não oferece edição remota segura, a alteração fica pendente em vez de apagar/recriar a playlist automaticamente.

### Interface
- Foi criado `window.AppUI` como modal global para alertas e confirmações.
- Alertas nativos ativos foram substituídos por modais.
- Confirmações de ações destrutivas usam modal com confirmação explícita.
- Fluxos que recarregam a página depois de salvar agora aguardam o usuário fechar o modal de sucesso.

### Segurança e limpeza
- Removidos fallbacks com chave da Evolution escrita diretamente no código.
- O startup não copia mais a chave global da Evolution para cada registro de instância no banco.
- Recuperação de senha foi vinculada à sessão, possui expiração e limite de tentativas de código.
- O código de recuperação não é devolvido no JSON.
- Respostas 500 sensíveis foram trocadas por mensagens genéricas, mantendo detalhes no log do servidor.
- O webhook aceita segredo dedicado por `X-Webhook-Secret` ou Bearer quando `EVOLUTION_WEBHOOK_SECRET` estiver configurado.
- Logs de tarefas deixaram de imprimir texto completo de mensagens e corpo da resposta da Evolution.
- O DRF expõe apenas JSON em produção. O Browsable API fica disponível somente com `DJANGO_DEBUG=True`.
- Backups SQL, caches, pycache e arquivos de depuração não devem fazer parte do pacote de produção.
- Rotas duplicadas de IBO/dispositivo/envio em massa foram consolidadas.
- Arquivos de lixeira e cópias sem referência foram removidos de forma conservadora.

## Atualização do banco

Há uma migration nova para a Device Key padrão e normalização dos status da integração:

```bash
python manage.py migrate
```

## Envio em massa no servidor

No Dockerfile desta versão, o comando abaixo está programado a cada minuto:

```bash
python manage.py processar_envio_massa
```

Se o projeto for executado fora desse Dockerfile, configure um cron equivalente. Sem o processador periódico, as campanhas ficam corretamente salvas na fila, mas não são disparadas automaticamente.

## Variáveis de ambiente

Use `.env.example` apenas como referência e mantenha o `.env` real fora do repositório/pacote. Em produção, configure principalmente:

- `SECRET_KEY`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `EVOLUTION_API_BASE_URL`
- `EVOLUTION_GLOBAL_API_KEY`
- `EVOLUTION_WEBHOOK_URL`
- `EVOLUTION_DIRECT_WEBHOOK_PATH`
- `EVOLUTION_WEBHOOK_SECRET`

Como uma chave da Evolution já esteve gravada no código antigo, recomenda-se **rotacionar essa chave** ao publicar esta versão.

## IBO e CAPTCHA

CAPTCHA não é burlado. Quando exigido pelo IBO, o lote pausa logicamente aquele aparelho, solicita a autenticação e continua a sequência após o usuário concluir o CAPTCHA.

## Sigmar

A renovação automática do Sigmar não foi implementada nesta revisão porque depende do contrato/API real do Sigmar. A base ficou mais adequada para essa próxima etapa: fila persistente, operações idempotentes, histórico por destinatário, isolamento por dono e integração de playlists separada por provedor.

Para a futura integração, prefira um serviço dedicado do Sigmar que gere um evento de renovação idempotente e só depois atualize cliente, vencimento, playlist e WhatsApp. Assim uma repetição do webhook não renova o mesmo cliente duas vezes.

## Observação

Conforme solicitado, esta entrega prioriza a lógica e a integração do código. Não foram executados testes contra suas APIs externas, banco de produção, IBO real ou Evolution real neste ambiente.

## Revisão visual adicional - tema, modais e lista de clientes

- Modal global `AppUI` redesenhado para usar `--primary`, `--primary-light`, `--bg-card`, `--border` e demais variáveis do tema ativo.
- Confirmações destrutivas continuam sinalizando risco no ícone, mas o botão principal segue a cor do tema para manter o padrão visual do sistema.
- Modal de exclusão de cliente refeito, removendo estilos inline/emoji e adotando o mesmo padrão dos demais modais.
- Modais de saldo, exclusão, indicação e tags na lista de clientes receberam acabamento unificado e responsivo.
- Filtro de planos da lista de clientes convertido para chips compactos com rolagem horizontal, contador e pequeno indicador da cor do plano.
- Corrigida a reconstrução AJAX dos filtros de plano: após trocar Ativos/Desativados, os planos continuam com o mesmo layout novo.
- Adicionada opção visual `Todos` para limpar o filtro de plano.
- Badge de plano na tabela ficou mais discreto: interface segue o tema e a cor própria do plano aparece apenas como indicador.
- Botões das ações expandidas do cliente foram padronizados para reduzir excesso de cores e seguir o tema.
- Histórico de mensagens antigo foi modernizado e passou a usar a confirmação global em modal.
- Cores principais fixas antigas em Configuração de Mensagens, Avisos e modais relacionados foram substituídas por variáveis do tema onde eram apenas cor de interface.
- Modal PIX/cliente antigo passou a respeitar fundo, texto, borda e cor principal do tema.

Observação: cores semânticas foram preservadas quando têm significado próprio, por exemplo WhatsApp, sucesso, alerta, vencimento e erro.
- Removidas funções JavaScript duplicadas de filtro/pesquisa na lista de clientes; agora há uma única implementação ativa para status, plano, URL e busca.
