from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.contrib import messages
from .models import Estoque, HistoricoMovimentacao
from .forms import NovaEntradaForm, TransferenciaForm, EdicaoForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.contrib import messages
from .models import Estoque, HistoricoMovimentacao, Configuracao, Cultivar, Peneira, Categoria
from .forms import NovaEntradaForm, ConfiguracaoForm, CultivarForm, PeneiraForm, CategoriaForm
from decimal import Decimal, InvalidOperation # <--- Adicione isso no topo
from django.http import JsonResponse

@login_required
def dashboard(request):
    """
    Renderiza a tela inicial. 
    Como removemos os modelos, não passamos nenhum contexto de dados.
    """
    return render(request, 'sapp/dashboard.html') 

def logout_view(request):
    """
    Realiza o logout e redireciona para o login.
    Aceita POST (padrão recomendado) ou GET se necessário.
    """
    logout(request)
    return redirect('sapp:login')



#########################################################################
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash

# --- IMPORTAÇÃO CORRIGIDA (Sem Conferente) ---
from .models import Estoque, HistoricoMovimentacao, Configuracao, Cultivar, Peneira, Categoria, Tratamento, PerfilUsuario
from .forms import (NovaEntradaForm, ConfiguracaoForm, CultivarForm, PeneiraForm, CategoriaForm, 
                    TratamentoForm, NovoConferenteUserForm, MudarSenhaForm)

@login_required
def mudar_senha(request):
    if request.method == 'POST':
        form = MudarSenhaForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['nova_senha'])
            request.user.save()
            try:
                # Atualiza perfil se existir
                perfil = request.user.perfil
                perfil.primeiro_acesso = False
                perfil.save()
            except: pass
            
            update_session_auth_hash(request, request.user)
            messages.success(request, "Senha atualizada com sucesso!")
            return redirect('sapp:lista_estoque')
    else:
        form = MudarSenhaForm()
    return render(request, 'sapp/mudar_senha.html', {'form': form})

@login_required
def lista_estoque(request):
    termo = request.GET.get('busca', '')
    config = Configuracao.get_solo()
    itens = Estoque.objects.all().order_by('-id')

    if config.ocultar_esgotados:
        itens = itens.filter(saldo__gt=0)

    if termo:
        itens = itens.filter(
            Q(lote__icontains=termo) | 
            Q(cultivar__nome__icontains=termo) | 
            Q(endereco__icontains=termo)
        )

    total_bag = itens.filter(embalagem='BAG').aggregate(saldo=Sum('saldo'))['saldo'] or 0
    total_sc_fisico = itens.filter(embalagem='SC').aggregate(saldo=Sum('saldo'))['saldo'] or 0
    total_sc_convertido = (total_bag * 25) + total_sc_fisico

    context = {
        'itens': itens,
        'total_bag': total_bag,
        'total_sc': total_sc_convertido,
        'form_entrada': NovaEntradaForm(),
        'all_cultivares': Cultivar.objects.all(),
        'all_peneiras': Peneira.objects.all(),
        'all_categorias': Categoria.objects.all(),
        'all_tratamentos': Tratamento.objects.all(),
        # Conferentes agora são usuários, não passamos lista aqui para edição manual
    }
    return render(request, 'sapp/tabela_estoque.html', context)

@login_required
def nova_entrada(request):
    if request.method == 'POST':
        form = NovaEntradaForm(request.POST)
        if form.is_valid():
            novo_obj = form.save(commit=False)
            novo_obj.conferente = request.user # Automático
            
            lote_existente = Estoque.objects.filter(
                lote=novo_obj.lote,
                endereco=novo_obj.endereco,
                cultivar=novo_obj.cultivar,
                peneira=novo_obj.peneira,
                categoria=novo_obj.categoria,
                tratamento=novo_obj.tratamento,
                embalagem=novo_obj.embalagem,
                empresa=novo_obj.empresa
            ).first()

            if lote_existente:
                lote_existente.entrada += novo_obj.entrada
                lote_existente.conferente = request.user
                lote_existente.save()
                HistoricoMovimentacao.objects.create(
                    estoque=lote_existente, 
                    usuario=request.user, 
                    tipo='Entrada (Soma)',
                    descricao=f"Adicionado <b>{novo_obj.entrada}</b> unid. (Saldo atual: {lote_existente.saldo})"
                )
                messages.success(request, "Lote existente somado!")
            else:
                novo_obj.save()
                HistoricoMovimentacao.objects.create(
                    estoque=novo_obj, 
                    usuario=request.user, 
                    tipo='Entrada Inicial',
                    descricao=f"Entrada de <b>{novo_obj.entrada}</b> no endereço <b>{novo_obj.endereco}</b>."
                )
                messages.success(request, "Novo lote criado!")
        else:
            messages.error(request, "Erro no formulário.")
    return redirect('sapp:lista_estoque')

@login_required
def transferir(request, id):
    item_origem = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            qtd = int(request.POST.get('quantidade'))
            novo_end = request.POST.get('novo_endereco')
            
            if qtd <= 0 or qtd > item_origem.saldo:
                messages.error(request, "Quantidade inválida.")
                return redirect('sapp:lista_estoque')

            item_origem.saida += qtd
            item_origem.save()
            
            HistoricoMovimentacao.objects.create(
                estoque=item_origem,
                usuario=request.user,
                tipo='Transf. (Saída)',
                descricao=f"Enviado <b>{qtd}</b> para <b>{novo_end}</b>."
            )

            item_destino = Estoque.objects.filter(
                lote=item_origem.lote,
                endereco=novo_end,
                cultivar=item_origem.cultivar,
                peneira=item_origem.peneira,
                categoria=item_origem.categoria,
                tratamento=item_origem.tratamento,
                embalagem=item_origem.embalagem,
                empresa=item_origem.empresa
            ).first()

            if item_destino:
                item_destino.entrada += qtd
                item_destino.conferente = request.user
                item_destino.save()
                HistoricoMovimentacao.objects.create(
                    estoque=item_destino,
                    usuario=request.user,
                    tipo='Transf. (Entrada/Soma)',
                    descricao=f"Recebido <b>{qtd}</b> de <b>{item_origem.endereco}</b>."
                )
            else:
                novo_item = Estoque.objects.create(
                    lote=item_origem.lote, cultivar=item_origem.cultivar, peneira=item_origem.peneira, 
                    categoria=item_origem.categoria, az=item_origem.az, endereco=novo_end, 
                    entrada=qtd, saida=0, origem_destino=f"Transf. de {item_origem.endereco}", 
                    conferente=request.user, 
                    especie=item_origem.especie, empresa=item_origem.empresa, 
                    embalagem=item_origem.embalagem, peso_unitario=item_origem.peso_unitario, 
                    tratamento=item_origem.tratamento
                )
                HistoricoMovimentacao.objects.create(
                    estoque=novo_item,
                    usuario=request.user,
                    tipo='Transf. (Entrada)',
                    descricao=f"Recebido <b>{qtd}</b> de <b>{item_origem.endereco}</b>."
                )
            
            messages.success(request, "Transferência realizada!")
        except Exception as e:
            messages.error(request, f"Erro: {e}")

    return redirect('sapp:lista_estoque')

@login_required
def editar(request, id):
    item = get_object_or_404(Estoque, id=id)
    
    if request.method == 'POST':
        try:
            # 1. CAPTURA O ESTADO ANTIGO (Para comparação)
            antigo_lote = item.lote
            antigo_endereco = item.endereco
            antigo_empresa = item.empresa
            antigo_od = item.origem_destino
            antigo_peso = item.peso_unitario
            antigo_emb = item.embalagem
            antigo_az = item.az or ""
            antigo_obs = item.observacao or ""
            
            # Para FKs, pegamos o NOME para ficar legível no histórico
            antigo_cultivar = item.cultivar.nome
            antigo_peneira = item.peneira.nome
            antigo_categoria = item.categoria.nome
            antigo_conferente = item.conferente.username # ou .first_name
            antigo_tratamento = item.tratamento.nome if item.tratamento else "Sem Tratamento"

            # 2. CAPTURA OS NOVOS VALORES DO FORMULÁRIO
            novo_lote = request.POST.get('lote')
            novo_endereco = request.POST.get('endereco')
            novo_empresa = request.POST.get('empresa')
            novo_od = request.POST.get('origem_destino')
            novo_emb = request.POST.get('embalagem')
            novo_az = request.POST.get('az')
            novo_obs = request.POST.get('observacao')

            # Tratamento do Peso (Blindagem contra erro de formatação)
            peso_raw = request.POST.get('peso_unitario', '0')
            if peso_raw.count('.') > 1:
                partes = peso_raw.split('.')
                peso_raw = f"{partes[0]}.{partes[1]}"
            novo_peso = Decimal(peso_raw.replace(',', '.'))

            # Busca os Objetos Novos (FKs)
            obj_cultivar = get_object_or_404(Cultivar, id=request.POST.get('cultivar'))
            obj_peneira = get_object_or_404(Peneira, id=request.POST.get('peneira'))
            obj_categoria = get_object_or_404(Categoria, id=request.POST.get('categoria'))
            
            # Tratamento é opcional
            tid = request.POST.get('tratamento')
            if tid:
                obj_tratamento = get_object_or_404(Tratamento, id=tid)
                nome_novo_tratamento = obj_tratamento.nome
            else:
                obj_tratamento = None
                nome_novo_tratamento = "Sem Tratamento"

            # 3. COMPARAÇÃO E MONTAGEM DO LOG
            mudancas = []

            if antigo_lote != novo_lote: 
                mudancas.append(f"Lote: {antigo_lote} -> <b>{novo_lote}</b>")
            
            if antigo_endereco != novo_endereco: 
                mudancas.append(f"Endereço: {antigo_endereco} -> <b>{novo_endereco}</b>")
            
            if antigo_cultivar != obj_cultivar.nome:
                mudancas.append(f"Cultivar: {antigo_cultivar} -> <b>{obj_cultivar.nome}</b>")
            
            if antigo_peneira != obj_peneira.nome:
                mudancas.append(f"Peneira: {antigo_peneira} -> <b>{obj_peneira.nome}</b>")
            
            if antigo_categoria != obj_categoria.nome:
                mudancas.append(f"Categoria: {antigo_categoria} -> <b>{obj_categoria.nome}</b>")

            if antigo_tratamento != nome_novo_tratamento:
                mudancas.append(f"Tratamento: {antigo_tratamento} -> <b>{nome_novo_tratamento}</b>")

            if antigo_peso != novo_peso:
                mudancas.append(f"Peso: {antigo_peso} -> <b>{novo_peso}</b>")
            
            if antigo_emb != novo_emb:
                mudancas.append(f"Emb: {antigo_emb} -> <b>{novo_emb}</b>")
                
            if antigo_empresa != novo_empresa:
                mudancas.append(f"Empresa alterada.")

            if antigo_od != novo_od:
                mudancas.append(f"Origem/Dest alterado.")

            if antigo_obs != novo_obs:
                mudancas.append("Observação alterada.")

            # 4. ATUALIZA O OBJETO E SALVA
            item.lote = novo_lote
            item.endereco = novo_endereco
            item.empresa = novo_empresa
            item.origem_destino = novo_od
            item.peso_unitario = novo_peso
            item.embalagem = novo_emb
            item.az = novo_az
            item.observacao = novo_obs
            
            item.cultivar = obj_cultivar
            item.peneira = obj_peneira
            item.categoria = obj_categoria
            item.tratamento = obj_tratamento
            
            # Atualiza quem editou por último
            item.conferente = request.user 
            
            item.save()

            # 5. GRAVA O HISTÓRICO
            if mudancas:
                desc = "<br>".join(mudancas)
                HistoricoMovimentacao.objects.create(
                    estoque=item, 
                    usuario=request.user, 
                    tipo='Edição', 
                    descricao=f"Alterações:<br>{desc}"
                )
            else:
                # Se o usuário abriu o modal e clicou salvar sem mudar nada
                HistoricoMovimentacao.objects.create(
                    estoque=item, 
                    usuario=request.user, 
                    tipo='Edição', 
                    descricao="Salvo sem alterações visíveis."
                )

            messages.success(request, "Lote editado com sucesso.")
        except Exception as e:
            messages.error(request, f"Erro ao editar: {e}")

    return redirect('sapp:lista_estoque')

@login_required
def excluir_lote(request, id):
    item = get_object_or_404(Estoque, id=id)
    if request.method == 'POST':
        HistoricoMovimentacao.objects.create(
            estoque=None, 
            lote_ref=f"{item.lote} (Excluído)",
            usuario=request.user,
            tipo='EXCLUSÃO',
            descricao=f"Lote <b>{item.lote}</b> do endereço <b>{item.endereco}</b> foi excluído."
        )
        item.delete()
        messages.success(request, "Lote excluído.")
    return redirect('sapp:lista_estoque')

@login_required
def configuracoes(request):
    config = Configuracao.get_solo()
    # Lista de usuários que NÃO são superusers (Conferentes)
    usuarios_conferentes = User.objects.filter(is_superuser=False)

    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'add_conferente_user':
            if not request.user.is_superuser:
                messages.error(request, "Apenas Administradores podem criar usuários.")
            else:
                form = NovoConferenteUserForm(request.POST)
                if form.is_valid():
                    try:
                        u = User.objects.create_user(
                            username=form.cleaned_data['username'], 
                            password='conceito', 
                            first_name=form.cleaned_data['first_name']
                        )
                        messages.success(request, f"Usuário '{u.username}' criado! Senha padrão: conceito")
                    except Exception as e:
                        messages.error(request, f"Erro ao criar usuário: {e}")

        elif acao == 'delete_conferente_user':
             if request.user.is_superuser:
                 try:
                     uid = request.POST.get('id_item')
                     u = User.objects.get(id=uid)
                     if not u.is_superuser: 
                         u.delete()
                         messages.success(request, "Usuário removido.")
                 except: pass

        elif acao == 'config_geral':
             form = ConfiguracaoForm(request.POST, instance=config)
             if form.is_valid(): form.save(); messages.success(request, "Salvo!")
        
        elif acao == 'add_cultivar':
             f = CultivarForm(request.POST); 
             if f.is_valid(): f.save()
        elif acao == 'add_peneira':
             f = PeneiraForm(request.POST); 
             if f.is_valid(): f.save()
        elif acao == 'add_categoria':
             f = CategoriaForm(request.POST); 
             if f.is_valid(): f.save()
        elif acao == 'add_tratamento':
             f = TratamentoForm(request.POST); 
             if f.is_valid(): f.save()
        
        elif acao == 'delete_item':
             tipo = request.POST.get('tipo_item')
             uid = request.POST.get('id_item')
             try:
                 if tipo == 'cultivar': Cultivar.objects.get(id=uid).delete()
                 elif tipo == 'peneira': Peneira.objects.get(id=uid).delete()
                 elif tipo == 'categoria': Categoria.objects.get(id=uid).delete()
                 elif tipo == 'tratamento': Tratamento.objects.get(id=uid).delete()
                 messages.success(request, "Item removido.")
             except: messages.error(request, "Erro ao remover item.")

        return redirect('sapp:configuracoes')

    context = {
        'form_config': ConfiguracaoForm(instance=config),
        'cultivares': Cultivar.objects.all(),
        'peneiras': Peneira.objects.all(),
        'categorias': Categoria.objects.all(),
        'tratamentos': Tratamento.objects.all(),
        'usuarios_conferentes': usuarios_conferentes,
        'form_conf_user': NovoConferenteUserForm(),
    }
    return render(request, 'sapp/configuracoes.html', context)

@login_required
def historico_geral(request):
    lista = HistoricoMovimentacao.objects.all().order_by('-data_hora')
    paginator = Paginator(lista, 50)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'sapp/historico_geral.html', {'page_obj': page_obj})

# Adicione isso no TOPO junto com os outros imports


from django.http import JsonResponse # <--- TEM QUE TER ESSA IMPORTAÇÃO NO TOPO

# ... (suas outras views) ...

# ... (No final do arquivo) ...
@login_required
def api_buscar_dados_lote(request):
    lote_buscado = request.GET.get('lote')
    item = Estoque.objects.filter(lote=lote_buscado).order_by('-id').first()
    
    if item:
        data = {
            'encontrado': True,
            'cultivar': item.cultivar.id,
            'peneira': item.peneira.id,
            'categoria': item.categoria.id,
            'tratamento': item.tratamento.id if item.tratamento else "",
            'endereco': item.endereco,
            'empresa': item.empresa,
            'origem_destino': item.origem_destino,
            'peso_unitario': str(item.peso_unitario),
            'embalagem': item.embalagem,
            'az': item.az or "",
            'observacao': item.observacao or ""
        }
    else:
        data = {'encontrado': False}
    return JsonResponse(data)