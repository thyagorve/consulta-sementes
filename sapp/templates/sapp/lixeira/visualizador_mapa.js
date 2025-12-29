// static/sapp/js/visualizador_mapa.js
document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('meuCanvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const elementos = DADOS_VISUALIZACAO.elementos;
    
    // Função para desenhar um elemento
    function desenharElemento(elemento) {
        ctx.save();
        
        let corPreenchimento = elemento.cor_preenchimento;
        
        switch(elemento.tipo) {
            case 'RETANGULO':
                ctx.fillStyle = corPreenchimento;
                ctx.fillRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
                
                ctx.lineWidth = elemento.espessura_borda;
                ctx.strokeStyle = elemento.cor_borda;
                ctx.strokeRect(elemento.pos_x, elemento.pos_y, elemento.largura, elemento.altura);
                
                // Texto do identificador
                if (elemento.identificador) {
                    ctx.fillStyle = '#000000';
                    ctx.font = 'bold 12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    
                    // Mede o texto para ajustar
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
        
        ctx.restore();
    }
    
    // Limpa e desenha tudo
    function redesenhar() {
        // Fundo
        ctx.fillStyle = '#f8f9fa';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Desenha elementos
        elementos.forEach(desenharElemento);
    }
    
    // Inicializa
    redesenhar();
    console.log('✅ Visualizador de Mapa carregado!');
});