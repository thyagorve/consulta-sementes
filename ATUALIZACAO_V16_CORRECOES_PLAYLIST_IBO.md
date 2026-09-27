# V16 - Correções no Gerenciador de playlists e IBO

Data: 2026-09-19

## Desativação no IBO

- A desativação não considera mais apenas o `200/success` retornado pelo endpoint de exclusão.
- Depois da exclusão, o gestor consulta novamente as playlists do dispositivo e confirma que o `remote_id` realmente desapareceu.
- O cadastro local só passa para **Desativada** e perde o `remote_id` depois dessa confirmação.
- Se o IBO responder sucesso mas a lista continuar aparecendo, o gestor mantém o vínculo local e informa o erro, evitando uma falsa desativação.
- O PIN salvo na playlist é reutilizado automaticamente. Se um cadastro antigo não tiver o PIN local, o código de proteção padrão configurado no gestor também é usado como fallback.
- Na chamada de exclusão do IBO, o PIN é enviado no corpo e como parâmetro para compatibilidade com variações do endpoint.

## Código de proteção

- O código não precisa mais ser digitado a cada edição.
- O PIN continua salvo apenas no backend e não é devolvido em texto para a tela.
- O modal de configuração mostra **Código de proteção salvo** quando já existe um código configurado.
- O campo para digitar código fica oculto e só aparece ao clicar em **Alterar código**.
- Novas listas recebem o código padrão automaticamente.
- Listas existentes preservam o próprio código.
- Cadastros antigos marcados como protegidos mas sem PIN local podem recuperar o código padrão configurado.

## Edições locais sem republicação

- Alterar somente dados do cadastro, como **Nome do cadastro**, não marca mais a playlist como pendente de publicação.
- O sistema compara o payload efetivamente enviado ao aplicativo antes e depois da edição.
- O botão **Atualizar no aplicativo** só passa a ser necessário quando os dados reais da playlist mudam.
- O nome do cadastro continua independente do nome técnico da playlist remota.
- Uma lista desativada pode ter o cadastro editado e continua desativada até o operador clicar em **Ativar**.

## Segurança e compatibilidade

- O PIN de proteção deixou de ser retornado em JSON para o navegador nos endpoints de detalhes.
- Nenhuma migration nova foi necessária.
