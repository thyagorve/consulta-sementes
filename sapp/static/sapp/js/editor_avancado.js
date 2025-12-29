// ==================== ESTADO GLOBAL ====================
const estado = {
    ferramenta: 'mover',
    elementoSelecionado: null,
    elementos: [],
    desenhando: false,
    arrastando: false,
    redimensionando: false,
    inicioX: 0,
    inicioY: 0,
    offsetX: 0,
    offsetY: 0,
    pontoRedim: null,
    modificado: false,
    zoom: 1.0,
    showGrid: true,
    showInfo: true
};

// ==================== ELEMENTOS DOM ====================
let canvas, ctx, pontosControle;

// ==================== INICIALIZAÇÃO ====================
function inicializarEditor() {
    console.log("🔄 Inicializando editor...");
    
    // Configura elementos DOM
    canvas = document.getElementById('meuCanvas');
    ctx = canvas.getContext('2d');
    pontosControle = document.getElementById('pontosControle');
    
    if (!canvas) {
        console.error("❌ Canvas não encontrado!");
        return;
    }
    
    console.log(`📐 Tamanho do canvas: ${canvas.width}x${canvas.height}`);
    
    // Carrega elementos iniciais
    console.log("📦 Elementos carregados:", elementos);
    estado.elementos = elementos || [];
    
    // Configura eventos
    configurarEventos();
    
    // Atualiza interface
    atualizarInterface();
    atualizarEstatisticas();
    
    // Redesenha canvas
    redesenharTudo();
    
    console.log('✅ Editor Avançado inicializado!');
    console.log(`📊 ${estado.elementos.length} elementos carregados`);
}

// ==================== CONFIGURAÇÃO DE EVENTOS ====================
function configurarEventos() {
    // EVENTOS DO MOUSE NO CANVAS
    canvas.addEventListener('mousedown', iniciarInteracao);
    canvas.addEventListener('mousemove', moverInteracao);
    canvas.addEventListener('mouseup', finalizarInteracao);
    canvas.addEventListener('mouseleave', finalizarInteracao);
    canvas.addEventListener('wheel', eventoZoom);
    canvas.addEventListener('dblclick', eventoDuploClique);
    
    // EVENTOS DE TECLADO
    document.addEventListener('keydown', tecladoPressionado);
    
    // FERRAMENTAS (apenas para admin)
    if (CONFIG.usuario.is_admin) {
        document.querySelectorAll('[data-ferramenta]').forEach(btn => {
            btn.addEventListener('click', function() {
                selecionarFerramenta(this.dataset.ferramenta);
            });
        });
        
        // PROPRIEDADES
        document.getElementById('inputIdentificador').addEventListener('change', atualizarPropriedade);
        document.getElementById('inputQuantidade').addEventListener('change', atualizarPropriedade);
        document.getElementById('corPreenchimento').addEventListener('change', atualizarPropriedade);
        document.getElementById('corBorda').addEventListener('change', atualizarPropriedade);
        document.getElementById('espessuraBorda').addEventListener('input', atualizarPropriedade);
        document.getElementById('opacidade').addEventListener('input', atualizarPropriedade);
        document.getElementById('inputRotacao').addEventListener('input', atualizarPropriedade);
        
        // PROPRIEDADES DE TEXTO
        document.getElementById('inputConteudoTexto').addEventListener('input', atualizarPropriedade);
        document.getElementById('selectFonte').addEventListener('change', atualizarPropriedade);
        document.getElementById('tamanhoFonte').addEventListener('change', atualizarPropriedade);
        
        // POSIÇÃO E DIMENSÕES
        document.getElementById('inputPosX').addEventListener('change', atualizarPosicao);
        document.getElementById('inputPosY').addEventListener('change', atualizarPosicao);
        document.getElementById('inputLargura').addEventListener('change', atualizarDimensoes);
        document.getElementById('inputAltura').addEventListener('change', atualizarDimensoes);
        document.getElementById('btnAplicarDimensoes').addEventListener('click', aplicarDimensoesManualmente);
        
        // ORDEM Z (CAMADAS)
        document.getElementById('btnTrazerFrente').addEventListener('click', () => alterarOrdemZ('frente'));
        document.getElementById('btnEnviarAtras').addEventListener('click', () => alterarOrdemZ('atras'));
        
        // SALVAR
        document.getElementById('btnSalvar').addEventListener('click', salvarLayout);
    }
    
    // CONTROLES GERAIS
    document.getElementById('btnCarregar').addEventListener('click', () => location.reload());
    document.getElementById('btnZoomIn').addEventListener('click', () => ajustarZoom(0.1));
    document.getElementById('btnZoomOut').addEventListener('click', () => ajustarZoom(-0.1));
    document.getElementById('btnZoomReset').addEventListener('click', () => resetarZoom());
    document.getElementById('btnToggleGrid').addEventListener('click', toggleGrid);
    
    // IMPEDIR SAÍDA SEM SALVAR
    window.addEventListener('beforeunload', function(e) {
        if (estado.modificado && CONFIG.usuario.is_admin) {
            e.preventDefault();
            e.returnValue = 'Você tem alterações não salvas. Tem certeza que deseja sair?';
        }
    });
}

// ==================== FUNÇÕES DE DESENHO ====================
function redesenharTudo() {
    // Limpa canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Aplica transformação de zoom
    ctx.save();
    ctx.scale(estado.zoom, estado.zoom);
    
    // Desenha grid se ativo
    if (estado.showGrid) {
        desenharGrid();
    }
    
    // Desenha elementos (ordenados por ordem_z)
    const elementosOrdenados = [...estado.elementos].sort((a, b) => a.ordem_z - b.ordem_z);
    elementosOrdenados.forEach((elemento, index) => {
        const isSelecionado = estado.elementoSelecionado === estado.elementos.indexOf(elemento);
        desenharElemento(elemento, isSelecionado);
    });
    
    ctx.restore();
    
    // Desenha pontos de controle se selecionado
    if (estado.elementoSelecionado !== null && CONFIG.usuario.is_admin) {
        desenharPontosControle(estado.elementos[estado.elementoSelecionado]);
    }
}

function desenharGrid() {
    const gridSize = 20 * estado.zoom;
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.lineWidth = 0.5;
    
    // Linhas verticais
    for (let x = 0; x <= canvas.width / estado.zoom; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height / estado.zoom);
        ctx.stroke();
    }
    
    // Linhas horizontais
    for (let y = 0; y <= canvas.height / estado.zoom; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width / estado.zoom, y);
        ctx.stroke();
    }
}

function desenharElemento(elemento, selecionado = false) {
    ctx.save();
    
    // Aplica rotação se existir
    if (elemento.rotacao) {
        const centerX = elemento.pos_x + elemento.largura / 2;
        const centerY = elemento.pos_y + elemento.altura / 2;
        ctx.translate(centerX, centerY);
        ctx.rotate(elemento.rotacao * Math.PI / 180);
        ctx.translate(-centerX, -centerY);
    }
    
    switch(elemento.tipo) {
        case 'RETANGULO':
            // Preenchimento com opacidade
            ctx.globalAlpha = (elemento.opacidade || 80) / 100;
            ctx.fillStyle = elemento.cor_preenchimento || '#4f46e5';
            ctx.fillRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
            
            // Borda
            ctx.globalAlpha = 1;
            ctx.lineWidth = elemento.espessura_borda || 2;
            ctx.strokeStyle = elemento.cor_borda || '#000000';
            ctx.strokeRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
            
            // Texto do identificador e quantidade
            ctx.fillStyle = '#ffffff';
            ctx.font = `bold ${Math.max(10, Math.min(14, elemento.largura / 10))}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            const maxLargura = elemento.largura - 10;
            const linhas = [];
            
            // Identificador/Lote
            if (elemento.identificador) {
                linhas.push(elemento.identificador);
            }
            
            // Quantidade
            if (elemento.quantidade !== undefined) {
                linhas.push(`${elemento.quantidade} unidades`);
            }
            
            // Desenha linhas centralizadas
            const alturaLinha = 16;
            const inicioY = elemento.pos_y + elemento.altura / 2 - ((linhas.length - 1) * alturaLinha) / 2;
            
            linhas.forEach((texto, index) => {
                ctx.fillText(
                    texto,
                    elemento.pos_x + elemento.largura / 2,
                    inicioY + (index * alturaLinha),
                    maxLargura
                );
            });
            
            // Barra de progresso baseada na quantidade (visual)
            if (elemento.quantidade > 0) {
                const barraAltura = 4;
                const barraY = elemento.pos_y + elemento.altura - barraAltura - 2;
                const barraLargura = Math.max(20, elemento.largura * 0.8);
                
                // Fundo da barra
                ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                ctx.fillRect(
                    elemento.pos_x + (elemento.largura - barraLargura) / 2, 
                    barraY, 
                    barraLargura, 
                    barraAltura
                );
                
                // Barra de preenchimento (proporcional à quantidade)
                const percentual = Math.min(1, elemento.quantidade / 100); // Assume 100 como máximo visual
                ctx.fillStyle = elemento.quantidade < 50 ? '#22c55e' : 
                                elemento.quantidade < 80 ? '#f59e0b' : '#ef4444';
                ctx.fillRect(
                    elemento.pos_x + (elemento.largura - barraLargura) / 2, 
                    barraY, 
                    barraLargura * percentual, 
                    barraAltura
                );
            }
            break;
            
        case 'TEXTO':
            ctx.font = `${elemento.texto_negrito ? 'bold' : ''} ${elemento.texto_italico ? 'italic' : ''} 
                       ${elemento.fonte_tamanho || 14}px ${elemento.fonte_nome || 'Arial'}`;
            ctx.fillStyle = elemento.cor_preenchimento || '#000000';
            ctx.textAlign = elemento.texto_alinhamento || 'left';
            ctx.textBaseline = 'top';
            
            if (elemento.texto_direcao === 'vertical') {
                ctx.save();
                ctx.translate(elemento.pos_x, elemento.pos_y);
                ctx.rotate(-Math.PI / 2);
                ctx.fillText(elemento.conteudo_texto || 'Texto', 0, 0);
                ctx.restore();
            } else {
                ctx.fillText(
                    elemento.conteudo_texto || 'Texto',
                    elemento.pos_x,
                    elemento.pos_y
                );
            }
            break;
    }
    
    // Borda de seleção (apenas para admin)
    if (selecionado && CONFIG.usuario.is_admin) {
        ctx.strokeStyle = '#4f46e5';
        ctx.lineWidth = 2;
        ctx.setLineDash([3, 3]);
        ctx.strokeRect(
            elemento.pos_x - 4,
            elemento.pos_y - 4,
            elemento.largura + 8,
            elemento.altura + 8
        );
        ctx.setLineDash([]);
    }
    
    ctx.restore();
}

function desenharPontosControle(elemento) {
    pontosControle.innerHTML = '';
    
    if (!elemento || elemento.tipo === 'TEXTO') return;
    
    const pontos = [
        {x: elemento.pos_x, y: elemento.pos_y, tipo: 'nw', cursor: 'nwse-resize'},
        {x: elemento.pos_x + elemento.largura, y: elemento.pos_y, tipo: 'ne', cursor: 'nesw-resize'},
        {x: elemento.pos_x, y: elemento.pos_y + elemento.altura, tipo: 'sw', cursor: 'nesw-resize'},
        {x: elemento.pos_x + elemento.largura, y: elemento.pos_y + elemento.altura, tipo: 'se', cursor: 'nwse-resize'},
    ];
    
    pontos.forEach(ponto => {
        const div = document.createElement('div');
        div.className = 'ponto-controle';
        div.style.left = `${ponto.x * estado.zoom}px`;
        div.style.top = `${ponto.y * estado.zoom}px`;
        div.style.cursor = ponto.cursor;
        div.dataset.tipo = ponto.tipo;
        
        div.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            estado.redimensionando = true;
            estado.pontoRedim = ponto.tipo;
        });
        
        pontosControle.appendChild(div);
    });
}

// ==================== INTERAÇÃO COM MOUSE ====================
function iniciarInteracao(e) {
    if (!CONFIG.usuario.is_admin && estado.ferramenta !== 'zoom') {
        return; // Apenas visualização para não-admins
    }
    
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / estado.zoom;
    const y = (e.clientY - rect.top) / estado.zoom;
    
    estado.inicioX = x;
    estado.inicioY = y;
    
    if (estado.ferramenta === 'zoom') {
        // Modo zoom - centraliza no ponto clicado
        estado.zoom = Math.min(3, Math.max(0.5, estado.zoom + 0.2));
        atualizarInfoZoom();
        redesenharTudo();
        return;
    }
    
    // Verifica se clicou em elemento existente
    const elementoIdx = encontrarElementoNaPosicao(x, y);
    
    if (elementoIdx !== -1) {
        estado.elementoSelecionado = elementoIdx;
        const elemento = estado.elementos[elementoIdx];
        
        estado.offsetX = x - elemento.pos_x;
        estado.offsetY = y - elemento.pos_y;
        
        if (estado.ferramenta === 'excluir') {
            if (confirm(`Excluir "${elemento.identificador || 'Lote'}"?`)) {
                estado.elementos.splice(elementoIdx, 1);
                estado.elementoSelecionado = null;
                estado.modificado = true;
                atualizarInterface();
                atualizarEstatisticas();
                redesenharTudo();
            }
            return;
        } else if (estado.ferramenta === 'mover') {
            estado.arrastando = true;
            canvas.style.cursor = 'grabbing';
        } else if (estado.ferramenta === 'redimensionar') {
            estado.redimensionando = true;
        }
        
        atualizarInterface();
    } else {
        // Cria novo elemento (apenas admin)
        if (CONFIG.usuario.is_admin && ['retangulo', 'texto'].includes(estado.ferramenta)) {
            estado.elementoSelecionado = null;
            estado.desenhando = true;
            
            let novoElemento;
            
            if (estado.ferramenta === 'retangulo') {
                novoElemento = {
                    id: null,
                    tipo: 'RETANGULO',
                    pos_x: x,
                    pos_y: y,
                    largura: 0,
                    altura: 0,
                    cor_preenchimento: '#4f46e5',
                    cor_borda: '#000000',
                    espessura_borda: 2,
                    opacidade: 80,
                    rotacao: 0,
                    identificador: `LOTE-${estado.elementos.filter(e => e.tipo === 'RETANGULO').length + 1}`,
                    quantidade: 0,
                    ordem_z: estado.elementos.length + 1,
                    data_criacao: new Date().toISOString().split('T')[0]
                };
            } else if (estado.ferramenta === 'texto') {
                novoElemento = {
                    id: null,
                    tipo: 'TEXTO',
                    pos_x: x,
                    pos_y: y,
                    largura: 100,
                    altura: 30,
                    cor_preenchimento: '#000000',
                    conteudo_texto: 'Novo Texto',
                    fonte_nome: 'Arial',
                    fonte_tamanho: 14,
                    texto_negrito: false,
                    texto_italico: false,
                    texto_sublinhado: false,
                    texto_direcao: 'horizontal',
                    texto_alinhamento: 'left',
                    identificador: 'Texto',
                    ordem_z: estado.elementos.length + 1
                };
            }
            
            estado.elementos.push(novoElemento);
            estado.elementoSelecionado = estado.elementos.length - 1;
            estado.modificado = true;
            
            atualizarInterface();
            atualizarEstatisticas();
        } else {
            estado.elementoSelecionado = null;
            atualizarInterface();
        }
    }
    
    redesenharTudo();
}

function moverInteracao(e) {
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / estado.zoom;
    const y = (e.clientY - rect.top) / estado.zoom;
    
    // Atualiza informações de posição
    document.getElementById('infoPosicao').textContent = `${Math.round(x)}, ${Math.round(y)}`;
    
    if (estado.arrastando && estado.elementoSelecionado !== null && CONFIG.usuario.is_admin) {
        const elemento = estado.elementos[estado.elementoSelecionado];
        elemento.pos_x = x - estado.offsetX;
        elemento.pos_y = y - estado.offsetY;
        
        document.getElementById('inputPosX').value = Math.round(elemento.pos_x);
        document.getElementById('inputPosY').value = Math.round(elemento.pos_y);
        
        estado.modificado = true;
        redesenharTudo();
    } else if (estado.redimensionando && estado.elementoSelecionado !== null && CONFIG.usuario.is_admin) {
        const elemento = estado.elementos[estado.elementoSelecionado];
        redimensionarElemento(elemento, estado.pontoRedim, x, y);
        
        estado.modificado = true;
        redesenharTudo();
    } else if (estado.desenhando && estado.elementoSelecionado !== null && CONFIG.usuario.is_admin) {
        const elemento = estado.elementos[estado.elementoSelecionado];
        
        if (elemento.tipo === 'RETANGULO') {
            elemento.largura = x - elemento.pos_x;
            elemento.altura = y - elemento.pos_y;
            
            // Mantém proporção mínima
            elemento.largura = Math.max(20, Math.abs(elemento.largura));
            elemento.altura = Math.max(20, Math.abs(elemento.altura));
        }
        
        estado.modificado = true;
        redesenharTudo();
    }
    
    // Mostra informações do elemento no hover
    if (!estado.arrastando && !estado.redimensionando && !estado.desenhando) {
        mostrarInfoHover(x, y);
    }
}

function finalizarInteracao() {
    estado.arrastando = false;
    estado.desenhando = false;
    estado.redimensionando = false;
    estado.pontoRedim = null;
    
    canvas.style.cursor = estado.ferramenta === 'mover' ? 'grab' : 
                         estado.ferramenta === 'zoom' ? 'zoom-in' : 'default';
    
    // Ajusta dimensões negativas
    if (estado.elementoSelecionado !== null) {
        const elemento = estado.elementos[estado.elementoSelecionado];
        
        if (elemento.largura < 0) {
            elemento.pos_x += elemento.largura;
            elemento.largura = Math.abs(elemento.largura);
        }
        
        if (elemento.altura < 0) {
            elemento.pos_y += elemento.altura;
            elemento.altura = Math.abs(elemento.altura);
        }
        
        atualizarCamposElemento(elemento);
        estado.modificado = true;
        redesenharTudo();
    }
}

// ==================== FUNÇÕES AUXILIARES ====================
function encontrarElementoNaPosicao(x, y) {
    // Procura do último para o primeiro
    const elementosOrdenados = [...estado.elementos].sort((a, b) => b.ordem_z - a.ordem_z);
    
    for (const elemento of elementosOrdenados) {
        const idx = estado.elementos.indexOf(elemento);
        
        if (x >= elemento.pos_x && 
            x <= elemento.pos_x + elemento.largura && 
            y >= elemento.pos_y && 
            y <= elemento.pos_y + elemento.altura) {
            return idx;
        }
    }
    
    return -1;
}

function redimensionarElemento(elemento, ponto, x, y) {
    switch(ponto) {
        case 'nw': // Canto superior esquerdo
            elemento.largura += elemento.pos_x - x;
            elemento.altura += elemento.pos_y - y;
            elemento.pos_x = x;
            elemento.pos_y = y;
            break;
            
        case 'ne': // Canto superior direito
            elemento.largura = x - elemento.pos_x;
            elemento.altura += elemento.pos_y - y;
            elemento.pos_y = y;
            break;
            
        case 'sw': // Canto inferior esquerdo
            elemento.largura += elemento.pos_x - x;
            elemento.altura = y - elemento.pos_y;
            elemento.pos_x = x;
            break;
            
        case 'se': // Canto inferior direito
            elemento.largura = x - elemento.pos_x;
            elemento.altura = y - elemento.pos_y;
            break;
    }
    
    // Limites mínimos
    elemento.largura = Math.max(20, elemento.largura);
    elemento.altura = Math.max(20, elemento.altura);
    
    // Atualiza campos
    document.getElementById('inputPosX').value = Math.round(elemento.pos_x);
    document.getElementById('inputPosY').value = Math.round(elemento.pos_y);
    document.getElementById('inputLargura').value = Math.round(elemento.largura);
    document.getElementById('inputAltura').value = Math.round(elemento.altura);
}

function mostrarInfoHover(x, y) {
    // Remove informações anteriores
    const infosAntigas = document.querySelectorAll('.elemento-info');
    infosAntigas.forEach(el => el.remove());
    
    const elementoIdx = encontrarElementoNaPosicao(x, y);
    
    if (elementoIdx !== -1 && estado.showInfo) {
        const elemento = estado.elementos[elementoIdx];
        
        if (elemento.tipo === 'RETANGULO') {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'elemento-info';
            infoDiv.style.left = `${x * estado.zoom + 15}px`;
            infoDiv.style.top = `${y * estado.zoom + 15}px`;
            
            let infoHTML = `<div class="info-lote">${elemento.identificador || 'Lote sem identificador'}</div>`;
            
            if (elemento.quantidade !== undefined) {
                infoHTML += `<div class="info-quantidade">${elemento.quantidade} unidades</div>`;
            }
            
            infoDiv.innerHTML = infoHTML;
            document.querySelector('.canvas-container').appendChild(infoDiv);
        }
    }
}

// ==================== INTERFACE ====================
function selecionarFerramenta(ferramenta) {
    if (!CONFIG.usuario.is_admin) return;
    
    document.querySelectorAll('[data-ferramenta]').forEach(btn => {
        btn.classList.remove('active');
    });
    
    event.target.closest('[data-ferramenta]').classList.add('active');
    estado.ferramenta = ferramenta;
    
    const modos = {
        'mover': 'Mover',
        'selecionar': 'Selecionar',
        'retangulo': 'Criar Lote',
        'texto': 'Texto',
        'excluir': 'Excluir',
        'zoom': 'Zoom'
    };
    
    document.getElementById('modoAtual').textContent = modos[ferramenta] || 'Selecionar';
    
    canvas.style.cursor = {
        'mover': 'grab',
        'selecionar': 'default',
        'retangulo': 'crosshair',
        'texto': 'text',
        'excluir': 'not-allowed',
        'zoom': 'zoom-in'
    }[ferramenta] || 'default';
    
    // Mostra/oculta painéis
    document.getElementById('painelTexto').style.display = ferramenta === 'texto' ? 'block' : 'none';
}

function atualizarInterface() {
    // Atualiza contador
    const totalElementos = estado.elementos.filter(e => e.tipo === 'RETANGULO').length;
    document.getElementById('contadorElementos').textContent = totalElementos;
    document.getElementById('contadorTotal').textContent = totalElementos;
    
    // Atualiza lista de elementos (apenas para admin)
    if (CONFIG.usuario.is_admin) {
        const lista = document.getElementById('listaElementos');
        lista.innerHTML = '';
        
        const elementosOrdenados = [...estado.elementos].sort((a, b) => b.ordem_z - a.ordem_z);
        
        elementosOrdenados.forEach((elemento, indexOriginal) => {
            const idx = estado.elementos.indexOf(elemento);
            const div = document.createElement('div');
            div.className = `elemento-item ${idx === estado.elementoSelecionado ? 'selecionado' : ''}`;
            
            const icon = elemento.tipo === 'RETANGULO' ? 'fa-map-marker-alt' : 'fa-font';
            const cor = elemento.cor_preenchimento || '#4f46e5';
            
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center" style="width: 80%;">
                        <i class="fas ${icon} me-2" style="color: ${cor};"></i>
                        <div style="overflow: hidden; text-overflow: ellipsis;">
                            <strong>${elemento.identificador || `Lote ${idx + 1}`}</strong>
                            <div class="small">${elemento.quantidade || 0} unidades</div>
                            <div class="small">Camada ${elemento.ordem_z}</div>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-danger btn-excluir-lista" data-index="${idx}">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            div.addEventListener('click', (e) => {
                if (!e.target.closest('.btn-excluir-lista')) {
                    estado.elementoSelecionado = idx;
                    atualizarCamposElemento(elemento);
                    redesenharTudo();
                    atualizarInterface();
                }
            });
            
            lista.appendChild(div);
        });
        
        // Configura botões de exclusão
        document.querySelectorAll('.btn-excluir-lista').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                const idx = parseInt(this.dataset.index);
                const elemento = estado.elementos[idx];
                
                if (confirm(`Excluir "${elemento.identificador || 'Lote'}"?`)) {
                    estado.elementos.splice(idx, 1);
                    if (estado.elementoSelecionado === idx) {
                        estado.elementoSelecionado = null;
                    }
                    estado.modificado = true;
                    atualizarInterface();
                    atualizarEstatisticas();
                    redesenharTudo();
                }
            });
        });
    }
    
    // Atualiza informações do elemento selecionado
    if (estado.elementoSelecionado !== null) {
        const elemento = estado.elementos[estado.elementoSelecionado];
        document.getElementById('infoSelecionado').textContent = 
            elemento.identificador || `Elemento ${estado.elementoSelecionado + 1}`;
        
        if (CONFIG.usuario.is_admin) {
            atualizarCamposElemento(elemento);
        }
    } else {
        document.getElementById('infoSelecionado').textContent = 'Nenhum';
        if (CONFIG.usuario.is_admin) {
            limparCamposElemento();
        }
    }
}

function atualizarCamposElemento(elemento) {
    document.getElementById('inputIdentificador').value = elemento.identificador || '';
    document.getElementById('inputQuantidade').value = elemento.quantidade || 0;
    document.getElementById('selectTipo').value = elemento.tipo;
    document.getElementById('corPreenchimento').value = elemento.cor_preenchimento || '#4f46e5';
    document.getElementById('corBorda').value = elemento.cor_borda || '#000000';
    document.getElementById('espessuraBorda').value = elemento.espessura_borda || 2;
    document.getElementById('valorEspessura').textContent = elemento.espessura_borda || 2;
    document.getElementById('opacidade').value = elemento.opacidade || 80;
    document.getElementById('valorOpacidade').textContent = elemento.opacidade || 80;
    document.getElementById('inputRotacao').value = elemento.rotacao || 0;
    document.getElementById('valorRotacao').textContent = elemento.rotacao || 0;
    document.getElementById('inputPosX').value = Math.round(elemento.pos_x);
    document.getElementById('inputPosY').value = Math.round(elemento.pos_y);
    document.getElementById('inputLargura').value = Math.round(elemento.largura);
    document.getElementById('inputAltura').value = Math.round(elemento.altura);
    
    if (elemento.tipo === 'TEXTO') {
        document.getElementById('inputConteudoTexto').value = elemento.conteudo_texto || '';
        document.getElementById('selectFonte').value = elemento.fonte_nome || 'Arial';
        document.getElementById('tamanhoFonte').value = elemento.fonte_tamanho || 14;
    }
}

function limparCamposElemento() {
    document.getElementById('inputIdentificador').value = '';
    document.getElementById('inputQuantidade').value = 0;
    document.getElementById('corPreenchimento').value = '#4f46e5';
    document.getElementById('corBorda').value = '#000000';
    document.getElementById('espessuraBorda').value = 2;
    document.getElementById('valorEspessura').textContent = '2';
    document.getElementById('opacidade').value = 80;
    document.getElementById('valorOpacidade').textContent = '80';
    document.getElementById('inputRotacao').value = 0;
    document.getElementById('valorRotacao').textContent = '0';
    document.getElementById('inputPosX').value = 0;
    document.getElementById('inputPosY').value = 0;
    document.getElementById('inputLargura').value = 120;
    document.getElementById('inputAltura').value = 80;
    document.getElementById('inputConteudoTexto').value = '';
}

// ==================== ATUALIZAÇÃO DE PROPRIEDADES ====================
function atualizarPropriedade() {
    if (estado.elementoSelecionado === null) return;
    
    const elemento = estado.elementos[estado.elementoSelecionado];
    const campo = event.target.id;
    const valor = event.target.value;
    
    switch(campo) {
        case 'inputIdentificador':
            elemento.identificador = valor;
            break;
        case 'inputQuantidade':
            elemento.quantidade = parseInt(valor) || 0;
            break;
        case 'corPreenchimento':
            elemento.cor_preenchimento = valor;
            break;
        case 'corBorda':
            elemento.cor_borda = valor;
            break;
        case 'espessuraBorda':
            elemento.espessura_borda = parseInt(valor);
            document.getElementById('valorEspessura').textContent = valor;
            break;
        case 'opacidade':
            elemento.opacidade = parseInt(valor);
            document.getElementById('valorOpacidade').textContent = valor;
            break;
        case 'inputRotacao':
            elemento.rotacao = parseInt(valor);
            document.getElementById('valorRotacao').textContent = valor;
            break;
        case 'inputConteudoTexto':
            elemento.conteudo_texto = valor;
            break;
        case 'selectFonte':
            elemento.fonte_nome = valor;
            break;
        case 'tamanhoFonte':
            elemento.fonte_tamanho = parseInt(valor);
            break;
    }
    
    estado.modificado = true;
    redesenharTudo();
    atualizarInterface();
    atualizarEstatisticas();
}

function atualizarPosicao() {
    if (estado.elementoSelecionado === null) return;
    
    const elemento = estado.elementos[estado.elementoSelecionado];
    elemento.pos_x = parseInt(document.getElementById('inputPosX').value);
    elemento.pos_y = parseInt(document.getElementById('inputPosY').value);
    
    estado.modificado = true;
    redesenharTudo();
}

function atualizarDimensoes() {
    if (estado.elementoSelecionado === null) return;
    
    const elemento = estado.elementos[estado.elementoSelecionado];
    elemento.largura = parseInt(document.getElementById('inputLargura').value);
    elemento.altura = parseInt(document.getElementById('inputAltura').value);
    
    estado.modificado = true;
    redesenharTudo();
}

function aplicarDimensoesManualmente() {
    atualizarDimensoes();
}

// ==================== CONTROLE DE CAMADAS ====================
function alterarOrdemZ(acao) {
    if (estado.elementoSelecionado === null) return;
    
    const elemento = estado.elementos[estado.elementoSelecionado];
    
    switch(acao) {
        case 'frente':
            const maxZ = Math.max(...estado.elementos.map(e => e.ordem_z));
            if (elemento.ordem_z < maxZ) {
                elemento.ordem_z++;
                estado.elementos.forEach(e => {
                    if (e !== elemento && e.ordem_z === elemento.ordem_z) {
                        e.ordem_z--;
                    }
                });
            }
            break;
            
        case 'atras':
            const minZ = Math.min(...estado.elementos.map(e => e.ordem_z));
            if (elemento.ordem_z > minZ) {
                elemento.ordem_z--;
                estado.elementos.forEach(e => {
                    if (e !== elemento && e.ordem_z === elemento.ordem_z) {
                        e.ordem_z++;
                    }
                });
            }
            break;
    }
    
    estado.modificado = true;
    atualizarInterface();
    redesenharTudo();
}

// ==================== ZOOM ====================
function ajustarZoom(delta) {
    estado.zoom = Math.min(3, Math.max(0.2, estado.zoom + delta));
    atualizarInfoZoom();
    redesenharTudo();
}

function resetarZoom() {
    estado.zoom = 1.0;
    atualizarInfoZoom();
    redesenharTudo();
}

function eventoZoom(e) {
    if (e.ctrlKey) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        ajustarZoom(delta);
    }
}

function atualizarInfoZoom() {
    document.getElementById('infoZoom').textContent = `${Math.round(estado.zoom * 100)}%`;
}

// ==================== GRID ====================
function toggleGrid() {
    estado.showGrid = !estado.showGrid;
    document.getElementById('btnToggleGrid').classList.toggle('active', estado.showGrid);
    redesenharTudo();
}

// ==================== ESTATÍSTICAS ====================
function atualizarEstatisticas() {
    const lotes = estado.elementos.filter(e => e.tipo === 'RETANGULO');
    const quantidadeTotal = lotes.reduce((sum, e) => sum + (e.quantidade || 0), 0);
    
    if (CONFIG.usuario.is_admin) {
        // Atualiza status badge
        document.getElementById('contadorTotal').textContent = lotes.length;
    } else {
        // Atualiza painel de estatísticas
        const statsTotal = document.getElementById('statsTotal');
        const statsQuantidade = document.getElementById('statsQuantidade');
        
        if (statsTotal) statsTotal.textContent = lotes.length;
        if (statsQuantidade) statsQuantidade.textContent = quantidadeTotal.toLocaleString();
    }
}

// ==================== EVENTO DUPLO CLIQUE ====================
function eventoDuploClique(e) {
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / estado.zoom;
    const y = (e.clientY - rect.top) / estado.zoom;
    
    const elementoIdx = encontrarElementoNaPosicao(x, y);
    
    if (elementoIdx !== -1) {
        const elemento = estado.elementos[elementoIdx];
        
        // Se não for admin, apenas mostra informações
        if (!CONFIG.usuario.is_admin) {
            alert(
                `Lote: ${elemento.identificador || 'Sem identificador'}\n` +
                `Quantidade: ${elemento.quantidade || 0} unidades\n` +
                `Posição: ${Math.round(elemento.pos_x)}, ${Math.round(elemento.pos_y)}\n` +
                `Tamanho: ${elemento.largura}x${elemento.altura}`
            );
        }
    }
}

// ==================== TECLADO ====================
function tecladoPressionado(e) {
    // Atalhos de teclado (apenas para admin)
    if (!CONFIG.usuario.is_admin) return;
    
    switch(e.key.toLowerCase()) {
        case 'm':
            selecionarFerramenta('mover');
            break;
        case 'q':
            selecionarFerramenta('retangulo');
            break;
        case 'e':
            selecionarFerramenta('texto');
            break;
        case 'delete':
            if (estado.elementoSelecionado !== null) {
                estado.elementos.splice(estado.elementoSelecionado, 1);
                estado.elementoSelecionado = null;
                estado.modificado = true;
                atualizarInterface();
                atualizarEstatisticas();
                redesenharTudo();
            }
            break;
        case 's':
            if (e.ctrlKey) {
                e.preventDefault();
                salvarLayout();
            }
            break;
    }
}

// ==================== SALVAR ====================
async function salvarLayout() {
    if (!CONFIG.usuario.is_admin) {
        alert('Apenas administradores podem salvar layouts.');
        return;
    }
    
    const btn = document.getElementById('btnSalvar');
    const originalHTML = btn.innerHTML;
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Salvando...';
    btn.disabled = true;
    
    // Prepara dados
    const dados = {
        armazem_id: CONFIG.armazem.id,
        elementos: estado.elementos.map((elemento, index) => ({
            id: elemento.id || null,
            tipo: elemento.tipo,
            pos_x: Math.round(elemento.pos_x),
            pos_y: Math.round(elemento.pos_y),
            largura: Math.round(elemento.largura),
            altura: Math.round(elemento.altura),
            cor_preenchimento: elemento.cor_preenchimento,
            cor_borda: elemento.cor_borda,
            espessura_borda: elemento.espessura_borda,
            opacidade: elemento.opacidade,
            rotacao: elemento.rotacao,
            conteudo_texto: elemento.conteudo_texto || '',
            fonte_nome: elemento.fonte_nome || 'Arial',
            fonte_tamanho: elemento.fonte_tamanho || 14,
            texto_negrito: elemento.texto_negrito || false,
            texto_italico: elemento.texto_italico || false,
            texto_sublinhado: elemento.texto_sublinhado || false,
            texto_direcao: elemento.texto_direcao || 'horizontal',
            texto_alinhamento: elemento.texto_alinhamento || 'left',
            identificador: elemento.identificador || '',
            quantidade: elemento.quantidade || 0,
            ordem_z: elemento.ordem_z || (index + 1),
            data_atualizacao: new Date().toISOString()
        }))
    };
    
    try {
        const response = await fetch(CONFIG.urls.salvar, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CONFIG.urls.csrf
            },
            body: JSON.stringify(dados)
        });
        
        const resultado = await response.json();
        
        if (resultado.success) {
            estado.modificado = false;
            
            // Atualiza IDs dos elementos
            if (resultado.elementos_salvos) {
                resultado.elementos_salvos.forEach((salvo, index) => {
                    if (estado.elementos[index]) {
                        estado.elementos[index].id = salvo.id;
                    }
                });
            }
            
            alert('✅ Layout salvo com sucesso!');
            
            // Atualiza estatísticas
            atualizarEstatisticas();
        } else {
            alert(`❌ Erro ao salvar: ${resultado.error}`);
        }
    } catch (error) {
        alert(`❌ Erro de conexão: ${error.message}`);
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
}

// ==================== EXPORTAR FUNÇÕES ====================
window.inicializarEditor = inicializarEditor;
window.redesenharTudo = redesenharTudo;
window.atualizarEstatisticas = atualizarEstatisticas;