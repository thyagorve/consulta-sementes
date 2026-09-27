# V19 - Teste completo com dispositivo, lista, tempo e migração

## O que mudou

A tela **Testes de clientes** foi refeita para que um teste seja um cadastro novo de verdade, sem depender de um dispositivo já cadastrado.

### Criação do teste
O fluxo agora é único e sequencial:
1. Dados da pessoa: nome, WhatsApp, plano pretendido (opcional) e vencimento com data + hora.
2. Dispositivo: aplicativo, MAC e Device Key conforme as exigências do provider.
3. Lista: usuário e senha IPTV, modo de acesso e os dados necessários para M3U, Xtream ou parceria/código.
4. Publicação: ao salvar, o gestor cria o cadastro do dispositivo, cria a PlaylistRemota e tenta subir a lista imediatamente.

É possível escolher **uma lista existente de outro cliente** como origem. O formulário copia usuário, senha, DNS/URL/código quando disponíveis; o operador ainda pode alterar antes de publicar.

### Controle de tempo
- O teste usa `datetime`, portanto mantém data e hora exatas.
- A página mostra contagem regressiva em tempo real.
- No vencimento, o serviço tenta remover a lista do aplicativo e preserva o cadastro local.
- Falhas ficam com status de atenção. No IBO, quando CAPTCHA é necessário, a autenticação retoma a operação pendente.

### Migração para cliente
O botão **Migrar para cliente** não cria outra playlist.
- cria o `CustomUser` com nome, WhatsApp, plano, vencimento, valor e custo;
- reaproveita usuário/senha IPTV do teste;
- vincula o dispositivo existente ao novo cliente;
- vincula a PlaylistRemota existente ao novo cliente;
- mantém a lista remota ativa, reativando antes se o teste estiver desativado;
- transforma o TestePlaylist em histórico de conversão, evitando novo processamento por vencimento.

O plano escolhido na criação do teste é apenas uma sugestão e já vem pré-selecionado na migração; pode ser trocado na hora.

### Banco de dados
Nova migration: `0098_testeplaylist_whatsapp_plano.py`

Depois de atualizar:

```bash
python manage.py migrate
```
