# V13 - Central de Sincronização

- Corrigido contraste/legibilidade do modal da Central de Sincronização.
- Cores explícitas impedem que estilos globais do tema deixem textos e badges esbranquiçados.
- Adicionado botão **Limpar** no cabeçalho.
- O botão só atua nas abas **Sincronizadas** e **Rejeitadas**.
- Pendências e conflitos nunca são apagados pelo botão.
- Limpar remove a cópia local finalizada e oculta a operação naquela Central/dispositivo.
- O registro oficial no servidor continua preservado para auditoria.
- IDs ocultos são guardados no IndexedDB específico do usuário/dispositivo, limitados aos 2.000 mais recentes.
- Atualizado cache-busting do JS e versão do shell do Service Worker para forçar a entrega do ajuste.
- Não há migration nova.
