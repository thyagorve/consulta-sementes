// mapa_canvas.js - SISTEMA COMPLETO DE MAPA COM CANVAS
document.addEventListener('DOMContentLoaded', function() {
    // ===== CONFIGURAÇÃO INICIAL =====
    const canvas = document.getElementById('meuCanvas');
    const ctx = canvas.getContext('2d');
    
    // Estado do sistema
    const estado = {
        ferramentaAtiva: 'selecionar',
        elementos: [...ELEMENTOS_INICIAIS],
        elementoSelecionado: null,
        isDesenhando: false,
        inicioX: 0,
        inicioY: 0,
        offsetX: 0,
        offsetY: 0,
        modoRedimensionamento: false,
        pontoRedimensionamento: null,
        imagensCarregadas: {},
        modificado: false
    };
    
    // ===== CARREGAR IMAGEM DE FUNDO =====
    function carregarImagemFundo() {
        // Se houver imagem de fundo no armazém, carrega
        // Implementação usando drawImage()[citation:2][citation:4]
        return new Promise((resolve) => {
            if (ARMAZEM_DATA.imagemUrl) {
                const img = new Image();
                img.crossOrigin = "anonymous";
                img.onload = () => {
                    estado.imagensCarregadas.fundo = img;
                    // Desenha a imagem ajustada ao canvas[citation:4]
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    redesenharCanvas();
                    resolve();
                };
                img.onerror = () => {
                    console.warn('Erro ao carregar imagem de fundo');
                    resolve();
                };
                img.src = ARMAZEM_DATA.imagemUrl;
            } else {
                resolve();
            }
        });
    }
    
    // ===== SISTEMA DE DESENHO =====
    function redesenharCanvas() {
        // Limpa canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Redesenha imagem de fundo se existir
        if (estado.imagensCarregadas.fundo) {
            ctx.globalAlpha = 0.7;
            ctx.drawImage(estado.imagensCarregadas.fundo, 0, 0, canvas.width, canvas.height);
            ctx.globalAlpha = 1.0;
        }
        
        // Desenha todos os elementos
        estado.elementos.forEach((elemento, index) => {
            desenharElemento(elemento);
            
            // Se está selecionado, desenha controles
            if (estado.elementoSelecionado === index) {
                desenharControlesSelecao(elemento);
            }
        });
    }
    
    function desenharElemento(elemento) {
        ctx.save();
        
        switch(elemento.tipo) {
            case 'RETANGULO':
                // Retângulo preenchido
                ctx.fillStyle = elemento.cor_preenchimento;
                ctx.fillRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
                
                // Borda
                ctx.lineWidth = elemento.espessura_borda;
                ctx.strokeStyle = elemento.cor_borda;
                ctx.strokeRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
                
                // Identificador (se houver)
                if (elemento.identificador) {
                    ctx.fillStyle = '#000000';
                    ctx.font = '12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(
                        elemento.identificador,
                        elemento.pos_x + elemento.largura / 2,
                        elemento.pos_y + elemento.altura / 2
                    );
                }
                break;
                
            case 'LINHA':
                ctx.beginPath();
                ctx.lineWidth = elemento.espessura_borda;
                ctx.strokeStyle = elemento.cor_borda;
                
                // Configura tipo de linha
                if (elemento.linha_tipo === 'tracejada') {
                    ctx.setLineDash([5, 5]);
                } else if (elemento.linha_tipo === 'pontilhada') {
                    ctx.setLineDash([2, 2]);
                }
                
                // Desenha linha horizontal ou vertical
                ctx.moveTo(elemento.pos_x, elemento.pos_y);
                if (elemento.largura > elemento.altura) {
                    // Linha predominante horizontal
                    ctx.lineTo(elemento.pos_x + elemento.largura, elemento.pos_y);
                } else {
                    // Linha predominante vertical
                    ctx.lineTo(elemento.pos_x, elemento.pos_y + elemento.altura);
                }
                ctx.stroke();
                ctx.setLineDash([]); // Reseta
                break;
                
            case 'TEXTO':
                ctx.font = `${elemento.texto_negrito ? 'bold ' : ''}${elemento.texto_italico ? 'italic ' : ''}${elemento.fonte_tamanho}px ${elemento.fonte_nome}`;
                ctx.fillStyle = elemento.cor_preenchimento;
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                
                // Texto na direção especificada
                if (elemento.texto_direcao === 'vertical') {
                    // Texto vertical - caractere por caractere
                    const chars = elemento.conteudo_texto.split('');
                    chars.forEach((char, i) => {
                        ctx.save();
                        ctx.translate(
                            elemento.pos_x + 10,
                            elemento.pos_y + (i * elemento.fonte_tamanho)
                        );
                        ctx.rotate(Math.PI / 2);
                        ctx.fillText(char, 0, 0);
                        ctx.restore();
                    });
                } else {
                    // Texto horizontal
                    ctx.fillText(
                        elemento.conteudo_texto,
                        elemento.pos_x,
                        elemento.pos_y
                    );
                }
                break;
        }
        
        ctx.restore();
    }
    
    function desenharControlesSelecao(elemento) {
        // Desenha retângulo de seleção
        ctx.strokeStyle = '#4f46e5';
        ctx.lineWidth = 2;
        ctx.setLineDash([3, 3]);
        ctx.strokeRect(
            elemento.pos_x - 5,
            elemento.pos_y - 5,
            elemento.largura + 10,
            elemento.altura + 10
        );
        ctx.setLineDash([]);
        
        // Desenha pontos de redimensionamento
        const pontos = [
            {x: elemento.pos_x, y: elemento.pos_y, tipo: 'nw'}, // Canto NW
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y, tipo: 'ne'}, // Canto NE
            {x: elemento.pos_x, y: elemento.pos_y + elemento.altura, tipo: 'sw'}, // Canto SW
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y + elemento.altura, tipo: 'se'}, // Canto SE
            {x: elemento.pos_x + elemento.largura / 2, y: elemento.pos_y, tipo: 'n'}, // Centro superior
            {x: elemento.pos_x, y: elemento.pos_y + elemento.altura / 2, tipo: 'w'}, // Centro esquerda
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y + elemento.altura / 2, tipo: 'e'}, // Centro direita
            {x: elemento.pos_x + elemento.largura / 2, y: elemento.pos_y + elemento.altura, tipo: 's'} // Centro inferior
        ];
        
        pontos.forEach(ponto => {
            ctx.fillStyle = '#ffffff';
            ctx.strokeStyle = '#4f46e5';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.arc(ponto.x, ponto.y, 6, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
        });
    }
    
    // ===== SISTEMA DE INTERAÇÃO =====
    canvas.addEventListener('mousedown', iniciarInteracao);
    canvas.addEventListener('mousemove', moverInteracao);
    canvas.addEventListener('mouseup', finalizarInteracao);
    canvas.addEventListener('mouseleave', finalizarInteracao);
    
    function iniciarInteracao(e) {
        if (!ARMAZEM_DATA.isAdmin) return; // Somente admin pode interagir
        
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        estado.inicioX = x;
        estado.inicioY = y;
        
        // Verifica se clicou em elemento existente
        const elementoClicado = encontrarElementoNaPosicao(x, y);
        
        if (elementoClicado !== -1) {
            // Seleciona elemento existente
            estado.elementoSelecionado = elementoClicado;
            const elemento = estado.elementos[elementoClicado];
            
            // Verifica se clicou em ponto de redimensionamento
            const pontoRedim = encontrarPontoRedimensionamento(x, y, elemento);
            if (pontoRedim) {
                estado.modoRedimensionamento = true;
                estado.pontoRedimensionamento = pontoRedim;
            } else {
                // Modo arrastar
                estado.modoRedimensionamento = false;
                estado.offsetX = x - elemento.pos_x;
                estado.offsetY = y - elemento.pos_y;
            }
            
            estado.isDesenhando = true;
        } else {
            // Inicia criação de novo elemento
            estado.elementoSelecionado = null;
            estado.isDesenhando = true;
            
            // Cria novo elemento baseado na ferramenta
            let novoElemento;
            switch(estado.ferramentaAtiva) {
                case 'retangulo':
                    novoElemento = {
                        tipo: 'RETANGULO',
                        pos_x: x,
                        pos_y: y,
                        largura: 0,
                        altura: 0,
                        cor_preenchimento: document.getElementById('corPreenchimento').value,
                        cor_borda: document.getElementById('corBorda').value,
                        espessura_borda: parseInt(document.getElementById('espessuraBorda').value),
                        identificador: ''
                    };
                    break;
                    
                case 'linha':
                    novoElemento = {
                        tipo: 'LINHA',
                        pos_x: x,
                        pos_y: y,
                        largura: 0,
                        altura: 0,
                        cor_borda: document.getElementById('corBorda').value,
                        espessura_borda: parseInt(document.getElementById('espessuraBorda').value),
                        linha_tipo: 'solida'
                    };
                    break;
                    
                case 'texto':
                    novoElemento = {
                        tipo: 'TEXTO',
                        pos_x: x,
                        pos_y: y,
                        largura: 100,
                        altura: 30,
                        cor_preenchimento: document.getElementById('corPreenchimento').value,
                        conteudo_texto: 'Novo Texto',
                        fonte_nome: document.getElementById('selectFonte').value,
                        fonte_tamanho: 14,
                        texto_negrito: false,
                        texto_italico: false,
                        texto_direcao: 'horizontal'
                    };
                    // Abre modal para texto
                    abrirModalTexto(novoElemento);
                    break;
                    
                case 'pincel':
                    // Modo pintura - altera cor do elemento clicado
                    const elementoParaPintar = encontrarElementoNaPosicao(x, y, true);
                    if (elementoParaPintar !== -1) {
                        estado.elementos[elementoParaPintar].cor_preenchimento = 
                            document.getElementById('corPreenchimento').value;
                        estado.modificado = true;
                        redesenharCanvas();
                    }
                    return;
                    
                case 'excluir':
                    // Modo exclusão
                    if (elementoClicado !== -1) {
                        const elemento = estado.elementos[elementoClicado];
                        if (confirmarExclusaoElemento(elemento)) {
                            estado.elementos.splice(elementoClicado, 1);
                            estado.elementoSelecionado = null;
                            estado.modificado = true;
                            redesenharCanvas();
                        }
                    }
                    return;
            }
            
            if (novoElemento) {
                estado.elementos.push(novoElemento);
                estado.elementoSelecionado = estado.elementos.length - 1;
            }
        }
        
        redesenharCanvas();
    }
    
    function moverInteracao(e) {
        if (!estado.isDesenhando || !ARMAZEM_DATA.isAdmin) return;
        
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (estado.elementoSelecionado !== null) {
            const elemento = estado.elementos[estado.elementoSelecionado];
            
            if (estado.modoRedimensionamento && estado.pontoRedimensionamento) {
                // Redimensionamento
                redimensionarElemento(elemento, estado.pontoRedimensionamento, x, y);
            } else if (elemento.tipo === 'LINHA') {
                // Para linhas, ajusta largura/altura
                elemento.largura = x - elemento.pos_x;
                elemento.altura = y - elemento.pos_y;
            } else {
                // Arrastar ou redimensionar criação
                if (elemento.largura === 0 && elemento.altura === 0) {
                    // Ainda criando - redimensiona
                    elemento.largura = x - elemento.pos_x;
                    elemento.altura = y - elemento.pos_y;
                } else {
                    // Arrastar elemento existente
                    elemento.pos_x = x - estado.offsetX;
                    elemento.pos_y = y - estado.offsetY;
                    
                    // Limita ao canvas
                    elemento.pos_x = Math.max(0, Math.min(elemento.pos_x, canvas.width - elemento.largura));
                    elemento.pos_y = Math.max(0, Math.min(elemento.pos_y, canvas.height - elemento.altura));
                }
            }
            
            estado.modificado = true;
            redesenharCanvas();
        }
    }
    
    function finalizarInteracao() {
        if (!estado.isDesenhando) return;
        
        estado.isDesenhando = false;
        estado.modoRedimensionamento = false;
        estado.pontoRedimensionamento = null;
        
        // Se criou um novo elemento, abre modal para identificação
        if (estado.elementoSelecionado !== null) {
            const elemento = estado.elementos[estado.elementoSelecionado];
            
            // Elementos muito pequenos são removidos
            if (elemento.largura < 10 && elemento.altura < 10 && elemento.tipo !== 'TEXTO') {
                estado.elementos.splice(estado.elementoSelecionado, 1);
                estado.elementoSelecionado = null;
                redesenharCanvas();
                return;
            }
            
            // Para retângulos, abre modal de identificação
            if (elemento.tipo === 'RETANGULO' && !elemento.identificador) {
                abrirModalIdentificacao(elemento);
            }
        }
    }
    
    // ===== FUNÇÕES AUXILIARES =====
    function encontrarElementoNaPosicao(x, y, incluirTexto = false) {
        // Percorre elementos de trás para frente (último desenhado primeiro)
        for (let i = estado.elementos.length - 1; i >= 0; i--) {
            const elemento = estado.elementos[i];
            
            if (elemento.tipo === 'TEXTO' && !incluirTexto) continue;
            
            // Verifica colisão baseada no tipo
            let colidiu = false;
            switch(elemento.tipo) {
                case 'RETANGULO':
                    colidiu = (
                        x >= elemento.pos_x &&
                        x <= elemento.pos_x + elemento.largura &&
                        y >= elemento.pos_y &&
                        y <= elemento.pos_y + elemento.altura
                    );
                    break;
                    
                case 'LINHA':
                    // Verifica proximidade da linha
                    const distancia = distanciaParaLinha(x, y, elemento);
                    colidiu = distancia < 10; // 10px de tolerância
                    break;
                    
                case 'TEXTO':
                    // Aproximação para texto
                    colidiu = (
                        x >= elemento.pos_x - 10 &&
                        x <= elemento.pos_x + elemento.largura + 10 &&
                        y >= elemento.pos_y - 10 &&
                        y <= elemento.pos_y + elemento.altura + 10
                    );
                    break;
            }
            
            if (colidiu) return i;
        }
        return -1;
    }
    
    function encontrarPontoRedimensionamento(x, y, elemento) {
        const pontos = [
            {x: elemento.pos_x, y: elemento.pos_y, tipo: 'nw'},
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y, tipo: 'ne'},
            {x: elemento.pos_x, y: elemento.pos_y + elemento.altura, tipo: 'sw'},
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y + elemento.altura, tipo: 'se'}
        ];
        
        for (const ponto of pontos) {
            const distancia = Math.sqrt(
                Math.pow(x - ponto.x, 2) + Math.pow(y - ponto.y, 2)
            );
            if (distancia <= 8) {
                return ponto.tipo;
            }
        }
        return null;
    }
    
    function redimensionarElemento(elemento, ponto, mouseX, mouseY) {
        switch(ponto) {
            case 'nw': // Canto superior esquerdo
                elemento.largura += elemento.pos_x - mouseX;
                elemento.altura += elemento.pos_y - mouseY;
                elemento.pos_x = mouseX;
                elemento.pos_y = mouseY;
                break;
                
            case 'ne': // Canto superior direito
                elemento.largura = mouseX - elemento.pos_x;
                elemento.altura += elemento.pos_y - mouseY;
                elemento.pos_y = mouseY;
                break;
                
            case 'sw': // Canto inferior esquerdo
                elemento.largura += elemento.pos_x - mouseX;
                elemento.altura = mouseY - elemento.pos_y;
                elemento.pos_x = mouseX;
                break;
                
            case 'se': // Canto inferior direito
                elemento.largura = mouseX - elemento.pos_x;
                elemento.altura = mouseY - elemento.pos_y;
                break;
        }
        
        // Limites mínimos
        elemento.largura = Math.max(10, elemento.largura);
        elemento.altura = Math.max(10, elemento.altura);
        
        // Mantém dentro do canvas
        if (elemento.pos_x < 0) {
            elemento.largura += elemento.pos_x;
            elemento.pos_x = 0;
        }
        if (elemento.pos_y < 0) {
            elemento.altura += elemento.pos_y;
            elemento.pos_y = 0;
        }
        if (elemento.pos_x + elemento.largura > canvas.width) {
            elemento.largura = canvas.width - elemento.pos_x;
        }
        if (elemento.pos_y + elemento.altura > canvas.height) {
            elemento.altura = canvas.height - elemento.pos_y;
        }
    }
    
    // ===== MODAIS E INTERFACE =====
    function abrirModalIdentificacao(elemento) {
        const modal = new bootstrap.Modal(document.getElementById('modalIdentificarElemento'));
        const inputIdentificador = document.getElementById('inputIdentificador');
        const selectTipo = document.getElementById('selectTipoElemento');
        
        // Configura valores iniciais
        inputIdentificador.value = elemento.identificador || '';
        selectTipo.value = elemento.tipo === 'RETANGULO' ? 'endereco' : 'outro';
        
        // Configura botão de confirmação
        document.getElementById('btnConfirmarIdentificador').onclick = function() {
            elemento.identificador = inputIdentificador.value.trim();
            
            // Para endereços, valida formato
            if (selectTipo.value === 'endereco') {
                if (!/^[A-Z][0-9]{3}$/i.test(elemento.identificador)) {
                    alert('Formato de endereço recomendado: Letra seguida de 3 números (ex: A001, B203)');
                }
            }
            
            estado.modificado = true;
            modal.hide();
            redesenharCanvas();
        };
        
        modal.show();
    }
    
    function abrirModalTexto(elemento) {
        // Implementação similar para edição de texto
        // Permite configurar fonte, tamanho, direção, etc.
    }
    
    function confirmarExclusaoElemento(elemento) {
        // REGRA CRÍTICA: Não permite excluir endereços com estoque
        if (elemento.identificador && elemento.tipo === 'RETANGULO') {
            // Verifica no servidor se há estoque
            return fetch(`/api/verificar-estoque/${encodeURIComponent(elemento.identificador)}/`)
                .then(response => response.json())
                .then(data => {
                    if (data.tem_estoque) {
                        alert(`❌ Não é possível excluir o endereço "${elemento.identificador}"!\nExiste estoque cadastrado neste local.`);
                        return false;
                    }
                    return confirm(`Excluir permanentemente "${elemento.identificador}"?`);
                })
                .catch(() => {
                    // Fallback: pergunta normalmente
                    return confirm(`Excluir "${elemento.identificador}"?`);
                });
        }
        
        return confirm(`Excluir elemento "${elemento.identificador || 'sem identificação'}"?`);
    }
    
    // ===== CONTROLES DA INTERFACE =====
    // Configura botões de ferramentas
    document.querySelectorAll('[data-ferramenta]').forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove classe ativa de todos
            document.querySelectorAll('[data-ferramenta]').forEach(b => {
                b.classList.remove('ativo');
            });
            
            // Ativa este botão
            this.classList.add('ativo');
            estado.ferramentaAtiva = this.dataset.ferramenta;
            
            // Mostra/oculta painéis específicos
            if (estado.ferramentaAtiva === 'texto') {
                document.getElementById('painelTexto').style.display = 'block';
            } else {
                document.getElementById('painelTexto').style.display = 'none';
            }
            
            // Altera cursor
            const cursores = {
                'selecionar': 'default',
                'retangulo': 'crosshair',
                'linha': 'crosshair',
                'texto': 'text',
                'pincel': 'url("pincel.cur"), crosshair',
                'excluir': 'not-allowed'
            };
            canvas.style.cursor = cursores[estado.ferramentaAtiva] || 'default';
        });
    });
    
    // Botão salvar
    document.getElementById('btnSalvarCanvas').addEventListener('click', salvarLayout);
    
    async function salvarLayout() {
        if (!estado.modificado) {
            mostrarMensagem('⚠️ Nenhuma alteração para salvar', 'warning');
            return;
        }
        
        // Prepara dados
        const dados = {
            armazem_id: ARMAZEM_DATA.id,
            elementos: estado.elementos.map((elemento, index) => ({
                ...elemento,
                ordem_z: index + 1
            }))
        };
        
        try {
            const response = await fetch('{% url "sapp:salvar_elemento_mapa" %}', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify(dados)
            });
            
            const result = await response.json();
            
            if (result.success) {
                estado.modificado = false;
                mostrarMensagem('✅ Layout salvo com sucesso!', 'success');
                
                // Atualiza IDs dos elementos
                if (result.elementos_salvos) {
                    result.elementos_salvos.forEach((savedElem, index) => {
                        if (estado.elementos[index]) {
                            estado.elementos[index].id = savedElem.id;
                        }
                    });
                }
            } else {
                mostrarMensagem(`❌ Erro ao salvar: ${result.error}`, 'danger');
            }
        } catch (error) {
            mostrarMensagem(`❌ Erro de conexão: ${error.message}`, 'danger');
        }
    }
    
    // ===== INICIALIZAÇÃO =====
    function inicializar() {
        // Configura ferramenta inicial
        document.querySelector('[data-ferramenta="selecionar"]').classList.add('ativo');
        
        // Carrega imagem de fundo
        carregarImagemFundo().then(() => {
            redesenharCanvas();
        });
        
        // Configura seletor de armazém
        document.getElementById('selectArmazemNav').addEventListener('change', function() {
            window.location.href = `/mapa-armazem/${this.value}/`;
        });
        
        // Configura controles de propriedades
        document.getElementById('corPreenchimento').addEventListener('change', function() {
            if (estado.elementoSelecionado !== null) {
                estado.elementos[estado.elementoSelecionado].cor_preenchimento = this.value;
                estado.modificado = true;
                redesenharCanvas();
            }
        });
        
        document.getElementById('corBorda').addEventListener('change', function() {
            if (estado.elementoSelecionado !== null) {
                estado.elementos[estado.elementoSelecionado].cor_borda = this.value;
                estado.modificado = true;
                redesenharCanvas();
            }
        });
        
        document.getElementById('espessuraBorda').addEventListener('input', function() {
            if (estado.elementoSelecionado !== null) {
                estado.elementos[estado.elementoSelecionado].espessura_borda = parseInt(this.value);
                estado.modificado = true;
                redesenharCanvas();
            }
        });
        
        // Avisa antes de sair se houver modificações não salvas
        window.addEventListener('beforeunload', function(e) {
            if (estado.modificado) {
                e.preventDefault();
                e.returnValue = 'Você tem alterações não salvas no mapa. Deseja realmente sair?';
            }
        });
    }
    
    // Funções auxiliares
    function distanciaParaLinha(x, y, linha) {
        // Calcula distância do ponto para a linha
        const x1 = linha.pos_x;
        const y1 = linha.pos_y;
        const x2 = linha.pos_x + linha.largura;
        const y2 = linha.pos_y + linha.altura;
        
        const A = x - x1;
        const B = y - y1;
        const C = x2 - x1;
        const D = y2 - y1;
        
        const dot = A * C + B * D;
        const lenSq = C * C + D * D;
        let param = -1;
        
        if (lenSq !== 0) {
            param = dot / lenSq;
        }
        
        let xx, yy;
        
        if (param < 0) {
            xx = x1;
            yy = y1;
        } else if (param > 1) {
            xx = x2;
            yy = y2;
        } else {
            xx = x1 + param * C;
            yy = y1 + param * D;
        }
        
        const dx = x - xx;
        const dy = y - yy;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    function getCSRFToken() {
        const name = 'csrftoken';
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
    }
    
    function mostrarMensagem(texto, tipo = 'info') {
        // Implementação do sistema de mensagens
        const mensagem = document.createElement('div');
        mensagem.className = `alert alert-${tipo} alert-dismissible fade show`;
        mensagem.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
        `;
        mensagem.innerHTML = `
            ${texto}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(mensagem);
        
        setTimeout(() => {
            if (mensagem.parentNode) mensagem.remove();
        }, 5000);
    }
    
    // Inicia o sistema
    inicializar();
    console.log('✅ Sistema de Mapa Canvas inicializado!');
});