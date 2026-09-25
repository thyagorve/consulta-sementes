# V12 - Correção SIGMAN modo direto

- Token direto passa a tentar primeiro `Authorization: Bearer <token>`.
- HTTP 404 de autenticação não interrompe mais a tentativa dos formatos alternativos.
- URL do painel é normalizada automaticamente, inclusive se for colado `/api`, `/api/servers` ou uma rota `/#/...`.
- Teste de conexão consulta `/api/auth/me` e depois `/api/servers`, sem alterar dados.
- Mensagem de erro 404 agora mostra a URL efetivamente consultada e orienta usar apenas a raiz do painel.
