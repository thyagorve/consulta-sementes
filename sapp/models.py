from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal, InvalidOperation
import json  # <-- ADICIONE ESTA LINHA

# ============================================================================
# TABELAS AUXILIARES (Cadastros Básicos)
# ============================================================================

class Cultivar(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class Peneira(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class Categoria(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class Tratamento(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

class Especie(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.nome

class OrigemDestino(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nome

# ============================================================================
# ARMAZÉM E ENDEREÇOS (SIMPLIFICADO)
# ============================================================================

# models.py - Adicione/atualize

class Armazem(models.Model):
    nome = models.CharField(max_length=20, unique=True)
    def __str__(self): return self.nome

class Endereco(models.Model):
    """Model unificado de endereços - simples e funcional"""
    
    codigo = models.CharField(max_length=100, unique=True, verbose_name="Endereço completo")
    armazem = models.ForeignKey(Armazem, on_delete=models.CASCADE, related_name='enderecos', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        ordering = ['armazem__nome', 'codigo']
    
    def __str__(self):
        if self.armazem:
            return f"{self.codigo} ({self.armazem.nome})"
        return self.codigo
    

    

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    primeiro_acesso = models.BooleanField(default=True, verbose_name="Deve mudar senha?")
    def __str__(self): return f"Perfil de {self.usuario.username}"

@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        primeiro = False if instance.is_superuser else True
        PerfilUsuario.objects.create(usuario=instance, primeiro_acesso=primeiro)

class Configuracao(models.Model):
    ocultar_esgotados = models.BooleanField(default=False, verbose_name="Ocultar Lotes Esgotados")
    def save(self, *args, **kwargs):
        self.pk = 1
        super(Configuracao, self).save(*args, **kwargs)
    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

# ============================================================================
# ESTOQUE E MOVIMENTAÇÃO
# ============================================================================

class Estoque(models.Model):
    lote = models.CharField(max_length=50)
    produto = models.CharField(max_length=100, blank=True, null=True, default='')
    
    cultivar = models.ForeignKey(Cultivar, on_delete=models.PROTECT)
    peneira = models.ForeignKey(Peneira, on_delete=models.PROTECT)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    tratamento = models.ForeignKey(Tratamento, on_delete=models.SET_NULL, null=True, blank=True)
    especie = models.ForeignKey(Especie, on_delete=models.PROTECT, null=True, blank=True)
    
    endereco = models.CharField(max_length=50, verbose_name="Endereço")
    
    entrada = models.IntegerField(default=0)
    saida = models.IntegerField(default=0)
    saldo = models.IntegerField(default=0)
    empenhado = models.IntegerField(default=0, verbose_name="Quantidade Empenhada")  # ← ADICIONAR ESTA LINHA
    conferente = models.ForeignKey(User, on_delete=models.PROTECT)
    origem_destino = models.CharField(max_length=255, blank=True, null=True, default='')
    data_entrada = models.DateTimeField(auto_now_add=True)
    data_ultima_saida = models.DateTimeField(null=True, blank=True)
    data_ultima_movimentacao = models.DateTimeField(auto_now=True)
    ultimo_lote_linha = models.BooleanField(default=False, verbose_name="Último Lote da Linha")
    empresa = models.CharField(max_length=100, blank=True, null=True, default='')
    embalagem = models.CharField(max_length=10, choices=[('SC', 'Saco'), ('BAG', 'Big Bag')], default='BAG')
    peso_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    peso_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    az = models.CharField(max_length=20, blank=True, null=True, default='')
    observacao = models.TextField(blank=True, null=True, default='')
    cliente = models.CharField(max_length=255, blank=True, null=True, default='', verbose_name="Cliente/Dono do Bag")
    status = models.CharField(max_length=20, choices=[('ATIVO', 'Ativo'), ('ESGOTADO', 'Esgotado'), ('INATIVO', 'Inativo'), ('BLOQUEADO', 'Bloqueado')], default='ATIVO')
    
    status_sistemico = models.ForeignKey(
        'StatusSistemico',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estoques',
        verbose_name='Status Sistêmico'
    )
    
    status_sistemico_alterado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_sistemico_alteracoes'
    )
    status_sistemico_alterado_em = models.DateTimeField(null=True, blank=True)
    status_sistemico_observacao = models.TextField(blank=True, null=True)
    
    def get_status_display_completo(self):
        """Retorna o status com ícone e cor"""
        if self.status_sistemico:
            return {
                'id': self.status_sistemico.id,
                'nome': self.status_sistemico.nome,
                'cor': self.status_sistemico.cor,
                'icone': self.status_sistemico.icone or '',
                'legenda': self.status_sistemico.legenda or '',
            }
        return {
            'id': None,
            'nome': 'Indefinido',
            'cor': '#6c757d',
            'icone': '⚪',
            'legenda': 'Status não definido'
        }
    
    def get_status_legenda_completa(self):
        """Retorna a legenda completa para exibição no tooltip"""
        if self.status_sistemico:
            texto = f"{self.status_sistemico.icone or ''} {self.status_sistemico.nome}"
            if self.status_sistemico.legenda:
                texto += f" - {self.status_sistemico.legenda}"
            return texto
        return "⚪ Indefinido"
    
    # ← ADICIONAR ESTE MÉTODO
    @property
    def disponivel(self):
        """Saldo físico menos total empenhado ativo"""
        return self.saldo - self.empenhado
    
    # NOVO: Sobrescrever save para definir status padrão
    def save(self, *args, **kwargs):
        original = None
        if self.pk:
            try:
                original = Estoque.objects.get(pk=self.pk)
            except Estoque.DoesNotExist:
                original = None

        self.saldo = self.entrada - self.saida
        self.status = 'ESGOTADO' if self.saldo <= 0 else 'ATIVO'

        if self.peso_unitario and self.saldo:
            try:
                self.peso_total = Decimal(str(self.saldo)) * Decimal(str(self.peso_unitario))
            except:
                self.peso_total = Decimal('0.00')
        else:
            self.peso_total = Decimal('0.00')

        # Se não tiver status definido, define como Crítico (padrão)
        if not self.status_sistemico:
            try:
                status_critico = StatusSistemico.objects.get(nome='Crítico')
                self.status_sistemico = status_critico
            except StatusSistemico.DoesNotExist:
                StatusSistemico.get_status_padrao()
                try:
                    status_critico = StatusSistemico.objects.get(nome='Crítico')
                    self.status_sistemico = status_critico
                except:
                    pass

        if original and original.endereco != self.endereco and original.ultimo_lote_linha:
            self.ultimo_lote_linha = False

        super().save(*args, **kwargs)

# sapp/models.py - Adicione no final do arquivo

class StatusSistemico(models.Model):
    """Model para gerenciar status personalizados com cores"""
    nome = models.CharField(max_length=50, unique=True, verbose_name="Nome do Status")
    cor = models.CharField(max_length=20, default='#6c757d', verbose_name="Cor (Hex)")
    legenda = models.CharField(max_length=200, blank=True, null=True, verbose_name="Legenda/Descrição")
    icone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Ícone (emoji)")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    e_padrao = models.BooleanField(default=False, verbose_name="É Status Padrão")
    ordem = models.IntegerField(default=0, verbose_name="Ordem de Exibição")
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='status_criados')
    
    class Meta:
        verbose_name = "Status Sistêmico"
        verbose_name_plural = "Status Sistêmicos"
        ordering = ['ordem', 'nome']
    
    def __str__(self):
        return f"{self.icone or ''} {self.nome} ({self.cor})"
    
    @classmethod
    def get_status_padrao(cls):
        """Cria os status padrão se não existirem"""
        status_padrao = [
            {'nome': 'OK', 'cor': '#28a745', 'legenda': 'Tudo certo', 'icone': '✅', 'ordem': 1},
            {'nome': 'Parcial', 'cor': '#ffc107', 'legenda': 'Divergência identificada', 'icone': '🟡', 'ordem': 2},
            {'nome': 'Crítico', 'cor': '#dc3545', 'legenda': 'Sem saldo real', 'icone': '🔴', 'ordem': 3},
            
        ]
        
        for status_data in status_padrao:
            status, created = cls.objects.get_or_create(
                nome=status_data['nome'],
                defaults={
                    'cor': status_data['cor'],
                    'legenda': status_data['legenda'],
                    'icone': status_data['icone'],
                    'e_padrao': True,
                    'ativo': True,
                    'ordem': status_data['ordem']
                }
            )
            if created:
                print(f"✅ Status padrão criado: {status.nome}")
        
        return cls.objects.filter(ativo=True)


class HistoricoStatusSistemico(models.Model):
    """Histórico de alterações de status"""
    estoque = models.ForeignKey('Estoque', on_delete=models.CASCADE, related_name='historico_status')
    status_anterior = models.ForeignKey(StatusSistemico, on_delete=models.SET_NULL, null=True, related_name='status_anterior')
    status_novo = models.ForeignKey(StatusSistemico, on_delete=models.SET_NULL, null=True, related_name='status_novo')
    observacao = models.TextField(blank=True, null=True)
    alterado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    alterado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Histórico de Status"
        verbose_name_plural = "Históricos de Status"
        ordering = ['-alterado_em']
    
    def __str__(self):
        return f"{self.estoque.lote} - {self.status_anterior} → {self.status_novo} em {self.alterado_em.strftime('%d/%m/%Y %H:%M')}"
# sapp/models.py - Adicionar método para legenda completa

def get_status_legenda_completa(self):
    """Retorna a legenda completa para exibição no tooltip"""
    if self.status_sistemico:
        texto = f"{self.status_sistemico.icone or ''} {self.status_sistemico.nome}"
        if self.status_sistemico.legenda:
            texto += f" - {self.status_sistemico.legenda}"
        return texto
    return "⚪ Indefinido"


class HistoricoMovimentacao(models.Model):
    quantidade = models.IntegerField(default=0)
    estoque = models.ForeignKey(Estoque, on_delete=models.SET_NULL, related_name='historico', null=True, blank=True)
    lote_ref = models.CharField(max_length=100, default="--")
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50) 
    descricao = models.TextField()
    numero_carga = models.CharField(max_length=50, blank=True, null=True)
    motorista = models.CharField(max_length=100, blank=True, null=True)
    placa = models.CharField(max_length=20, blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    ordem_entrega = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta: ordering = ['-data_hora']
    
    def save(self, *args, **kwargs):
        if self.estoque: self.lote_ref = f"{self.estoque.lote}"
        super().save(*args, **kwargs)

class FotoMovimentacao(models.Model):
    historico = models.ForeignKey(HistoricoMovimentacao, related_name='fotos', on_delete=models.CASCADE)
    arquivo = models.ImageField(upload_to='historico_fotos/%Y/%m/')
    data_upload = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Foto de {self.historico}"

# ============================================================================
# MAPA E LAYOUT
# ============================================================================

class ArmazemLayout(models.Model):
    numero = models.IntegerField(unique=True, verbose_name="Número do Armazém")
    nome = models.CharField(max_length=100, default="")
    imagem_fundo = models.ImageField(upload_to='mapa_armazens/', null=True, blank=True)
    largura_canvas = models.IntegerField(default=1000)
    altura_canvas = models.IntegerField(default=600)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Layout do Armazém"
        verbose_name_plural = "Layouts dos Armazéns"
    
    def __str__(self): return f"Armazém {self.numero} - {self.nome}"

class ElementoMapa(models.Model):
    TIPO_ELEMENTO_CHOICES = [('RETANGULO', 'Retângulo/Endereço'), ('LINHA', 'Linha'), ('TEXTO', 'Texto')]
    
    armazem = models.ForeignKey(ArmazemLayout, on_delete=models.CASCADE, related_name='elementos')
    tipo = models.CharField(max_length=20, choices=TIPO_ELEMENTO_CHOICES)
    
    pos_x = models.IntegerField(default=0)
    pos_y = models.IntegerField(default=0)
    largura = models.IntegerField(default=100)
    altura = models.IntegerField(default=60)
    rotacao = models.IntegerField(default=0)
    
    cor_preenchimento = models.CharField(max_length=20, default='#CCCCCC')
    cor_borda = models.CharField(max_length=20, default='#000000')
    espessura_borda = models.IntegerField(default=2)
    
    conteudo_texto = models.TextField(blank=True, null=True)
    fonte_nome = models.CharField(max_length=100, default='Arial')
    fonte_tamanho = models.IntegerField(default=14)
    texto_negrito = models.BooleanField(default=False)
    texto_italico = models.BooleanField(default=False)
    texto_direcao = models.CharField(max_length=20, default='horizontal', choices=[('horizontal', 'Horizontal'), ('vertical', 'Vertical')])
    
    linha_tipo = models.CharField(max_length=20, default='solida', choices=[('solida', 'Sólida'), ('tracejada', 'Tracejada'), ('pontilhada', 'Pontilhada')])
    identificador = models.CharField(max_length=50, blank=True, null=True)
    ordem_z = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = "Elemento do Mapa"
        verbose_name_plural = "Elementos do Mapa"
        ordering = ['armazem', 'ordem_z']
    
    def __str__(self): return f"{self.get_tipo_display()} - {self.identificador or 'Sem ID'}"

# ============================================================================
# SISTEMA DE EMPENHO
# ============================================================================

class EmpenhoStatus(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True, null=True)
    def __str__(self): return self.nome

class Empenho(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    status = models.ForeignKey(EmpenhoStatus, on_delete=models.PROTECT, default=1)
    tipo_movimentacao = models.CharField(max_length=20, choices=[('EXPEDICAO', 'Expedição'), ('TRANSFERENCIA', 'Transferência'), ('EDICAO', 'Edição'), ('ENTRADA', 'Entrada')], default='EXPEDICAO')
    observacao = models.TextField(blank=True, null=True)
    numero_carga = models.CharField(max_length=50, blank=True, null=True)
    motorista = models.CharField(max_length=100, blank=True, null=True)
    placa = models.CharField(max_length=20, blank=True, null=True)
    cliente = models.CharField(max_length=255, blank=True, null=True)
    ordem_entrega = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta: ordering = ['-data_criacao']
    
    def __str__(self): return f"Empenho #{self.id} - {self.usuario.username}"
    
    @property
    def total_itens(self): return self.itens.count()
    
    @property
    def saldo_afetado(self): return sum(item.quantidade for item in self.itens.all())

class ItemEmpenho(models.Model):
    empenho = models.ForeignKey(Empenho, on_delete=models.CASCADE, related_name='itens')
    estoque = models.ForeignKey(Estoque, on_delete=models.CASCADE, related_name='empenhos')
    quantidade = models.IntegerField(default=0)
    endereco_origem = models.CharField(max_length=20)
    endereco_destino = models.CharField(max_length=20, blank=True, null=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)
    lote = models.CharField(max_length=50)
    cultivar = models.CharField(max_length=100)
    peneira = models.CharField(max_length=50)
    categoria = models.CharField(max_length=50)
    saldo_anterior = models.IntegerField(default=0)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta: 
        ordering = ['-data_criacao']
        unique_together = ['empenho', 'estoque']

    def __str__(self): return f"{self.lote} - {self.quantidade} unidades"
    
    # ← SUBSTITUIR ESTE MÉTODO
    def save(self, *args, **kwargs):
        from django.db import transaction
        
        is_new = self.pk is None
        old_quantidade = 0
        
        if not is_new:
            try:
                old = ItemEmpenho.objects.get(pk=self.pk)
                old_quantidade = old.quantidade
            except ItemEmpenho.DoesNotExist:
                pass
        
        # Preencher dados do estoque se necessário
        if self.estoque:
            if not self.lote:
                self.lote = self.estoque.lote
            if not self.cultivar:
                self.cultivar = self.estoque.cultivar.nome if self.estoque.cultivar else ''
            if not self.peneira:
                self.peneira = self.estoque.peneira.nome if self.estoque.peneira else ''
            if not self.categoria:
                self.categoria = self.estoque.categoria.nome if self.estoque.categoria else ''
            if not self.saldo_anterior:
                self.saldo_anterior = self.estoque.saldo
            if not self.endereco_origem:
                self.endereco_origem = self.estoque.endereco
        
        with transaction.atomic():
            # Bloquear o estoque para evitar concorrência
            if self.estoque:
                estoque = Estoque.objects.select_for_update().get(pk=self.estoque.pk)
                
                # Calcular quanto vai mudar no empenhado
                delta = self.quantidade - old_quantidade
                
                # Validar se não ultrapassa o saldo físico
                novo_empenhado = estoque.empenhado + delta
                if novo_empenhado > estoque.saldo:
                    raise ValueError(
                        f"Saldo insuficiente para o lote {estoque.lote}. "
                        f"Disponível: {estoque.saldo - estoque.empenhado}, "
                        f"Tentando empenhar: {self.quantidade}"
                    )
                
                # Atualizar empenhado no estoque
                estoque.empenhado = novo_empenhado
                estoque.save(update_fields=['empenhado'])
            
            super().save(*args, **kwargs)
    
    # ← ADICIONAR ESTE MÉTODO
    def delete(self, *args, **kwargs):
        """Libera a reserva ao excluir um item empenhado"""
        from django.db import transaction
        
        with transaction.atomic():
            if self.estoque:
                estoque = Estoque.objects.select_for_update().get(pk=self.estoque.pk)
                estoque.empenhado = max(0, estoque.empenhado - self.quantidade)
                estoque.save(update_fields=['empenhado'])
            
            super().delete(*args, **kwargs)
    
    @property
    def saldo_disponivel(self): return self.estoque.saldo - self.quantidade

    ##===========================================================================
# PRODUTO
# ============================================================================

# sapp/models.py - Classe Produto CORRIGIDA

# No início de models.py
from django.conf import settings
from django.db import models


class HistoricoItemEmpenho(models.Model):
    """
    Preserva os dados dos itens de um card que já foram
    transferidos ou expedidos.

    Esses registros não entram no cálculo de quantidade empenhada.
    Eles são utilizados para auditoria, consulta e impressão.
    """

    TIPO_TRANSFERENCIA = 'transferencia'
    TIPO_EXPEDICAO = 'expedicao'

    TIPO_CHOICES = [
        (TIPO_TRANSFERENCIA, 'Transferência'),
        (TIPO_EXPEDICAO, 'Expedição'),
    ]

    empenho = models.ForeignKey(
        'Empenho',
        on_delete=models.PROTECT,
        related_name='historico_itens',
        verbose_name='Card de empenho',
    )

    item_empenho_id_original = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='ID do ItemEmpenho removido após o processamento.',
    )

    estoque_origem = models.ForeignKey(
        'Estoque',
        on_delete=models.PROTECT,
        related_name='historicos_itens_origem',
    )

    estoque_destino = models.ForeignKey(
        'Estoque',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='historicos_itens_destino',
    )

    # Cópia dos dados no momento do processamento.
    # Isso evita que alterações futuras no estoque modifiquem a impressão antiga.
    lote = models.CharField(
        max_length=100,
        db_index=True,
    )

    produto = models.CharField(
        max_length=255,
        blank=True,
        default='',
    )

    cultivar = models.CharField(
        max_length=255,
        blank=True,
        default='',
    )

    peneira = models.CharField(
        max_length=100,
        blank=True,
        default='',
    )

    categoria = models.CharField(
        max_length=100,
        blank=True,
        default='',
    )

    tratamento = models.CharField(
        max_length=255,
        blank=True,
        default='',
    )

    especie = models.CharField(
        max_length=100,
        blank=True,
        default='',
    )

    embalagem = models.CharField(
        max_length=100,
        blank=True,
        default='',
    )

    empresa = models.CharField(
        max_length=255,
        blank=True,
        default='',
    )

    cliente = models.CharField(
        max_length=255,
        blank=True,
        default='',
    )

    endereco_origem = models.CharField(
        max_length=100,
        blank=True,
        default='',
    )

    endereco_destino = models.CharField(
        max_length=100,
        blank=True,
        default='',
    )

    quantidade = models.PositiveIntegerField()

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        db_index=True,
    )

    observacao = models.TextField(
        blank=True,
        default='',
    )

    numero_carga = models.CharField(
        max_length=100,
        blank=True,
        default='',
    )

    placa = models.CharField(
        max_length=20,
        blank=True,
        default='',
    )

    processado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='historicos_itens_empenhados_processados',
    )

    processado_em = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'Histórico de item empenhado'
        verbose_name_plural = 'Históricos de itens empenhados'
        ordering = ['-processado_em', '-id']

        indexes = [
            models.Index(
                fields=['empenho', '-processado_em'],
                name='hist_emp_data_idx',
            ),
            models.Index(
                fields=['estoque_origem', '-processado_em'],
                name='hist_origem_data_idx',
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade__gt=0),
                name='hist_item_quantidade_maior_zero',
            ),
        ]

    def __str__(self):
        data = (
            self.processado_em.strftime('%d/%m/%Y %H:%M')
            if self.processado_em
            else 'não processado'
        )

        return (
            f'{self.lote} - {self.quantidade} un - '
            f'{self.get_tipo_display()} em {data}'
        )

    @property
    def foi_transferido(self):
        return self.tipo == self.TIPO_TRANSFERENCIA

    @property
    def foi_expedido(self):
        return self.tipo == self.TIPO_EXPEDICAO


class Produto(models.Model):
    cultivar = models.ForeignKey(Cultivar, on_delete=models.PROTECT, verbose_name="Cultivar")
    tipo = models.CharField(max_length=50, verbose_name="Tipo", blank=True, null=True)
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código do Produto")
    descricao = models.TextField(verbose_name="Descrição")
    peneira = models.ForeignKey(Peneira, on_delete=models.PROTECT, verbose_name="Peneira", blank=True, null=True)
    empresa = models.CharField(max_length=100, verbose_name="Empresa", blank=True, null=True)
    especie = models.ForeignKey(Especie, on_delete=models.PROTECT, verbose_name="Espécie", blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, verbose_name="Categoria", blank=True, null=True)
    tratamento = models.ForeignKey(Tratamento, on_delete=models.PROTECT, verbose_name="Tratamento", blank=True, null=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['cultivar__nome', 'codigo']
        permissions = [
            ("pode_ver_estoque", "Pode visualizar estoque"),
            ("pode_movimentar_estoque", "Pode movimentar estoque"),
            ("pode_ver_dashboard", "Pode acessar o dashboard"),
            ("pode_ver_almoxarifado", "Pode visualizar almoxarifado"),
            ("pode_gerenciar_almoxarifado", "Pode gerenciar almoxarifado"),
            ("pode_ver_empenhos", "Pode visualizar empenhos"),
            ("pode_criar_empenhos", "Pode criar empenhos"),
            ("pode_ver_mapa", "Pode acessar mapa canvas"),
            ("pode_gerenciar_usuarios", "Pode gerenciar usuários"),
            ("pode_configuracoes", "Pode alterar configurações"),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.cultivar.nome}"
    
    def info_completa(self):
        info = []
        if self.tipo: info.append(f"Tipo: {self.tipo}")
        if self.peneira: info.append(f"Peneira: {self.peneira.nome}")
        if self.empresa: info.append(f"Empresa: {self.empresa}")
        if self.especie: info.append(f"Espécie: {self.especie.nome}")
        if self.categoria: info.append(f"Categoria: {self.categoria.nome}")
        if self.tratamento: info.append(f"Tratamento: {self.tratamento.nome}")
        return " | ".join(info)
# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardConfig(models.Model):
    TIPO_GRAFICO_CHOICES = [
        ('doughnut', 'Rosca (Doughnut)'),
        ('pie', 'Pizza (Pie)'),
        ('bar', 'Barras'),
        ('horizontalBar', 'Barras Horizontais'),
        ('line', 'Linha'),
        ('area', 'Área'),
    ]
    
    ORDEM_CHOICES = [
        ('valor_desc', 'Maior Valor'),
        ('valor_asc', 'Menor Valor'),
        ('nome_asc', 'Nome (A-Z)'),
        ('nome_desc', 'Nome (Z-A)'),
    ]
    
    PERIODO_CHOICES = [
        (7, 'Últimos 7 dias'),
        (15, 'Últimos 15 dias'),
        (30, 'Últimos 30 dias'),
        (90, 'Últimos 90 dias'),
    ]
    
    cultivar_tipo = models.CharField(max_length=20, choices=TIPO_GRAFICO_CHOICES, default='doughnut')
    cultivar_qtd = models.IntegerField(default=10)
    cultivar_ordem = models.CharField(max_length=20, choices=ORDEM_CHOICES, default='valor_desc')
    cultivar_zerados = models.BooleanField(default=False)
    cultivar_agrupar_outros = models.BooleanField(default=True)
    
    peneira_tipo = models.CharField(max_length=20, choices=TIPO_GRAFICO_CHOICES, default='pie')
    peneira_qtd = models.IntegerField(default=8)
    peneira_ordem = models.CharField(max_length=20, choices=ORDEM_CHOICES, default='valor_desc')
    
    armazem_tipo = models.CharField(max_length=20, choices=TIPO_GRAFICO_CHOICES, default='bar')
    armazem_ordem = models.CharField(max_length=20, choices=ORDEM_CHOICES, default='nome_asc')
    armazem_metrica = models.CharField(max_length=20, choices=[
        ('volume', 'Volume (SC)'),
        ('lotes', 'Quantidade de Lotes'),
        ('peso', 'Peso Total (kg)'),
    ], default='volume')
    
    tendencia_periodo = models.IntegerField(choices=PERIODO_CHOICES, default=7)
    tendencia_saidas = models.BooleanField(default=True)
    tendencia_transferencias = models.BooleanField(default=False)
    tendencia_agrupamento = models.CharField(max_length=10, choices=[
        ('day', 'Por Dia'),
        ('week', 'Por Semana'),
        ('month', 'Por Mês'),
    ], default='day')
    
    auto_refresh = models.IntegerField(default=0)
    unidade_padrao = models.CharField(max_length=10, choices=[
        ('sc', 'Sacas (SC)'),
        ('bags', 'Bags'),
        ('kg', 'Quilogramas (kg)'),
    ], default='sc')
    
    tema_cores = models.CharField(max_length=20, choices=[
        ('default', 'Padrão (Verde)'),
        ('modern', 'Moderno (Azul)'),
        ('pastel', 'Pastel'),
        ('dark', 'Escuro'),
    ], default='default')
    
    mostrar_legendas = models.BooleanField(default=True)
    mostrar_percentuais = models.BooleanField(default=True)
    
    filtro_cultivar = models.BooleanField(default=True)
    filtro_peneira = models.BooleanField(default=True)
    filtro_armazem = models.BooleanField(default=True)
    filtro_periodo = models.BooleanField(default=True)
    
    layout_config = models.TextField(default='{}')
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dashboard_configs')
    
    class Meta:
        verbose_name = "Configuração do Dashboard"
        verbose_name_plural = "Configurações do Dashboard"
        unique_together = ['criado_por']
    
    def __str__(self):
        return f"Dashboard Config - {self.criado_em.strftime('%d/%m/%Y %H:%M')}"
    
    def get_layout_config(self):
        try:
            return json.loads(self.layout_config)
        except:
            return {}
    
    def set_layout_config(self, config_dict):
        self.layout_config = json.dumps(config_dict)

class DashboardFiltroSalvo(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, null=True)
    filtros = models.TextField()
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='filtros_salvos')
    compartilhado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Filtro Salvo"
        verbose_name_plural = "Filtros Salvos"
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.nome} - {self.usuario.username}"
    
    def get_filtros(self):
        try:
            return json.loads(self.filtros)
        except:
            return {}

class DashboardWidget(models.Model):
    TIPO_WIDGET_CHOICES = [
        ('grafico', 'Gráfico'),
        ('tabela', 'Tabela'),
        ('kpi', 'Indicador KPI'),
        ('lista', 'Lista'),
    ]
    
    ORIGEM_DADOS_CHOICES = [
        ('cultivares', 'Top Cultivares'),
        ('peneiras', 'Distribuição por Peneira'),
        ('armazens', 'Ocupação por Armazém'),
        ('tendencia', 'Tendência de Movimentação'),
        ('estoque_resumo', 'Resumo do Estoque'),
        ('ultimas_mov', 'Últimas Movimentações'),
        ('clientes_top', 'Top Clientes'),
        ('produtos_top', 'Top Produtos'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_WIDGET_CHOICES)
    origem_dados = models.CharField(max_length=30, choices=ORIGEM_DADOS_CHOICES)
    
    titulo = models.CharField(max_length=200, blank=True)
    subtitulo = models.CharField(max_length=200, blank=True)
    
    pos_x = models.IntegerField(default=0)
    pos_y = models.IntegerField(default=0)
    largura = models.IntegerField(default=6)
    altura = models.IntegerField(default=4)
    
    config = models.TextField(default='{}')
    
    ativo = models.BooleanField(default=True)
    visivel_para_todos = models.BooleanField(default=False)
    usuarios_permitidos = models.ManyToManyField(User, blank=True, related_name='widgets_permitidos')
    
    ordem = models.IntegerField(default=0)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='widgets_criados')
    
    class Meta:
        verbose_name = "Widget do Dashboard"
        verbose_name_plural = "Widgets do Dashboard"
        ordering = ['ordem', 'pos_y', 'pos_x']
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"
    
    def get_config(self):
        try:
            return json.loads(self.config)
        except:
            return {}

# ============================================================================
# CONFIGURAÇÃO DE LOGO
# ============================================================================

class ConfiguracaoLogo(models.Model):
    logo = models.ImageField(upload_to='logos/', null=True, blank=True, verbose_name="Logo da Empresa")
    nome_empresa = models.CharField(max_length=100, default='GRUPO CONCEITO', verbose_name="Nome da Empresa")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Atualizado por")
    
    class Meta:
        verbose_name = "Configuração da Logo"
        verbose_name_plural = "Configurações da Logo"
    
    def save(self, *args, **kwargs):
        if self.ativo:
            ConfiguracaoLogo.objects.filter(ativo=True).exclude(pk=self.pk).update(ativo=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_logo(cls):
        try:
            return cls.objects.get(ativo=True)
        except cls.DoesNotExist:
            return None
        except cls.MultipleObjectsReturned:
            primeira = cls.objects.filter(ativo=True).first()
            cls.objects.filter(ativo=True).exclude(pk=primeira.pk).update(ativo=False)
            return primeira
        




# ============================================================================
# FASE 2 - SISTEMA DE SOLICITAÇÃO E KANBAN
# ============================================================================

class Solicitacao(models.Model):
    """
    Representa uma solicitação/card no sistema.
    Separado do Empenho para ter critérios próprios e fluxo independente.
    """
    UNIDADE_CHOICES = [
        ('EMBALAGEM', 'Embalagem'),
        ('QUILOGRAMA', 'Quilograma'),
    ]
    
    PRIORIDADE_CHOICES = [
        ('BAIXA', 'Baixa'),
        ('MEDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('URGENTE', 'Urgente'),
    ]
    
    # Identificação
    titulo = models.CharField(max_length=100, verbose_name="Título do Card")
    criador = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        related_name='solicitacoes_criadas',
        verbose_name="Usuário criador"
    )
    
    # Critérios da solicitação
    armazem = models.ForeignKey(
        'Armazem', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        verbose_name="Armazém"
    )
    produto = models.CharField(max_length=100, blank=True, null=True, verbose_name="Produto")
    especie = models.ForeignKey(
        'Especie', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        verbose_name="Espécie"
    )
    cliente = models.CharField(max_length=255, blank=True, null=True, verbose_name="Cliente")
    
    # Controle de quantidade
    unidade_controle = models.CharField(
        max_length=20, 
        choices=UNIDADE_CHOICES, 
        default='EMBALAGEM',
        verbose_name="Unidade de Controle"
    )
    quantidade_solicitada = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Quantidade Solicitada"
    )
    quantidade_empenhada = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Quantidade Empenhada"
    )
    quantidade_movimentada = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name="Quantidade Movimentada"
    )
    
    # Metadados
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    responsavel = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='solicitacoes_responsavel',
        verbose_name="Responsável"
    )
    prioridade = models.CharField(
        max_length=10, 
        choices=PRIORIDADE_CHOICES, 
        default='MEDIA',
        verbose_name="Prioridade"
    )
    
    # Status e Kanban
    status = models.CharField(
        max_length=30, 
        default='AGUARDANDO_EMPENHO',
        verbose_name="Status da Solicitação"
    )
    coluna_kanban = models.ForeignKey(
        'ColunaKanban', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='solicitacoes',
        verbose_name="Coluna do Kanban"
    )
    
    # Datas
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Solicitação"
        verbose_name_plural = "Solicitações"
        ordering = ['-data_criacao']
        permissions = [
            ("pode_criar_solicitacao", "Pode criar solicitação"),
            ("pode_empenhar_solicitacao", "Pode empenhar itens em solicitação"),
            ("pode_movimentar_solicitacao", "Pode transferir/expedir solicitação"),
            ("pode_cancelar_solicitacao", "Pode cancelar solicitação"),
        ]
    
    def __str__(self):
        return f"Solicitação #{self.id} - {self.titulo}"
    
    @property
    def percentual_empenhado(self):
        """Percentual da quantidade já empenhada"""
        if self.quantidade_solicitada > 0:
            return (self.quantidade_empenhada / self.quantidade_solicitada) * 100
        return 0
    
    @property
    def percentual_movimentado(self):
        """Percentual da quantidade já movimentada"""
        if self.quantidade_solicitada > 0:
            return (self.quantidade_movimentada / self.quantidade_solicitada) * 100
        return 0
    
    @property
    def quantidade_pendente_empenho(self):
        """Quanto ainda falta empenhar"""
        return max(0, self.quantidade_solicitada - self.quantidade_empenhada)
    
    @property
    def quantidade_pendente_movimentacao(self):
        """Quanto ainda falta movimentar"""
        return max(0, self.quantidade_solicitada - self.quantidade_movimentada)

   # No arquivo sapp/models.py, dentro da classe Solicitacao
    @property
    def quantidade_empenhada_kg(self):
        if self.unidade_controle != 'QUILOGRAMA':
            return None
        empenho = Empenho.objects.filter(
            observacao=self.titulo, status__nome='Rascunho'
        ).first()
        if not empenho:
            return Decimal('0')
        total = Decimal('0')
        for item in empenho.itens.select_related('estoque'):
            peso = item.estoque.peso_unitario or Decimal('0')
            total += Decimal(str(item.quantidade)) * peso
        return total


class ColunaKanban(models.Model):
    """Colunas do quadro Kanban"""
    nome = models.CharField(max_length=50, verbose_name="Nome da Coluna")
    cor = models.CharField(max_length=20, default='#6c757d', verbose_name="Cor")
    ordem = models.IntegerField(default=0, verbose_name="Ordem")
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    
    class Meta:
        verbose_name = "Coluna Kanban"
        verbose_name_plural = "Colunas Kanban"
        ordering = ['ordem', 'nome']
    
    def __str__(self):
        return self.nome
    
    @classmethod
    def criar_colunas_padrao(cls):
        """Cria as colunas padrão se não existirem"""
        colunas = [
            {'nome': 'Início', 'cor': '#6c757d', 'ordem': 1},
            {'nome': 'Meio', 'cor': '#ffc107', 'ordem': 2},
            {'nome': 'Fim', 'cor': '#28a745', 'ordem': 3},
        ]
        for col in colunas:
            cls.objects.get_or_create(
                nome=col['nome'],
                defaults={'cor': col['cor'], 'ordem': col['ordem']}
            )


class RegraWorkflow(models.Model):
    """Regras automáticas do Kanban"""
    EVENTO_CHOICES = [
        ('CRIACAO', 'Solicitação Criada'),
        ('PRIMEIRO_EMPENHO', 'Primeiro Item Empenhado'),
        ('EMPENHO_PARCIAL', 'Empenho Parcial'),
        ('EMPENHO_COMPLETO', 'Volume Totalmente Empenhado'),
        ('PRIMEIRA_MOVIMENTACAO', 'Primeira Movimentação'),
        ('MOVIMENTACAO_PARCIAL', 'Movimentação Parcial'),
        ('TRANSFERENCIA_COMPLETA', 'Transferência Completa'),
        ('EXPEDICAO_COMPLETA', 'Expedição Completa'),
        ('CONCLUSAO', 'Conclusão'),
        ('CANCELAMENTO', 'Cancelamento'),
        ('MOVIMENTACAO_MANUAL', 'Movimentação Manual'),
    ]
    
    coluna = models.ForeignKey(
        ColunaKanban, 
        on_delete=models.CASCADE, 
        related_name='regras',
        verbose_name="Coluna"
    )
    evento = models.CharField(max_length=30, choices=EVENTO_CHOICES, verbose_name="Evento")
    status_resultante = models.CharField(max_length=30, verbose_name="Status Resultante")
    movimentacao_automatica = models.BooleanField(
        default=True, 
        verbose_name="Movimentação Automática"
    )
    
    class Meta:
        verbose_name = "Regra de Workflow"
        verbose_name_plural = "Regras de Workflow"
        unique_together = ['coluna', 'evento']
    
    def __str__(self):
        return f"{self.coluna.nome} - {self.get_evento_display()}"


class HistoricoCard(models.Model):
    """Registro de alterações nos cards (feed de atualizações)"""
    ACAO_CHOICES = [
        ('CRIACAO', 'criou a solicitação'),
        ('EMPENHO', 'empenhou'),
        ('TRANSFERENCIA', 'transferiu'),
        ('EXPEDICAO', 'expediu'),
        ('CANCELAMENTO', 'cancelou'),
        ('MOVIMENTACAO_KANBAN', 'moveu o card'),
        ('REMOCAO_ITEM', 'removeu item'),
        ('CONCLUSAO', 'concluiu'),
    ]
    
    solicitacao = models.ForeignKey(
        Solicitacao, 
        on_delete=models.CASCADE, 
        related_name='historico',
        verbose_name="Solicitação"
    )
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Usuário")
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES, verbose_name="Ação")
    lote = models.CharField(max_length=50, blank=True, null=True, verbose_name="Lote")
    quantidade = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name="Quantidade"
    )
    unidade = models.CharField(max_length=10, blank=True, null=True, verbose_name="Unidade")
    coluna_anterior = models.CharField(max_length=50, blank=True, null=True, verbose_name="Coluna Anterior")
    coluna_nova = models.CharField(max_length=50, blank=True, null=True, verbose_name="Nova Coluna")
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")
    data = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")
    
    class Meta:
        verbose_name = "Histórico do Card"
        verbose_name_plural = "Históricos dos Cards"
        ordering = ['-data']
    
    def __str__(self):
        return f"{self.usuario.username} {self.get_acao_display()} - {self.solicitacao.titulo}"
    
    def descricao_completa(self):
        partes = [self.usuario.get_full_name() or self.usuario.username, self.get_acao_display()]
        if self.lote:
            partes.append(f"lote {self.lote}")
        if self.quantidade:
            partes.append(f"{self.quantidade} {self.unidade or 'un'}")
        
        # 👇 ALTERE AQUI
        nome_card = self.solicitacao.titulo if self.solicitacao else f"Card {self.solicitacao_id}"
        partes.append(f'no card "{nome_card}"')
        
        if self.coluna_anterior and self.coluna_nova:
            partes.append(f"de '{self.coluna_anterior}' para '{self.coluna_nova}'")
        return ' '.join(partes)

class ConfiguracaoAtualizacao(models.Model):
    """Preferências individuais de atualização"""
    usuario = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='config_atualizacao',
        verbose_name="Usuário"
    )
    som_ativo = models.BooleanField(default=True, verbose_name="Som Ativo")
    volume = models.IntegerField(default=50, verbose_name="Volume (0-100)")
    intervalo_atualizacao = models.IntegerField(default=30, verbose_name="Intervalo (segundos)")
    
    class Meta:
        verbose_name = "Configuração de Atualização"
        verbose_name_plural = "Configurações de Atualização"
    
    def __str__(self):
        return f"Config de {self.usuario.username}"


