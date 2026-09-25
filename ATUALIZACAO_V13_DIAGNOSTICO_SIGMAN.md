# V13 - diagnóstico correto do SIGMAN

- O teste de conexão não depende mais de `/api/auth/me`.
- Primeiro valida `/api/settings/public` sem credencial para separar bloqueio da VPS/CDN de erro de token.
- Depois valida autenticação com `/api/customers?perPage=1`.
- Só então consulta servidores/pacotes.
- Mantém `/api/auth/me` apenas como informação opcional.
- User-Agent ajustado para o mesmo perfil de navegador observado no HAR.
- Mensagens de erro agora diferenciam URL/CDN bloqueado de token recusado/expirado.
