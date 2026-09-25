// ===== FUNÇÕES JAVASCRIPT PARA LISTA DE CLIENTES =====

// Função para alternar detalhes do cliente
function toggleDetails(button) {
    const row = button.closest("tr").nextElementSibling;
    const icon = button.querySelector('i');

    if (!row) {
        console.error('Linha de detalhes não encontrada');
        return;
    }

    if (row.style.display === "none" || row.style.display === "") {
        row.style.display = "table-row";
        icon.className = "fas fa-chevron-up";
        button.classList.add('active');
    } else {
        row.style.display = "none";
        icon.className = "fas fa-chevron-down";
        button.classList.remove('active');
    }
}

// Funções de modal
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        document.body.style.overflow = 'hidden';
        modal.style.display = 'flex';
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);
        
        // Foco no primeiro campo
        const firstInput = modal.querySelector('input, select, textarea');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    } else {
        console.error(`Modal com ID ${modalId} não encontrado.`);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }, 300);
    }
}

// Função para abrir modal de saldo
// Função para abrir modal de saldo (CORRIGIDA PARA SEU HTML ATUAL)
function openSaldoModal(button) {
    const clienteId = button.getAttribute("data-id");
    
    // 1. Identifica a linha onde o botão está (Linha de Detalhes)
    const currentRow = button.closest('tr');
    
    let clienteNome = "Cliente"; // Nome padrão caso falhe
    let nomeElement = null;

    // 2. A lógica precisa buscar o nome na linha DE CIMA (previousElementSibling)
    // pois o botão está na linha de detalhes expandida
    if (currentRow && currentRow.previousElementSibling) {
        nomeElement = currentRow.previousElementSibling.querySelector('.cliente-nome');
    }

    // 3. Fallback: Se não achou na de cima, tenta na própria linha 
    // (caso algum dia o botão seja movido para a linha principal)
    if (!nomeElement && currentRow) {
        nomeElement = currentRow.querySelector('.cliente-nome');
    }

    // 4. Se encontrou o elemento, pega o texto
    if (nomeElement) {
        clienteNome = nomeElement.textContent.trim();
    }

    // Preenche os dados no modal
    const inputId = document.getElementById('clienteId');
    const spanNome = document.getElementById('clienteNomeSaldo');
    
    if (inputId) inputId.value = clienteId;
    if (spanNome) spanNome.textContent = clienteNome;
    
    // Limpa e reseta os campos do formulário
    const inputValor = document.getElementById('valor');
    if (inputValor) inputValor.value = '';
    
    // Garante que o radio button "Adicionar" esteja marcado
    const radioAdicionar = document.querySelector('input[name="tipo"][value="adicionar"]');
    if (radioAdicionar) radioAdicionar.checked = true;
    
    const inputObs = document.getElementById('observacao');
    if (inputObs) inputObs.value = '';
    
    openModal('saldoModal');
}

// Função para abrir modal de exclusão
function abrirModalExcluir(clienteId, clienteNome) {
    const modalExcluir = document.getElementById("modalExcluir");
    const excluirClienteIdInput = document.getElementById("excluirClienteId");
    const clienteNomeElement = document.getElementById("clienteNomeExcluir");

    if (!modalExcluir || !excluirClienteIdInput || !clienteNomeElement) {
        console.error("Elementos do modal de exclusão não encontrados.");
        return;
    }

    excluirClienteIdInput.value = clienteId;
    clienteNomeElement.textContent = clienteNome;
    
    // Resetar confirmação
    document.getElementById('confirmacao').checked = false;
    document.getElementById('btnExcluir').disabled = true;
    
    openModal('modalExcluir');
}

// Função para abrir modal de renovação
function abrirModalRenovar(clienteId, clienteNome) {
    const modalRenovar = document.getElementById("modalRenovar");
    const renovarClienteIdInput = document.getElementById("renovarClienteId");
    const dataVencimentoInput = document.getElementById("dataVencimento");
    const diasRenovacaoInput = document.getElementById("diasRenovacao");
    const clienteNomeElement = document.getElementById("clienteNomeRenovar");

    if (!modalRenovar || !renovarClienteIdInput || !dataVencimentoInput || !diasRenovacaoInput || !clienteNomeElement) {
        console.error("Elementos do modal de renovação não encontrados.");
        return;
    }

    renovarClienteIdInput.value = clienteId;
    clienteNomeElement.textContent = clienteNome;
    dataVencimentoInput.value = "";
    diasRenovacaoInput.value = "";
    
    // Define a data mínima como hoje
    const hoje = new Date().toISOString().split('T')[0];
    dataVencimentoInput.min = hoje;
    
    openModal('modalRenovar');
}

// Função para confirmar renovação
function confirmarRenovacao() {
    const clienteId = document.getElementById("renovarClienteId").value;
    const diasRenovacao = document.getElementById("diasRenovacao").value;
    const dataVencimento = document.getElementById("dataVencimento").value;

    if (!diasRenovacao && !dataVencimento) {
        window.AppUI.alert("Por favor, preencha ao menos um dos campos para renovar.");
        return;
    }

    if (diasRenovacao && dataVencimento) {
        window.AppUI.alert("Por favor, preencha apenas um dos campos (Dias ou Data de Vencimento), não ambos.");
        return;
    }

    // Mostrar loading
    const btnConfirmar = document.querySelector('#modalRenovar .btn-primary');
    const originalText = btnConfirmar.innerHTML;
    btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
    btnConfirmar.disabled = true;

    fetch(`/renovar_cliente/${clienteId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            dias: diasRenovacao || null,
            data_vencimento: dataVencimento || null,
        }),
    })
    .then((response) => {
        if (!response.ok) {
            throw new Error(`Erro na resposta do servidor. Status: ${response.status}`);
        }
        return response.json();
    })
    .then(async (data) => {
        if (data.status === "success") {
            await window.AppUI.alert(`Cliente renovado com sucesso! Novo vencimento: ${data.proximo_vencimento}`, {title:'Renovação concluída'});
            closeModal('modalRenovar');
            location.reload();
        } else {
            window.AppUI.alert(`Erro ao renovar: ${data.message}`);
        }
    })
    .catch((error) => {
        console.error("Erro ao renovar cliente:", error);
        window.AppUI.alert("Ocorreu um erro ao renovar o cliente. Tente novamente.");
    })
    .finally(() => {
        // Restaurar botão
        btnConfirmar.innerHTML = originalText;
        btnConfirmar.disabled = false;
    });
}

// Função para alternar status do cliente
async function toggleClienteStatus(button) {
    const clienteId = button.getAttribute('data-id');
    const isCurrentlyActive = button.getAttribute('data-is-active') === 'True';
    const action = isCurrentlyActive ? 'desativar' : 'ativar';

    if (!(await window.AppUI.confirm(`Tem certeza que deseja ${action} este cliente?`, {title:'Alterar status'}))) {
        return;
    }

    // Mostrar loading
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
    button.disabled = true;

    fetch(`/ativar_desativar_cliente/${clienteId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie("csrftoken"),
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erro na resposta do servidor. Status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        if (data.status === 'success') {
            await window.AppUI.alert(data.message, {title:'Status atualizado'});
            location.reload();
        } else {
            window.AppUI.alert("Erro ao atualizar status: " + data.message);
        }
    })
    .catch(error => {
        console.error("Erro na requisição de status:", error);
        window.AppUI.alert("Ocorreu um erro ao comunicar com o servidor.");
    })
    .finally(() => {
        // Restaurar botão
        button.innerHTML = originalHTML;
        button.disabled = false;
    });
}

// Funções WhatsApp
function enviarMensagemWhatsApp(clienteId) {
    const btn = event.target;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    fetch(`/get_mensagem_cliente/${clienteId}/`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erro HTTP! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (!data.whatsapp) {
            window.AppUI.alert("Número de WhatsApp não encontrado para este cliente.");
            return;
        }

        const mensagem = data.mensagem_texto ? encodeURIComponent(data.mensagem_texto) : "";
        let numero = data.whatsapp.replace(/\D/g, '');
        let url = mensagem ? `https://wa.me/${numero}?text=${mensagem}` : `https://wa.me/${numero}`;

        window.open(url, '_blank');
    })
    .catch(error => {
        console.error("Erro ao obter mensagem do cliente:", error);
        window.AppUI.alert("Erro ao buscar mensagem.");
    })
    .finally(() => {
        // Restaurar botão
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    });
}

function abrirWhatsApp(clienteId) {
    const btn = event.target;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    btn.disabled = true;

    fetch(`/get_mensagem_cliente/${clienteId}/`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erro HTTP! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (!data.whatsapp) {
            window.AppUI.alert("Número de WhatsApp não encontrado para este cliente.");
            return;
        }

        let numero = data.whatsapp.replace(/\D/g, '');
        let url = `https://wa.me/${numero}`;
        window.open(url, '_blank');
    })
    .catch(error => {
        console.error("Erro ao obter número do cliente:", error);
        window.AppUI.alert("Erro ao buscar número.");
    })
    .finally(() => {
        // Restaurar botão
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    });
}

async function gerarLink(clienteId) {
    if (!(await window.AppUI.confirm('Deseja gerar um link de acesso para este cliente?', {title:'Gerar novo link'}))) {
        return;
    }

    const btn = event.target;
    const originalHTML = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';
    btn.disabled = true;

    fetch(`/gerar_novo_link/${clienteId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie("csrftoken"),
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Erro HTTP! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(async data => {
        if (data.status === 'success') {
            await window.AppUI.alert('Link gerado com sucesso!', {title:'Link de acesso'});
            location.reload();
        } else {
            window.AppUI.alert('Erro ao gerar link: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        window.AppUI.alert('Erro ao gerar link');
    })
    .finally(() => {
        // Restaurar botão
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    });
}

// Função utilitária para obter cookie CSRF
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie) {
        const cookies = document.cookie.split(";").map((cookie) => cookie.trim());
        for (const cookie of cookies) {
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ===== INICIALIZAÇÃO =====
document.addEventListener('DOMContentLoaded', function () {

    // Configurar modais para fechar ao clicar no overlay
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(event) {
            if (event.target.classList.contains('modal-overlay')) {
                closeModal(modal.id);
            }
        });
    });

 // Configurar formulário de saldo
    const saldoForm = document.querySelector('#saldoForm');
    if (saldoForm) {
        saldoForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const formData = new FormData(this);
            const url = this.action;

            // --- CORREÇÃO AQUI ---
            // O botão está fora do form, no footer do modal.
            // Precisamos buscá-lo pelo atributo 'form' ou globalmente.
            let btnSubmit = document.querySelector(`button[type="submit"][form="${this.id}"]`);
            
            // Fallback: se não achar fora, tenta achar dentro (caso o HTML mude um dia)
            if (!btnSubmit) {
                btnSubmit = this.querySelector('button[type="submit"]');
            }

            // Verifica se achou o botão antes de tentar alterar o HTML
            let originalText = '';
            if (btnSubmit) {
                originalText = btnSubmit.innerHTML;
                btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';
                btnSubmit.disabled = true;
            }
            // ---------------------

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie("csrftoken"),
                },
            })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Erro na resposta do servidor. Status: ${response.status}`);
                }
                return response.json();
            })
            .then(async (data) => {
                if (data.status === 'success') {
                    await window.AppUI.alert(data.message, {title:'Saldo atualizado'});
                    closeModal('saldoModal');
                    location.reload();
                } else {
                    window.AppUI.alert("Erro ao atualizar saldo: " + data.message);
                }
            })
            .catch((error) => {
                console.error("Erro na requisição:", error);
                window.AppUI.alert("Ocorreu um erro ao alterar o saldo.");
            })
            .finally(() => {
                // Restaurar botão se ele existir
                if (btnSubmit) {
                    btnSubmit.innerHTML = originalText;
                    btnSubmit.disabled = false;
                }
            });
        });
    }

    // Configurar formulário de exclusão
    const formExcluir = document.getElementById("formExcluir");
    if (formExcluir) {
        formExcluir.addEventListener('submit', function(event) {
            event.preventDefault();
            const formData = new FormData(this);
            const clienteId = document.getElementById("excluirClienteId").value;
            const url = `/excluir_cliente/${clienteId}/`;

            // Mostrar loading
            const btnSubmit = this.querySelector('button[type="submit"]');
            const originalText = btnSubmit.innerHTML;
            btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Excluindo...';
            btnSubmit.disabled = true;

            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCookie("csrftoken"),
                },
            })
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Erro na resposta do servidor. Status: ${response.status}`);
                }
                return response.json();
            })
            .then(async (data) => {
                if (data.status === 'success') {
                    await window.AppUI.alert(data.message, {title:'Cliente excluído'});
                    closeModal('modalExcluir');
                    location.reload();
                } else {
                    window.AppUI.alert("Erro ao excluir cliente: " + data.message);
                }
            })
            .catch((error) => {
                console.error("Erro na requisição de exclusão:", error);
                window.AppUI.alert("Ocorreu um erro ao excluir o cliente.");
            })
            .finally(() => {
                // Restaurar botão
                btnSubmit.innerHTML = originalText;
                btnSubmit.disabled = false;
            });
        });
    }

    // Configurar checkbox de confirmação de exclusão
    const confirmacaoCheckbox = document.getElementById('confirmacao');
    if (confirmacaoCheckbox) {
        confirmacaoCheckbox.addEventListener('change', function() {
            document.getElementById('btnExcluir').disabled = !this.checked;
        });
    }

    // Fechar modais com ESC
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            document.querySelectorAll('.modal.show').forEach(modal => {
                closeModal(modal.id);
            });
        }
    });

    // Sincronização entre dias e data de renovação
    const diasRenovacaoInput = document.getElementById('diasRenovacao');
    const dataVencimentoInput = document.getElementById('dataVencimento');
    
    if (diasRenovacaoInput && dataVencimentoInput) {
        diasRenovacaoInput.addEventListener('input', function() {
            if (this.value) {
                dataVencimentoInput.value = '';
            }
        });

        dataVencimentoInput.addEventListener('change', function() {
            if (this.value) {
                diasRenovacaoInput.value = '';
            }
        });
    }
});

function changePageSize(select) {
    const url = new URL(window.location.href);
    url.searchParams.set('page_size', select.value);
    url.searchParams.delete('page'); // Volta para a primeira página
    window.location.href = url.toString();
}