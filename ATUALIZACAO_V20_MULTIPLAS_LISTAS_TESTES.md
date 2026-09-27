# V20 - Correção de testes e múltiplas listas por dispositivo

Data: 26/09/2026

## Problema corrigido

Na V19, ao criar um teste usando um MAC que já estava cadastrado, o sistema tentava criar outro `IntegracaoPlaylistCliente`. Como o banco mantém um único cadastro de dispositivo por dono + aplicativo + MAC, a operação era bloqueada com a mensagem de dispositivo duplicado. Em alguns casos o cadastro do teste/playlist local já havia sido salvo, mas a publicação remota falhava e o teste ficava em erro com mensagens como `Device not found`.

## Novo comportamento

- Um dispositivo físico continua tendo apenas um cadastro no gestor.
- O mesmo dispositivo pode ter várias `PlaylistRemota` independentes.
- A tela Criar teste permite escolher um dispositivo já cadastrado.
- Se o operador digitar um MAC que já existe no mesmo aplicativo, o backend reaproveita automaticamente esse dispositivo.
- Cada teste cria uma NOVA playlist. As playlists que já estavam no dispositivo não são alteradas.
- O Gerenciador mostra todas as listas de cada dispositivo e disponibiliza `+ Lista` para adicionar outras listas ao mesmo MAC.
- Editar o dispositivo altera somente nome/cliente/MAC/Device Key e não modifica a primeira playlist por acidente.
- Desativar uma lista remove somente aquela lista do aplicativo. Se houver outras listas ativas no mesmo dispositivo, o dispositivo permanece com status ativo.
- Na migração de teste para cliente, somente a playlist daquele teste é vinculada ao novo cliente quando o dispositivo já era compartilhado com outras listas. As demais listas permanecem intactas.

## Registros antigos com Device not found

Quando um teste antigo nunca chegou a ser publicado e não possui ID remoto, o processador reconhece falhas de publicação como `Device not found`. Ao vencer, ele encerra o teste localmente em vez de tentar excluir uma lista inexistente para sempre. O cadastro permanece preservado.

## Banco de dados

Não há migration nova nesta versão. O modelo `PlaylistRemota` já permitia várias listas vinculadas ao mesmo `IntegracaoPlaylistCliente`; a V20 ajusta o fluxo e a interface para usar corretamente essa estrutura.
