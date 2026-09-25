# Teste SIGMAN em modo somente leitura

Esta etapa existe para validar a integração antes de qualquer importação ou alteração no banco local.

## O que o comando faz

- testa `GET /me`;
- consulta `GET /users`;
- exibe nome, usuário IPTV, senha, plano, vencimento, status, telas e servidor quando esses campos vierem da API;
- opcionalmente consulta `GET /playlist` para um usuário;
- **não cria, não renova, não bloqueia e não salva nada no banco**.

## Credenciais

A documentação pública da API SIGMAN exige dois headers:

- `x-api-key`
- `x-painel-token`

Por segurança, prefira variáveis de ambiente para que as credenciais não fiquem no histórico do terminal.

### Linux / VPS

```bash
export SIGMAN_API_URL="https://apiiptv.quickgestor.com/api"
export SIGMAN_API_KEY="SUA_API_KEY"
export SIGMAN_PAINEL_TOKEN="TOKEN_DO_SEU_PAINEL"
python manage.py testar_sigman --limite 20
```

Para mostrar as senhas completas:

```bash
python manage.py testar_sigman --limite 20 --mostrar-senhas
```

Para buscar um cliente específico:

```bash
python manage.py testar_sigman --usuario 123456789 --mostrar-senhas
```

Para inspecionar também o retorno da playlist:

```bash
python manage.py testar_sigman --usuario 123456789 --playlist --raw
```

### PowerShell

```powershell
$env:SIGMAN_API_URL="https://apiiptv.quickgestor.com/api"
$env:SIGMAN_API_KEY="SUA_API_KEY"
$env:SIGMAN_PAINEL_TOKEN="TOKEN_DO_SEU_PAINEL"
python manage.py testar_sigman --limite 20
```

## Próxima etapa

Somente depois que o retorno estiver conferido, a integração pode ganhar uma tela de pré-visualização e um botão explícito de importação/sincronização. Nenhum usuário deve ser adicionado automaticamente apenas ao salvar a configuração da API.
