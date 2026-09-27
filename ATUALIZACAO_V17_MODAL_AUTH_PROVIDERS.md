# V17 - Mensagens acima dos modais, retomada do IBO e revisão dos providers

Data: 2026-09-20

## Mensagens de sucesso e erro

- Os avisos do Gerenciador de playlists são movidos para o `body` e usam uma camada acima de qualquer modal.
- Sucesso, erro e informação aparecem no topo central, sem ficarem escondidos atrás do modal.
- O aviso permanece visível por 6 segundos e pode ser fechado manualmente.

## IBO: autenticar e continuar

- Se uma ação no IBO perder/precisar da autenticação, o gestor abre automaticamente o CAPTCHA.
- Depois de autenticar com sucesso, a ação que estava em andamento é retomada automaticamente.
- Coberto para publicar/reativar, atualizar no aplicativo, desativar, excluir e troca de DNS em massa.
- Ao cancelar o CAPTCHA, a ação pendente é descartada e o gestor informa que nada foi executado.
- O backend agora devolve `auth_required` e `resume_url` nas operações IBO que podem exigir nova autenticação.

## FocoX Player, Lazer Player e Fun Plays

- Revisado o fluxo de exclusão/desativação nos três providers.
- FocoX e Lazer usam a API AppAcesso e agora confirmam a exclusão consultando novamente a listagem remota.
- Fun Plays também confirma que o ID remoto realmente desapareceu após a resposta de exclusão.
- Se a API responder sucesso mas a lista continuar aparecendo, o `remote_id` local é preservado e o cadastro não é falsamente marcado como desativado.

## Compatibilidade

- Nenhuma migration nova.
- Fluxo local de edição e código de proteção da V16 preservados.
