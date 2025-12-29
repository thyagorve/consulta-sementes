// static/sapp/js/editor_mapa.js - VERSÃO REVISADA E CORRIGIDA
document.addEventListener('DOMContentLoaded', function() {
    // Configuração inicial
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
        modificado: false,
        textoDigitando: false,
        textoAtual: ''
    };
    
    // ===== FUNÇÕES DE DESENHO MELHORADAS =====
    function redesenharCanvas() {
        // Limpa canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Desenha grid de fundo
        desenharGrid();
        
        // Desenha todos os elementos
        estado.elementos.forEach((elemento, index) => {
            desenharElemento(elemento);
            
            // Se está selecionado, desenha controles
            if (estado.elementoSelecionado === index) {
                desenharControlesSelecao(elemento);
            }
        });
    }
    
    function desenharGrid() {
        const gridSize = 20;
        ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
        ctx.lineWidth = 0.5;
        
        // Linhas verticais
        for (let x = 0; x <= canvas.width; x += gridSize) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
            ctx.stroke();
        }
        
        // Linhas horizontais
        for (let y = 0; y <= canvas.height; y += gridSize) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }
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
                    ctx.font = 'bold 12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    
                    // Quebra texto se for muito longo
                    const texto = elemento.identificador;
                    const maxChars = Math.floor(elemento.largura / 8);
                    if (texto.length > maxChars) {
                        ctx.font = 'bold 10px Arial';
                    }
                    
                    ctx.fillText(
                        texto,
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
                
                // Desenha linha - CORREÇÃO AQUI
                // Se largura e altura são 0, desenha ponto
                if (elemento.largura === 0 && elemento.altura === 0) {
                    ctx.arc(elemento.pos_x, elemento.pos_y, 2, 0, Math.PI * 2);
                    ctx.fill();
                } else {
                    ctx.moveTo(elemento.pos_x, elemento.pos_y);
                    // Usa largura e altura como coordenadas finais
                    ctx.lineTo(elemento.pos_x + elemento.largura, elemento.pos_y + elemento.altura);
                    ctx.stroke();
                }
                
                ctx.setLineDash([]); // Reseta
                break;
                
            case 'TEXTO':
                // CORREÇÃO DO TEXTO
                const estiloFonte = [
                    elemento.texto_negrito ? 'bold' : '',
                    elemento.texto_italico ? 'italic' : '',
                    `${elemento.fonte_tamanho}px`,
                    elemento.fonte_nome
                ].filter(Boolean).join(' ');
                
                ctx.font = estiloFonte;
                ctx.fillStyle = elemento.cor_preenchimento;
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                
                // Texto vertical ou horizontal
                if (elemento.texto_direcao === 'vertical') {
                    ctx.save();
                    ctx.translate(elemento.pos_x, elemento.pos_y);
                    ctx.rotate(-Math.PI / 2); // Rotaciona -90 graus
                    ctx.fillText(elemento.conteudo_texto, 0, 0);
                    ctx.restore();
                } else {
                    ctx.fillText(elemento.conteudo_texto, elemento.pos_x, elemento.pos_y);
                }
                
                // Mede texto para ajustar largura/altura
                const metrics = ctx.measureText(elemento.conteudo_texto);
                elemento.largura = metrics.width;
                elemento.altura = elemento.fonte_tamanho;
                break;
        }
        
        ctx.restore();
    }
    
    function desenharControlesSelecao(elemento) {
        // Retângulo de seleção
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
        
        // Pontos de redimensionamento (apenas para retângulos)
        if (elemento.tipo === 'RETANGULO' || elemento.tipo === 'LINHA') {
            const tamanhoPonto = 6;
            const pontos = [
                // Cantos
                {x: elemento.pos_x, y: elemento.pos_y},
                {x: elemento.pos_x + elemento.largura, y: elemento.pos_y},
                {x: elemento.pos_x, y: elemento.pos_y + elemento.altura},
                {x: elemento.pos_x + elemento.largura, y: elemento.pos_y + elemento.altura}
            ];
            
            pontos.forEach(ponto => {
                ctx.fillStyle = '#ffffff';
                ctx.strokeStyle = '#4f46e5';
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.arc(ponto.x, ponto.y, tamanhoPonto, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
            });
        }
    }
    
    // ===== INTERAÇÃO COM O CANVAS REVISADA =====
    canvas.addEventListener('mousedown', iniciarInteracao);
    canvas.addEventListener('mousemove', moverInteracao);
    canvas.addEventListener('mouseup', finalizarInteracao);
    canvas.addEventListener('mouseleave', finalizarInteracao);
    
    function iniciarInteracao(e) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        estado.inicioX = x;
        estado.inicioY = y;
        
        // Se estiver digitando texto, não inicia interação
        if (estado.textoDigitando) return;
        
        // Verifica se clicou em elemento existente
        const elementoIdx = encontrarElementoNaPosicao(x, y);
        
        if (elementoIdx !== -1) {
            // Seleciona elemento existente
            estado.elementoSelecionado = elementoIdx;
            const elemento = estado.elementos[elementoIdx];
            
            // Verifica se clicou em ponto de redimensionamento
            const ponto = encontrarPontoRedimensionamento(x, y, elemento);
            if (ponto && (elemento.tipo === 'RETANGULO' || elemento.tipo === 'LINHA')) {
                estado.modoRedimensionamento = true;
                estado.pontoRedimensionamento = ponto;
            } else {
                estado.modoRedimensionamento = false;
                estado.offsetX = x - elemento.pos_x;
                estado.offsetY = y - elemento.pos_y;
            }
            
            estado.isDesenhando = true;
            
            atualizarListaElementos();
        } else {
            // Inicia criação de novo elemento
            if (estado.ferramentaAtiva === 'excluir') return;
            
            estado.elementoSelecionado = null;
            estado.isDesenhando = true;
            
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
                        linha_tipo: 'solida',
                        identificador: 'Linha'
                    };
                    break;
                    
                case 'texto':
                    // Para texto, inicia modo de digitação
                    estado.textoDigitando = true;
                    estado.textoAtual = '';
                    
                    novoElemento = {
                        tipo: 'TEXTO',
                        pos_x: x,
                        pos_y: y,
                        largura: 0,
                        altura: 20,
                        cor_preenchimento: document.getElementById('corPreenchimento').value,
                        conteudo_texto: '',
                        fonte_nome: 'Arial',
                        fonte_tamanho: parseInt(document.getElementById('selectFonteTamanho').value),
                        texto_negrito: false,
                        texto_italico: false,
                        texto_direcao: 'horizontal',
                        identificador: 'Texto'
                    };
                    
                    estado.elementos.push(novoElemento);
                    estado.elementoSelecionado = estado.elementos.length - 1;
                    
                    // Foca no input de texto
                    const inputTexto = document.getElementById('inputTexto');
                    inputTexto.value = '';
                    inputTexto.style.display = 'block';
                    inputTexto.focus();
                    inputTexto.select();
                    
                    estado.modificado = true;
                    atualizarListaElementos();
                    redesenharCanvas();
                    return; // Sai da função
                    
                default:
                    return;
            }
            
            if (novoElemento) {
                estado.elementos.push(novoElemento);
                estado.elementoSelecionado = estado.elementos.length - 1;
                estado.modificado = true;
                
                atualizarListaElementos();
            }
        }
        
        redesenharCanvas();
    }
    
    function moverInteracao(e) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Atualiza coordenadas
        document.getElementById('coordenadas').textContent = `X: ${Math.round(x)}, Y: ${Math.round(y)}`;
        
        if (!estado.isDesenhando) return;
        
        if (estado.elementoSelecionado !== null) {
            const elemento = estado.elementos[estado.elementoSelecionado];
            
            if (estado.modoRedimensionamento && estado.pontoRedimensionamento) {
                // Redimensionamento
                redimensionarElemento(elemento, estado.pontoRedimensionamento, x, y);
            } else if (elemento.tipo === 'TEXTO' && estado.textoDigitando) {
                // Texto em digitação - não move
            } else {
                // Arrastar ou redimensionar criação
                if (elemento.largura === 0 && elemento.altura === 0 && elemento.tipo !== 'TEXTO') {
                    // Ainda criando - redimensiona
                    elemento.largura = x - elemento.pos_x;
                    elemento.altura = y - elemento.pos_y;
                } else if (!estado.modoRedimensionamento && elemento.tipo !== 'TEXTO') {
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
        if (!estado.isDesenhando && !estado.textoDigitando) return;
        
        estado.isDesenhando = false;
        estado.modoRedimensionamento = false;
        estado.pontoRedimensionamento = null;
        
        // Se criou um novo elemento, ajusta
        if (estado.elementoSelecionado !== null) {
            const elemento = estado.elementos[estado.elementoSelecionado];
            
            // Ajusta dimensões negativas
            if (elemento.largura < 0) {
                elemento.pos_x += elemento.largura;
                elemento.largura = Math.abs(elemento.largura);
            }
            if (elemento.altura < 0) {
                elemento.pos_y += elemento.altura;
                elemento.altura = Math.abs(elemento.altura);
            }
            
            // Remove elementos muito pequenos (exceto texto)
            if (elemento.tipo !== 'TEXTO' && Math.abs(elemento.largura) < 5 && Math.abs(elemento.altura) < 5) {
                estado.elementos.splice(estado.elementoSelecionado, 1);
                estado.elementoSelecionado = null;
                estado.modificado = true;
            }
            
            // Para retângulos sem identificador, abre modal
            if (elemento.tipo === 'RETANGULO' && !elemento.identificador) {
                setTimeout(() => abrirModalIdentificacao(elemento), 100);
            }
            
            redesenharCanvas();
            atualizarListaElementos();
        }
    }
    
    // ===== FUNÇÕES AUXILIARES MELHORADAS =====
    function encontrarElementoNaPosicao(x, y) {
        for (let i = estado.elementos.length - 1; i >= 0; i--) {
            const elemento = estado.elementos[i];
            
            // Verifica colisão baseada no tipo
            let colidiu = false;
            
            if (elemento.tipo === 'TEXTO') {
                // Para texto, verifica área aproximada
                const metrics = ctx.measureText(elemento.conteudo_texto);
                colidiu = (
                    x >= elemento.pos_x - 5 &&
                    x <= elemento.pos_x + metrics.width + 5 &&
                    y >= elemento.pos_y - 5 &&
                    y <= elemento.pos_y + elemento.fonte_tamanho + 5
                );
            } else if (elemento.tipo === 'LINHA') {
                // Para linha, verifica proximidade
                const distancia = distanciaParaLinha(x, y, elemento);
                colidiu = distancia < 10; // 10px de tolerância
            } else {
                // Para retângulos
                colidiu = (
                    x >= elemento.pos_x &&
                    x <= elemento.pos_x + elemento.largura &&
                    y >= elemento.pos_y &&
                    y <= elemento.pos_y + elemento.altura
                );
            }
            
            if (colidiu) return i;
        }
        return -1;
    }
    
    function encontrarPontoRedimensionamento(x, y, elemento) {
        if (elemento.tipo === 'TEXTO') return null;
        
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
    }
    
    function distanciaParaLinha(x, y, linha) {
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
    
    // ===== FUNÇÕES DE INTERFACE =====
    function atualizarListaElementos() {
        const container = document.getElementById('listaElementos');
        container.innerHTML = '';
        
        estado.elementos.forEach((elemento, index) => {
            const item = document.createElement('div');
            item.className = `list-group-item list-group-item-action elemento-item ${index === estado.elementoSelecionado ? 'active' : ''}`;
            item.dataset.id = elemento.id || `new_${index}`;
            
            const tipoIcon = {
                'RETANGULO': 'fa-square',
                'LINHA': 'fa-minus',
                'TEXTO': 'fa-font'
            }[elemento.tipo] || 'fa-shapes';
            
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <div class="me-2" style="color: ${elemento.cor_preenchimento};">
                            <i class="fas ${tipoIcon}"></i>
                        </div>
                        <div>
                            <strong class="${index === estado.elementoSelecionado ? 'text-white' : ''}">
                                ${elemento.identificador || 'Sem nome'}
                            </strong>
                            <div class="small ${index === estado.elementoSelecionado ? 'text-white-50' : 'text-muted'}">
                                ${elemento.tipo} • ${elemento.pos_x}, ${elemento.pos_y}
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-${index === estado.elementoSelecionado ? 'light' : 'danger'} btn-excluir-elemento"
                            data-index="${index}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            item.addEventListener('click', () => {
                estado.elementoSelecionado = index;
                redesenharCanvas();
                document.querySelectorAll('.elemento-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
            });
            
            container.appendChild(item);
        });
        
        if (estado.elementos.length === 0) {
            container.innerHTML = `
                <div class="text-center py-3 text-muted">
                    <i class="fas fa-info-circle me-1"></i>
                    Nenhum elemento criado ainda
                </div>
            `;
        }
    }
    
    function abrirModalIdentificacao(elemento) {
        const modal = new bootstrap.Modal(document.getElementById('modalIdentificar'));
        const input = document.getElementById('inputIdentificador');
        const select = document.getElementById('selectTipoElemento');
        
        input.value = elemento.identificador || '';
        select.value = elemento.tipo;
        
        document.getElementById('btnConfirmarIdentificador').onclick = function() {
            elemento.identificador = input.value.trim();
            elemento.tipo = select.value;
            
            // Validações
            if (elemento.tipo === 'RETANGULO' && !elemento.identificador) {
                alert('Endereços devem ter um identificador!');
                return;
            }
            
            estado.modificado = true;
            modal.hide();
            atualizarListaElementos();
            redesenharCanvas();
        };
        
        modal.show();
        input.focus();
        input.select();
    }
    
    // ===== CONFIGURAÇÃO DOS CONTROLES =====
    // Botões de ferramentas
    document.querySelectorAll('.btn-ferramenta').forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove todas as seleções
            document.querySelectorAll('.btn-ferramenta').forEach(b => {
                b.classList.remove('active', 'btn-primary');
                b.classList.add('btn-outline-primary');
            });
            
            // Ativa a ferramenta clicada
            this.classList.remove('btn-outline-primary');
            this.classList.add('btn-primary', 'active');
            estado.ferramentaAtiva = this.dataset.ferramenta;
            
            // Mostra/oculta painel de texto
            const painelTexto = document.getElementById('painelTexto');
            painelTexto.style.display = estado.ferramentaAtiva === 'texto' ? 'block' : 'none';
            
            // Altera cursor
            const cursores = {
                'selecionar': 'default',
                'retangulo': 'crosshair',
                'linha': 'crosshair',
                'texto': 'text',
                'excluir': 'not-allowed'
            };
            canvas.style.cursor = cursores[estado.ferramentaAtiva] || 'default';
            
            // Sai do modo texto
            estado.textoDigitando = false;
        });
    });
    
    // Input de texto
    document.getElementById('inputTexto')?.addEventListener('input', function(e) {
        if (estado.elementoSelecionado !== null && estado.textoDigitando) {
            const elemento = estado.elementos[estado.elementoSelecionado];
            elemento.conteudo_texto = this.value;
            estado.modificado = true;
            redesenharCanvas();
        }
    });
    
    document.getElementById('inputTexto')?.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === 'Escape') {
            estado.textoDigitando = false;
            this.style.display = 'none';
            
            // Se texto vazio, remove o elemento
            if (estado.elementoSelecionado !== null) {
                const elemento = estado.elementos[estado.elementoSelecionado];
                if (!elemento.conteudo_texto.trim()) {
                    estado.elementos.splice(estado.elementoSelecionado, 1);
                    estado.elementoSelecionado = null;
                }
                atualizarListaElementos();
                redesenharCanvas();
            }
        }
    });
    
    // Botão identificar
    document.getElementById('btnIdentificar')?.addEventListener('click', () => {
        if (estado.elementoSelecionado !== null) {
            abrirModalIdentificacao(estado.elementos[estado.elementoSelecionado]);
        } else {
            alert('Selecione um elemento primeiro!');
        }
    });
    
    // Botão excluir
    document.addEventListener('click', (e) => {
        if (e.target.closest('.btn-excluir-elemento')) {
            const btn = e.target.closest('.btn-excluir-elemento');
            const index = parseInt(btn.dataset.index);
            
            if (confirm(`Excluir "${estado.elementos[index]?.identificador || 'elemento'}"?`)) {
                estado.elementos.splice(index, 1);
                estado.elementoSelecionado = null;
                estado.modificado = true;
                redesenharCanvas();
                atualizarListaElementos();
            }
        }
    });
    
    // Botão salvar
    document.getElementById('btnSalvar')?.addEventListener('click', async () => {
        if (!estado.modificado) {
            showAlert('⚠️ Nenhuma alteração para salvar', 'warning');
            return;
        }
        
        const dados = {
            armazem_id: ARMAZEM_DATA.id,
            elementos: estado.elementos.map((elemento, index) => ({
                ...elemento,
                ordem_z: index + 1
            }))
        };
        
        try {
            const response = await fetch(ARMAZEM_DATA.urlSalvar, {
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
                showAlert('✅ Layout salvo com sucesso!', 'success');
                
                // Atualiza IDs
                if (result.elementos_salvos) {
                    result.elementos_salvos.forEach((savedElem, index) => {
                        if (estado.elementos[index]) {
                            estado.elementos[index].id = savedElem.id;
                        }
                    });
                }
                
                atualizarListaElementos();
            } else {
                showAlert(`❌ Erro ao salvar: ${result.error}`, 'danger');
            }
        } catch (error) {
            showAlert(`❌ Erro de conexão: ${error.message}`, 'danger');
        }
    });
    
    // Botão reset
    document.getElementById('btnReset')?.addEventListener('click', () => {
        if (!estado.modificado || confirm('Recarregar layout do servidor? Alterações não salvas serão perdidas.')) {
            location.reload();
        }
    });
    
    // Seletor de armazém
    document.getElementById('selectArmazem')?.addEventListener('change', function() {
        if (estado.modificado && !confirm('Você tem alterações não salvas. Deseja realmente sair?')) {
            this.value = window.location.href;
            return;
        }
        window.location.href = this.value;
    });
    
    // Controles de propriedades
    document.getElementById('corPreenchimento')?.addEventListener('change', function() {
        if (estado.elementoSelecionado !== null) {
            estado.elementos[estado.elementoSelecionado].cor_preenchimento = this.value;
            estado.modificado = true;
            redesenharCanvas();
        }
    });
    
    document.getElementById('corBorda')?.addEventListener('change', function() {
        if (estado.elementoSelecionado !== null) {
            estado.elementos[estado.elementoSelecionado].cor_borda = this.value;
            estado.modificado = true;
            redesenharCanvas();
        }
    });
    
    document.getElementById('espessuraBorda')?.addEventListener('input', function() {
        const valor = parseInt(this.value);
        document.getElementById('espessuraValor').textContent = `${valor}px`;
        
        if (estado.elementoSelecionado !== null) {
            estado.elementos[estado.elementoSelecionado].espessura_borda = valor;
            estado.modificado = true;
            redesenharCanvas();
        }
    });
    
    // ===== FUNÇÕES UTILITÁRIAS =====
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
    
    function showAlert(texto, tipo = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${tipo} alert-dismissible fade show position-fixed`;
        alert.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
        `;
        alert.innerHTML = `
            ${texto}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alert);
        
        setTimeout(() => {
            if (alert.parentNode) alert.remove();
        }, 5000);
    }
    
    // Avisa antes de sair
    window.addEventListener('beforeunload', function(e) {
        if (estado.modificado) {
            e.preventDefault();
            e.returnValue = 'Você tem alterações não salvas no mapa. Deseja realmente sair?';
        }
    });
    
    // ===== INICIALIZAÇÃO =====
    function inicializar() {
        // Configura ferramenta inicial
        document.querySelector('[data-ferramenta="selecionar"]').classList.add('btn-primary', 'active');
        
        // Inicializa lista
        atualizarListaElementos();
        
        // Desenha inicial
        redesenharCanvas();
        
        console.log('✅ Editor de Mapa (revisado) inicializado!');
    }
    
    inicializar();
});