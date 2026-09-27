# V15 - Desativar e reativar playlists

## Objetivo
Permitir retirar uma lista do aplicativo/painel sem apagar o cadastro do Gerenciador de playlists.

## Alterações
- Novo botão **Desativar** quando a lista possui ID remoto.
- A desativação chama a exclusão remota do provedor, mas preserva o cadastro local, cliente, MAC, credenciais e modo de acesso.
- Após confirmação remota, o `remote_id` é limpo e o estado interno `excluida` passa a ser exibido como **Desativada**.
- Novo botão **Ativar** para cadastros desativados. Ele reaproveita os dados salvos e publica a lista novamente, recebendo um novo ID remoto.
- Edições e troca de DNS feitas enquanto a lista está desativada não ativam a lista automaticamente. O estado continua desativado até o usuário clicar em **Ativar**.
- Histórico registra a remoção remota usada na desativação.
- A exclusão total do cadastro continua separada em **Excluir cadastro**.

## Segurança operacional
O cadastro local só é marcado como desativado depois que o provedor confirma a exclusão remota. Se a API falhar, os dados locais e o ID remoto permanecem intactos.
