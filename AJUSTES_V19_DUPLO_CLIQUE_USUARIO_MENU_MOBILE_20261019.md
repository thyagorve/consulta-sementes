# V19 — Duplo clique preciso, usuário conectado e menu mobile

## Movimentar Estoque
- O duplo clique agora envia o ID físico do registro de estoque, não somente o lote.
- Quando um mesmo lote existe em vários endereços, abre somente o endereço clicado.
- A tela de Visualizar Estoque abre o registro já expandido.
- A linha do tempo embutida mostra somente as 12 movimentações mais recentes.
- O botão "Histórico completo" abre o Histórico Geral filtrado por lote e endereço.
- A consulta do resumo de histórico usa prefetch limitado e também antecipa usuário/fotos para reduzir N+1 queries.

## Usuário conectado
- Desktop: chip compacto na navbar com nome, identificação da sessão e nível geral (Superadmin/Administrativo/Usuário).
- Mobile: cartão no topo do menu com usuário, @username e status conectado.
- Não adiciona consultas extras ao banco; usa request.user já autenticado.

## Menu mobile
- Menu passa a abrir como painel lateral à direita.
- Backdrop escurecido e fechamento ao tocar fora.
- Cabeçalho fixo com usuário e botão de fechar.
- Itens maiores, dropdowns embutidos no fluxo e botão Sair em largura total.
- Ao navegar para uma página, o menu fecha automaticamente.

## Banco de dados
- Nenhuma migration nova.
- Nenhuma alteração em regras de estoque, empenho, carga, restauração ou saldos.
