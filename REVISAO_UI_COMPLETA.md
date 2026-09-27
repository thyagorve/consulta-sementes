# Revisão visual completa

## Lista de clientes
- Status Ativos/Desativados redesenhado como controle segmentado.
- Ativos usa verde semântico e Desativados usa tom neutro/escuro elegante.
- Planos voltaram a usar a cor cadastrada no próprio plano.
- Cada plano usa sua cor em borda, fundo suave, indicador e estado ativo.
- Contador do plano acompanha a cor do plano.
- O botão Todos continua seguindo a cor do tema.
- Corrigido o AJAX de troca Ativos/Desativados para preservar a cor do plano ao reconstruir os filtros.
- Layout responsivo mantido no celular.

## Padronização global
Foi adicionada `static/css/ui-polish.css`, carregada pelo `base.html`.

Ela padroniza em todas as telas administrativas que herdam o base:
- inputs;
- textarea;
- selects;
- seta dos selects;
- Select2;
- checkboxes;
- radios;
- campos de arquivo;
- campos de data/hora;
- color picker;
- range;
- botões nativos sem classe;
- foco e hover;
- tabelas;
- cards/painéis comuns;
- modais Bootstrap;
- paginação;
- dropdowns;
- abas;
- accordions;
- toasts/alerts;
- scrollbars.

## Selects
- Removida a seta padrão inconsistente do navegador.
- Adicionada seta SVG própria, alinhada e dimensionada de forma uniforme.
- Bordas, foco, fundo e texto seguem o tema.
- Select2 recebeu acabamento equivalente.

## Páginas antigas
- `clientes/excluir_cliente.html` foi modernizada e integrada ao `base.html`.
- `clientes/excluir_servico.html.html` foi modernizada e integrada ao `base.html`.
- Ambas usam confirmação por modal AppUI e cores coerentes com o restante do sistema.

## Regras visuais
- Cor do tema: navegação, ações principais, foco e componentes genéricos.
- Verde: sucesso/ativo.
- Vermelho: perigo/erro/exclusão.
- Cor do plano: identidade específica do plano.
- Cores próprias de integrações, como WhatsApp, permanecem quando têm significado.

## Observação
A tela pública de jogos e algumas páginas públicas/autônomas mantêm identidade própria propositalmente. A padronização global foi aplicada às páginas administrativas que herdam o `base.html` e aos fluxos antigos de exclusão que ainda estavam fora desse padrão.
