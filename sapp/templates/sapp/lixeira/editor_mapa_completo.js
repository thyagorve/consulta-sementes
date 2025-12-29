// static/sapp/js/editor_mapa_completo.js
document.addEventListener('DOMContentLoaded', function() {
    // ELEMENTOS DOM
    const canvas = document.getElementById('meuCanvas');
    const ctx = canvas.getContext('2d');
    const pontosControle = document.getElementById('pontosControle');
    
    // ==================== FUNÇÕES DE DESENHO ====================
    
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
    
    function desenharElemento(elemento, isSelecionado = false) {
        ctx.save();
        
        switch(elemento.tipo) {
            case 'RETANGULO':
                // Preenchimento
                ctx.fillStyle = elemento.cor_preenchimento;
                ctx.fillRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
                
                // Borda
                ctx.lineWidth = elemento.espessura_borda;
                ctx.strokeStyle = elemento.cor_borda;
                ctx.strokeRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
                
                // Texto (identificador)
                if (elemento.identificador) {
                    ctx.fillStyle = '#000000';
                    ctx.font = 'bold 12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    
                    // Quebra texto se necessário
                    const texto = elemento.identificador;
                    const maxWidth = elemento.largura - 10;
                    ctx.fillText(texto, 
                        elemento.pos_x + elemento.largura / 2,
                        elemento.pos_y + elemento.altura / 2,
                        maxWidth
                    );
                }
                break;
                
            case 'LINHA':
                ctx.beginPath();
                ctx.lineWidth = elemento.espessura_borda;
                ctx.strokeStyle = elemento.cor_borda;
                
                // Tipo de linha
                if (elemento.linha_tipo === 'tracejada') {
                    ctx.setLineDash([5, 3]);
                } else if (elemento.linha_tipo === 'pontilhada') {
                    ctx.setLineDash([2, 2]);
                }
                
                ctx.moveTo(elemento.pos_x, elemento.pos_y);
                ctx.lineTo(elemento.pos_x + elemento.largura, elemento.pos_y + elemento.altura);
                ctx.stroke();
                ctx.setLineDash([]);
                break;
                
            case 'TEXTO':
                ctx.font = `${elemento.texto_negrito ? 'bold ' : ''}${elemento.texto_italico ? 'italic ' : ''}${elemento.fonte_tamanho}px ${elemento.fonte_nome}`;
                ctx.fillStyle = elemento.cor_preenchimento;
                ctx.textAlign = 'left';
                ctx.textBaseline = 'top';
                
                if (elemento.texto_direcao === 'vertical') {
                    ctx.save();
                    ctx.translate(elemento.pos_x, elemento.pos_y);
                    ctx.rotate(-Math.PI / 2);
                    ctx.fillText(elemento.conteudo_texto, 0, 0);
                    ctx.restore();
                } else {
                    ctx.fillText(elemento.conteudo_texto, elemento.pos_x, elemento.pos_y);
                }
                break;
        }
        
        // Borda de seleção
        if (isSelecionado) {
            ctx.strokeStyle = '#0d6efd';
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
        if (!elemento || (elemento.tipo !== 'RETANGULO' && elemento.tipo !== 'LINHA')) return;
        
        pontosControle.innerHTML = '';
        
        const pontos = [
            // Cantos
            {x: elemento.pos_x, y: elemento.pos_y, tipo: 'nw'},
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y, tipo: 'ne'},
            {x: elemento.pos_x, y: elemento.pos_y + elemento.altura, tipo: 'sw'},
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y + elemento.altura, tipo: 'se'}
        ];
        
        pontos.forEach(ponto => {
            const div = document.createElement('div');
            div.className = 'ponto-controle';
            div.style.left = ponto.x + 'px';
            div.style.top = ponto.y + 'px';
            div.dataset.tipo = ponto.tipo;
            div.style.pointerEvents = 'auto';
            div.style.cursor = 'move';
            pontosControle.appendChild(div);
        });
    }
    
    function redesenharTudo() {
        // Limpa canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Desenha grid
        desenharGrid();
        
        // Desenha todos os elementos
        elementos.forEach((elemento, index) => {
            desenharElemento(elemento, index === estado.elementoSelecionado);
        });
        
        // Desenha pontos de controle do elemento selecionado
        if (estado.elementoSelecionado !== null) {
            desenharPontosControle(elementos[estado.elementoSelecionado]);
        }
    }
    
    // ==================== FUNÇÕES DE INTERAÇÃO ====================
    
    function encontrarElementoNaPosicao(x, y) {
        // Procura do último para o primeiro (elementos mais recentes primeiro)
        for (let i = elementos.length - 1; i >= 0; i--) {
            const elemento = elementos[i];
            
            // Verifica se o ponto está dentro do elemento
            if (x >= elemento.pos_x && 
                x <= elemento.pos_x + elemento.largura && 
                y >= elemento.pos_y && 
                y <= elemento.pos_y + elemento.altura) {
                return i;
            }
        }
        return -1;
    }
    
    function encontrarPontoControle(x, y, elemento) {
        const pontos = [
            {x: elemento.pos_x, y: elemento.pos_y, tipo: 'nw'},
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y, tipo: 'ne'},
            {x: elemento.pos_x, y: elemento.pos_y + elemento.altura, tipo: 'sw'},
            {x: elemento.pos_x + elemento.largura, y: elemento.pos_y + elemento.altura, tipo: 'se'}
        ];
        
        for (const ponto of pontos) {
            const distancia = Math.sqrt(Math.pow(x - ponto.x, 2) + Math.pow(y - ponto.y, 2));
            if (distancia <= 8) { // 8px de tolerância
                return ponto.tipo;
            }
        }
        return null;
    }
    
    // ==================== EVENTOS DO MOUSE ====================
    
    canvas.addEventListener('mousedown', function(e) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        estado.inicioX = x;
        estado.inicioY = y;
        
        // Verifica se clicou em um ponto de controle
        if (estado.elementoSelecionado !== null) {
            const elemento = elementos[estado.elementoSelecionado];
            const ponto = encontrarPontoControle(x, y, elemento);
            
            if (ponto) {
                estado.redimensionando = true;
                estado.pontoRedimensionamento = ponto;
                estado.desenhando = true;
                return;
            }
        }
        
        // Verifica se clicou em um elemento
        const elementoIdx = encontrarElementoNaPosicao(x, y);
        
        if (elementoIdx !== -1) {
            // Seleciona o elemento
            estado.elementoSelecionado = elementoIdx;
            estado.offsetX = x - elementos[elementoIdx].pos_x;
            estado.offsetY = y - elementos[elementoIdx].pos_y;
            estado.desenhando = true;
            
            atualizarInterface();
        } else {
            // Cria novo elemento
            if (estado.ferramenta === 'delete') return;
            
            estado.elementoSelecionado = null;
            estado.desenhando = true;
            
            let novoElemento;
            const corPreenchimento = document.getElementById('corPreenchimento').value;
            const corBorda = document.getElementById('corBorda').value;
            const espessura = parseInt(document.getElementById('espessuraBorda').value);
            
            switch(estado.ferramenta) {
                case 'rectangle':
                    novoElemento = {
                        id: null,
                        tipo: 'RETANGULO',
                        pos_x: x,
                        pos_y: y,
                        largura: 0,
                        altura: 0,
                        cor_preenchimento: corPreenchimento,
                        cor_borda: corBorda,
                        espessura_borda: espessura,
                        conteudo_texto: '',
                        fonte_nome: 'Arial',
                        fonte_tamanho: 14,
                        texto_negrito: false,
                        texto_italico: false,
                        texto_direcao: 'horizontal',
                        linha_tipo: 'solida',
                        identificador: ''
                    };
                    break;
                    
                case 'line':
                    novoElemento = {
                        id: null,
                        tipo: 'LINHA',
                        pos_x: x,
                        pos_y: y,
                        largura: 0,
                        altura: 0,
                        cor_preenchimento: '',
                        cor_borda: corBorda,
                        espessura_borda: espessura,
                        conteudo_texto: '',
                        fonte_nome: 'Arial',
                        fonte_tamanho: 14,
                        texto_negrito: false,
                        texto_italico: false,
                        texto_direcao: 'horizontal',
                        linha_tipo: 'solida',
                        identificador: 'Linha'
                    };
                    break;
                    
                case 'text':
                    novoElemento = {
                        id: null,
                        tipo: 'TEXTO',
                        pos_x: x,
                        pos_y: y,
                        largura: 100,
                        altura: 30,
                        cor_preenchimento: corPreenchimento,
                        cor_borda: '',
                        espessura_borda: 1,
                        conteudo_texto: 'Novo Texto',
                        fonte_nome: 'Arial',
                        fonte_tamanho: parseInt(document.getElementById('tamanhoFonte').value),
                        texto_negrito: false,
                        texto_italico: false,
                        texto_direcao: 'horizontal',
                        linha_tipo: 'solida',
                        identificador: 'Texto'
                    };
                    // Habilita edição de texto
                    document.getElementById('inputTexto').value = 'Novo Texto';
                    document.getElementById('inputTexto').style.display = 'block';
                    document.getElementById('inputTexto').focus();
                    estado.modoTexto = true;
                    break;
                    
                default:
                    return;
            }
            
            elementos.push(novoElemento);
            estado.elementoSelecionado = elementos.length - 1;
            estado.modificado = true;
            
            atualizarInterface();
        }
        
        redesenharTudo();
    });
    
    canvas.addEventListener('mousemove', function(e) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Atualiza coordenadas
        document.getElementById('coordenadas').textContent = `X: ${Math.round(x)}, Y: ${Math.round(y)}`;
        
        if (!estado.desenhando) return;
        
        if (estado.elementoSelecionado !== null) {
            const elemento = elementos[estado.elementoSelecionado];
            
            if (estado.redimensionamento) {
                // Redimensionamento
                switch(estado.pontoRedimensionamento) {
                    case 'nw':
                        elemento.largura += elemento.pos_x - x;
                        elemento.altura += elemento.pos_y - y;
                        elemento.pos_x = x;
                        elemento.pos_y = y;
                        break;
                    case 'ne':
                        elemento.largura = x - elemento.pos_x;
                        elemento.altura += elemento.pos_y - y;
                        elemento.pos_y = y;
                        break;
                    case 'sw':
                        elemento.largura += elemento.pos_x - x;
                        elemento.altura = y - elemento.pos_y;
                        elemento.pos_x = x;
                        break;
                    case 'se':
                        elemento.largura = x - elemento.pos_x;
                        elemento.altura = y - elemento.pos_y;
                        break;
                }
                
                // Garante dimensões mínimas
                elemento.largura = Math.max(10, elemento.largura);
                elemento.altura = Math.max(10, elemento.altura);
            } else if (estado.ferramenta === 'select') {
                // Move elemento
                elemento.pos_x = x - estado.offsetX;
                elemento.pos_y = y - estado.offsetY;
            } else {
                // Redimensiona novo elemento
                elemento.largura = x - elemento.pos_x;
                elemento.altura = y - elemento.pos_y;
            }
            
            estado.modificado = true;
            redesenharTudo();
        }
    });
    
    canvas.addEventListener('mouseup', function() {
        if (!estado.desenhando) return;
        
        estado.desenhando = false;
        estado.redimensionando = false;
        estado.pontoRedimensionamento = null;
        
        // Ajusta dimensões negativas
        if (estado.elementoSelecionado !== null) {
            const elemento = elementos[estado.elementoSelecionado];
            
            if (elemento.largura < 0) {
                elemento.pos_x += elemento.largura;
                elemento.largura = Math.abs(elemento.largura);
            }
            if (elemento.altura < 0) {
                elemento.pos_y += elemento.altura;
                elemento.altura = Math.abs(elemento.altura);
            }
            
            // Remove elementos muito pequenos
            if (Math.abs(elemento.largura) < 5 && Math.abs(elemento.altura) < 5 && !estado.modoTexto) {
                elementos.splice(estado.elementoSelecionado, 1);
                estado.elementoSelecionado = null;
            }
            
            estado.modificado = true;
            atualizarInterface();
            redesenharTudo();
        }
    });
    
    // ==================== INTERFACE ====================
    
    function atualizarInterface() {
        // Atualiza lista de elementos
        const lista = document.getElementById('listaElementos');
        lista.innerHTML = '';
        
        elementos.forEach((elemento, index) => {
            const item = document.createElement('div');
            item.className = `list-group-item list-group-item-action elemento-item ${index === estado.elementoSelecionado ? 'active' : ''}`;
            item.dataset.index = index;
            
            const tipoIcon = {
                'RETANGULO': 'fa-square',
                'LINHA': 'fa-minus',
                'TEXTO': 'fa-font'
            }[elemento.tipo] || 'fa-shapes';
            
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div class="d-flex align-items-center">
                        <div class="me-2" style="color: ${elemento.cor_preenchimento || elemento.cor_borda};">
                            <i class="fas ${tipoIcon}"></i>
                        </div>
                        <div>
                            <strong class="${index === estado.elementoSelecionado ? 'text-white' : ''}">
                                ${elemento.identificador || 'Sem nome'}
                            </strong>
                            <div class="small ${index === estado.elementoSelecionado ? 'text-white-50' : 'text-muted'}">
                                ${elemento.tipo} • ${Math.round(elemento.pos_x)}x${Math.round(elemento.pos_y)}
                            </div>
                        </div>
                    </div>
                    <button class="btn btn-sm btn-outline-${index === estado.elementoSelecionado ? 'light' : 'danger'} btn-excluir-item" 
                            data-index="${index}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.btn-excluir-item')) {
                    estado.elementoSelecionado = index;
                    redesenharTudo();
                    atualizarInterface();
                }
            });
            
            lista.appendChild(item);
        });
        
        if (elementos.length === 0) {
            lista.innerHTML = `
                <div class="text-center py-3 text-muted">
                    <i class="fas fa-info-circle me-1"></i>
                    Nenhum elemento criado
                </div>
            `;
        }
        
        // Atualiza propriedades do elemento selecionado
        if (estado.elementoSelecionado !== null) {
            const elemento = elementos[estado.elementoSelecionado];
            document.getElementById('corPreenchimento').value = elemento.cor_preenchimento || '#CCCCCC';
            document.getElementById('corBorda').value = elemento.cor_borda || '#000000';
            document.getElementById('espessuraBorda').value = elemento.espessura_borda || 2;
            document.getElementById('espessuraValor').textContent = elemento.espessura_borda || 2;
            document.getElementById('inputIdentificador').value = elemento.identificador || '';
            
            if (elemento.tipo === 'TEXTO') {
                document.getElementById('inputTexto').value = elemento.conteudo_texto || '';
                document.getElementById('inputTexto').style.display = 'block';
                document.getElementById('tamanhoFonte').value = elemento.fonte_tamanho || 14;
            }
        }
    }
    
    // ==================== EVENTOS DA INTERFACE ====================
    
    // Ferramentas
    document.querySelectorAll('[data-tool]').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('[data-tool]').forEach(b => {
                b.classList.remove('active');
            });
            this.classList.add('active');
            estado.ferramenta = this.dataset.tool;
            
            // Mostra/oculta painel de texto
            const painelTexto = document.getElementById('painelTexto');
            painelTexto.style.display = estado.ferramenta === 'text' ? 'block' : 'none';
            
            // Altera cursor
            const cursores = {
                'select': 'default',
                'rectangle': 'crosshair',
                'line': 'crosshair',
                'text': 'text',
                'delete': 'not-allowed'
            };
            canvas.style.cursor = cursores[estado.ferramenta] || 'default';
            
            // Sai do modo texto
            estado.modoTexto = false;
            document.getElementById('inputTexto').style.display = 'none';
        });
    });
    
    // Propriedades
    document.getElementById('corPreenchimento').addEventListener('change', function() {
        if (estado.elementoSelecionado !== null) {
            elementos[estado.elementoSelecionado].cor_preenchimento = this.value;
            estado.modificado = true;
            redesenharTudo();
        }
    });
    
    document.getElementById('corBorda').addEventListener('change', function() {
        if (estado.elementoSelecionado !== null) {
            elementos[estado.elementoSelecionado].cor_borda = this.value;
            estado.modificado = true;
            redesenharTudo();
        }
    });
    
    document.getElementById('espessuraBorda').addEventListener('input', function() {
        const valor = this.value;
        document.getElementById('espessuraValor').textContent = valor;
        
        if (estado.elementoSelecionado !== null) {
            elementos[estado.elementoSelecionado].espessura_borda = parseInt(valor);
            estado.modificado = true;
            redesenharTudo();
        }
    });
    
    // Identificador
    document.getElementById('btnAplicarIdentificador').addEventListener('click', function() {
        if (estado.elementoSelecionado !== null) {
            const identificador = document.getElementById('inputIdentificador').value.trim();
            elementos[estado.elementoSelecionado].identificador = identificador;
            estado.modificado = true;
            atualizarInterface();
            redesenharTudo();
        }
    });
    
    // Texto
    document.getElementById('inputTexto').addEventListener('input', function() {
        if (estado.elementoSelecionado !== null && elementos[estado.elementoSelecionado].tipo === 'TEXTO') {
            elementos[estado.elementoSelecionado].conteudo_texto = this.value;
            estado.modificado = true;
            redesenharTudo();
        }
    });
    
    document.getElementById('tamanhoFonte').addEventListener('change', function() {
        if (estado.elementoSelecionado !== null && elementos[estado.elementoSelecionado].tipo === 'TEXTO') {
            elementos[estado.elementoSelecionado].fonte_tamanho = parseInt(this.value);
            estado.modificado = true;
            redesenharTudo();
        }
    });
    
    // Exclusão de elementos
    document.addEventListener('click', function(e) {
        if (e.target.closest('.btn-excluir-item')) {
            const btn = e.target.closest('.btn-excluir-item');
            const index = parseInt(btn.dataset.index);
            
            const modal = new bootstrap.Modal(document.getElementById('modalConfirmacao'));
            document.getElementById('modalMensagem').textContent = 
                `Excluir "${elementos[index].identificador || 'elemento'}"?`;
            
            document.getElementById('btnConfirmarExclusao').onclick = function() {
                elementos.splice(index, 1);
                if (estado.elementoSelecionado === index) {
                    estado.elementoSelecionado = null;
                } else if (estado.elementoSelecionado > index) {
                    estado.elementoSelecionado--;
                }
                estado.modificado = true;
                modal.hide();
                atualizarInterface();
                redesenharTudo();
            };
            
            modal.show();
        }
    });
    
    // Salvar
    document.getElementById('btnSalvar').addEventListener('click', async function() {
        if (!estado.modificado) {
            mostrarMensagem('Nenhuma alteração para salvar', 'warning');
            return;
        }
        
        const dados = {
            armazem_id: CONFIG.armazem.id,
            elementos: elementos.map((elemento, index) => ({
                id: elemento.id,
                tipo: elemento.tipo,
                pos_x: Math.round(elemento.pos_x),
                pos_y: Math.round(elemento.pos_y),
                largura: Math.round(elemento.largura),
                altura: Math.round(elemento.altura),
                cor_preenchimento: elemento.cor_preenchimento,
                cor_borda: elemento.cor_borda,
                espessura_borda: elemento.espessura_borda,
                conteudo_texto: elemento.conteudo_texto,
                fonte_nome: elemento.fonte_nome,
                fonte_tamanho: elemento.fonte_tamanho,
                texto_negrito: elemento.texto_negrito,
                texto_italico: elemento.texto_italico,
                texto_direcao: elemento.texto_direcao,
                linha_tipo: elemento.linha_tipo,
                identificador: elemento.identificador,
                ordem_z: index + 1
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
                mostrarMensagem('✅ Layout salvo com sucesso!', 'success');
                
                // Atualiza IDs dos elementos
                if (resultado.elementos_salvos) {
                    resultado.elementos_salvos.forEach((saved, index) => {
                        if (elementos[index]) {
                            elementos[index].id = saved.id;
                        }
                    });
                }
            } else {
                mostrarMensagem(`❌ Erro: ${resultado.error}`, 'danger');
            }
        } catch (error) {
            mostrarMensagem(`❌ Erro de conexão: ${error.message}`, 'danger');
        }
    });
    
    // Mudar armazém
    document.getElementById('selectArmazem').addEventListener('change', function() {
        if (estado.modificado && !confirm('Você tem alterações não salvas. Deseja realmente sair?')) {
            this.value = window.location.href;
            return;
        }
        window.location.href = this.value;
    });
    
    // ==================== FUNÇÕES UTILITÁRIAS ====================
    
    function mostrarMensagem(texto, tipo = 'info') {
        const alerta = document.createElement('div');
        alerta.className = `alert alert-${tipo} alert-dismissible fade show position-fixed`;
        alerta.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
        `;
        alerta.innerHTML = `
            ${texto}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alerta);
        
        setTimeout(() => {
            if (alerta.parentNode) alerta.remove();
        }, 5000);
    }
    
    // Previne saída sem salvar
    window.addEventListener('beforeunload', function(e) {
        if (estado.modificado) {
            e.preventDefault();
            e.returnValue = 'Você tem alterações não salvas. Deseja realmente sair?';
        }
    });
    
    // ==================== INICIALIZAÇÃO ====================
    
    function inicializar() {
        // Configura ferramenta inicial
        document.querySelector('[data-tool="select"]').classList.add('active');
        
        // Atualiza interface
        atualizarInterface();
        
        // Desenha elementos iniciais
        redesenharTudo();
        
        console.log('✅ Editor de Mapa inicializado com sucesso!');
    }
    
    inicializar();
});