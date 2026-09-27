# V21 — Gerenciador: uma lista por linha

A tela do Gerenciador de playlists foi reorganizada para ficar compacta.

- Cada `PlaylistRemota` ocupa exatamente uma linha da tabela.
- Não existe mais uma linha do dispositivo seguida por outra linha expandida com a playlist.
- Se o mesmo MAC/dispositivo tiver 5 listas, aparecem 5 linhas compactas, uma para cada lista.
- MAC e aplicativo são repetidos em cada linha para facilitar leitura, filtro e operação.
- Editar, ativar/desativar, atualizar, adicionar outra lista e demais ações ficam na mesma linha.
- Excluir lista remove somente a lista selecionada; excluir o dispositivo inteiro continua separado e claramente identificado no menu “Mais”.
- Um dispositivo ainda sem nenhuma lista aparece em uma única linha com o botão “+ Lista”.
- Nenhuma mudança de banco de dados ou migration foi necessária.
