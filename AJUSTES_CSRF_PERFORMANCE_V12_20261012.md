# V12 — CSRF e Performance

Base: V11. Esta versão não altera regras de saldo, empenho, transferência, restauração ou carga.

## CSRF / login
- Login, logout, troca de senha e admin não são mais guardados no Cache Storage do PWA.
- Caches HTML de versões antigas são removidos na ativação do novo Service Worker.
- O login renova o campo CSRF a partir do cookie atual antes do POST (protege inclusive contra BFCache).
- Um CSRF obsoleto no login não desativa a proteção: o servidor redireciona para um GET limpo do login.

## Sessão / banco
- Sessões usam `cached_db`: cache rápido com PostgreSQL como fallback/durabilidade.
- `SESSION_SAVE_EVERY_REQUEST=False`.
- `last_activity` é persistido no máximo uma vez por minuto.
- Pollings automáticos não contam como atividade humana e não ficam gravando `django_session`.
- Conexões PostgreSQL são reaproveitadas por 60s (`DATABASE_CONN_MAX_AGE`, configurável).
- `CONN_HEALTH_CHECKS=True`.

## Consultas
- Permissões individuais são carregadas uma vez por request e reutilizadas.
- Pollings passivos evitam a consulta de `PerfilUsuario`.
- A versão de cargas tem cache curtíssimo de 3s para compartilhar o cálculo entre clientes.
- Dashboard verifica versão a cada 5s (antes 2,5s) e pausa quando a aba está oculta.

## PWA
- Removido o segundo GET da página que o `offline-sync.js` disparava após cada abertura.
- O próprio Service Worker continua fazendo network-first nas telas operacionais.
- Filas offline continuam no IndexedDB e não são apagadas pela limpeza de cache HTML.

## Estáticos
- WhiteNoise passa a gerar conteúdo estático comprimido em `collectstatic`.
- Logo reduzida para 512x512 mantendo PNG/transparência, adequada ao manifesto PWA.
