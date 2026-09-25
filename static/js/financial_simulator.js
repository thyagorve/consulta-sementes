/**
 * Simulador Financeiro v2.0 - 100% Funcional com Logs
 */
document.addEventListener('DOMContentLoaded', function() {

    const simulator = {
        scenarioId: null,
        modal: null,

        // 1. Inicialização
        init: function() {
            
            // Verifica se o Bootstrap está carregado
            if (typeof bootstrap === 'undefined') {
                console.error("❌ [ERRO] Bootstrap não foi encontrado! O Modal não vai funcionar.");
                window.AppUI.alert("Erro: O sistema de interface (Bootstrap) não carregou. Verifique o base.html.");
                return;
            }

            try {
                this.modal = new bootstrap.Modal(document.getElementById('entryModal'));
            } catch (e) {
                console.error("❌ [ERRO] Falha ao instanciar o Modal. Verifique se o ID 'entryModal' existe no HTML.", e);
            }

            this.loadScenario();
            this.bindEvents();
        },

        // 2. Capturar Token de Segurança (CSRF)
        getCookie: function(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },

        // 3. Vincular Eventos aos Botões
        bindEvents: function() {

            const btnNewEntry = document.getElementById('btnNewEntry');
            const entryForm = document.getElementById('entryForm');

            if (btnNewEntry) {
                btnNewEntry.addEventListener('click', () => {
                    entryForm.reset();
                    document.getElementById('entryDate').valueAsDate = new Date();
                    this.modal.show();
                });
            } else {
                console.error("❌ [ERRO] Botão 'btnNewEntry' não encontrado no HTML.");
            }

            if (entryForm) {
                entryForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.saveEntry();
                });
            }

            // Filtros
            document.getElementById('filterType').addEventListener('change', (e) => {
                this.refresh();
            });
            
            let timeout;
            document.getElementById('searchInput').addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.refresh();
                }, 500);
            });
        },

        // 4. Carregar Cenário Principal
        loadScenario: async function() {
            try {
                const res = await fetch('/financial/api/scenario/');
                const data = await res.json();

                if (data.success) {
                    this.scenarioId = data.scenario.id;
                    document.getElementById('scenarioInfo').innerText = `Cenário: ${data.scenario.name}`;
                    this.refresh();
                } else {
                    console.error("❌ [ERRO API] Falha ao carregar cenário:", data.error);
                }
            } catch (err) {
                console.error("❌ [FALHA REDE] Não foi possível conectar à API de cenário.", err);
            }
        },

        // 5. Atualizar Tudo
        refresh: function() {
            this.loadEntries();
            this.loadTotals();
        },

        // 6. Carregar Lista de Lançamentos
        loadEntries: async function() {
            const type = document.getElementById('filterType').value;
            const search = document.getElementById('searchInput').value;
            const url = `/financial/api/entries/?scenario_id=${this.scenarioId}&type=${type}&search=${search}`;
            

            try {
                const res = await fetch(url);
                const data = await res.json();
                
                const tbody = document.getElementById('entriesTableBody');
                const noData = document.getElementById('noDataMessage');
                
                tbody.innerHTML = '';
                if (data.entries.length === 0) {
                    noData.classList.remove('d-none');
                    return;
                }

                noData.classList.add('d-none');
                data.entries.forEach(e => {
                    const row = `
                        <tr>
                            <td class="small">${e.entry_date}</td>
                            <td><strong>${e.description}</strong></td>
                            <td><span class="badge bg-light text-dark">${e.category || 'Geral'}</span></td>
                            <td class="text-end fw-bold ${e.entry_type === 'income' ? 'text-success' : 'text-danger'}">
                                ${e.entry_type === 'income' ? '+' : '-'} R$ ${e.amount.toLocaleString('pt-BR', {minimumFractionDigits: 2})}
                            </td>
                            <td class="text-center">
                                <button class="btn btn-sm btn-link text-danger" onclick="window.simulatorInstance.deleteEntry(${e.id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                    tbody.insertAdjacentHTML('beforeend', row);
                });
            } catch (err) {
                console.error("❌ [ERRO] Falha ao renderizar tabela:", err);
            }
        },

        // 7. Carregar Totais (Cards)
        loadTotals: async function() {
            try {
                const res = await fetch(`/financial/api/totals/?scenario_id=${this.scenarioId}`);
                const data = await res.json();
                
                document.getElementById('totalIncome').innerText = `R$ ${data.total_income.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
                document.getElementById('totalExpense').innerText = `R$ ${data.total_expense.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
                
                const balanceEl = document.getElementById('totalBalance');
                balanceEl.innerText = `R$ ${data.balance.toLocaleString('pt-BR', {minimumFractionDigits: 2})}`;
                
                if (data.balance >= 0) {
                    balanceEl.className = 'mb-0 text-success';
                } else {
                    balanceEl.className = 'mb-0 text-danger';
                }
            } catch (err) {
                console.error("❌ [ERRO] Falha ao carregar totais:", err);
            }
        },

        // 8. Salvar Novo Registro
        saveEntry: async function() {
            const btn = document.getElementById('btnSubmit');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Salvando...';

            const payload = {
                description: document.getElementById('description').value,
                amount: document.getElementById('amount').value,
                entry_type: document.getElementById('entryType').value,
                category: document.getElementById('category').value,
                entry_date: document.getElementById('entryDate').value,
                include_in_balance: document.getElementById('includeInBalance').checked
            };

            try {
                const res = await fetch('/financial/api/entries/create/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCookie('csrftoken')
                    },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                if (data.success) {
                    this.modal.hide();
                    this.refresh();
                } else {
                    console.error("❌ [ERRO API] Servidor recusou os dados:", data.error);
                    window.AppUI.alert("Erro ao salvar: " + data.error);
                }
            } catch (err) {
                console.error("❌ [FALHA REDE] Erro na requisição POST:", err);
            } finally {
                btn.disabled = false;
                btn.innerHTML = 'Salvar';
            }
        },

        // 9. Deletar Registro
        deleteEntry: async function(id) {
            if (!(await window.AppUI.confirm("Deseja realmente excluir este lançamento?", {title:'Excluir lançamento', danger:true, confirmText:'Excluir'}))) return;
            
            try {
                const res = await fetch(`/financial/api/entries/${id}/delete/`, {
                    method: 'DELETE',
                    headers: { 'X-CSRFToken': this.getCookie('csrftoken') }
                });

                if (res.ok) {
                    this.refresh();
                } else {
                    console.error("❌ [ERRO API] Falha ao excluir.");
                }
            } catch (err) {
                console.error("❌ [FALHA REDE] Erro na requisição DELETE:", err);
            }
        }
    };

    // Disponibiliza o objeto globalmente para que os cliques na tabela (onclick) funcionem
    window.simulatorInstance = simulator;
    
    // Inicia tudo
    simulator.init();
});