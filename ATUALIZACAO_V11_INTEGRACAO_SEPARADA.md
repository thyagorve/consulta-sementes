# V11 — Abastecimento separado da integração

- O botão **Abastecer** voltou a tratar somente créditos/lotes.
- Novo botão **Integração** na lista de planos.
- Nova página dedicada de integração por servidor.
- SIGMAN simplificado em dois modos: **Direto pelo painel** (URL + token) e **API oficial** (URL + x-painel-token + x-api-key).
- Removido da interface o campo técnico "Compatibilidade do token". O backend escolhe os headers automaticamente no modo direto.
- UniTV mantém somente os campos necessários para renovação.
- **Salvar e testar** e **Buscar planos** salvam a configuração automaticamente antes de consultar o painel.
- A configuração de política de renovação, pacote de 1 mês e pacote de teste permanece por servidor.
- Não há migration nova nesta versão.
