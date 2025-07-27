# --- Ficheiro Final com Paginação e Mensagens: stock/views.py ---

import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import Produto, Cliente, Fatura, ItemFatura, DadosEmpresa
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import calendar
from django.core.paginator import Paginator # Importa o Paginator

# --- Views da Aplicação ---

@login_required
def home_view(request):
    """Mostra o Dashboard com estatísticas e gráfico de vendas."""
    hoje = date.today()
    faturas_mes_atual = Fatura.objects.filter(data_emissao__year=hoje.year, data_emissao__month=hoje.month)
    num_faturas_mes = faturas_mes_atual.count()
    total_faturado_mes = sum(f.total_final for f in faturas_mes_atual)
    num_clientes = Cliente.objects.count()
    limite_estoque_baixo = 10
    produtos_estoque_baixo = Produto.objects.filter(estoque_atual__lte=limite_estoque_baixo).order_by('estoque_atual')
    periodo = request.GET.get('periodo', '6m')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    labels_grafico, dados_grafico = [], []

    if periodo == 'custom' and start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        mes_atual_iter = date(start_date.year, start_date.month, 1)
        while mes_atual_iter <= end_date:
            labels_grafico.append(mes_atual_iter.strftime('%b/%y'))
            faturas_do_mes = Fatura.objects.filter(data_emissao__year=mes_atual_iter.year, data_emissao__month=mes_atual_iter.month)
            total_com_igv = sum(f.total_final for f in faturas_do_mes)
            dados_grafico.append(float(total_com_igv))
            mes_atual_iter += relativedelta(months=1)
    elif periodo == '1m_daily':
        _, num_dias = calendar.monthrange(hoje.year, hoje.month)
        for dia in range(1, num_dias + 1):
            labels_grafico.append(str(dia))
            faturas_dia = Fatura.objects.filter(data_emissao__year=hoje.year, data_emissao__month=hoje.month, data_emissao__day=dia)
            total_dia = sum(f.total_final for f in faturas_dia)
            dados_grafico.append(float(total_dia))
    else:
        num_meses = 3 if periodo == '3m' else 6
        for i in range(num_meses):
            mes_calculo = hoje - relativedelta(months=i)
            labels_grafico.append(mes_calculo.strftime('%b/%y'))
            faturas_do_mes = Fatura.objects.filter(data_emissao__year=mes_calculo.year, data_emissao__month=mes_calculo.month)
            total_do_mes = sum(f.total_final for f in faturas_do_mes)
            dados_grafico.append(float(total_do_mes))
        labels_grafico.reverse()
        dados_grafico.reverse()
        
    contexto = {
        'total_faturado_mes': total_faturado_mes, 'num_faturas_mes': num_faturas_mes, 'num_clientes': num_clientes,
        'produtos_estoque_baixo': produtos_estoque_baixo, 'limite_estoque_baixo': limite_estoque_baixo,
        'labels_grafico': json.dumps(labels_grafico), 'dados_grafico': json.dumps(dados_grafico),
        'periodo_selecionado': periodo, 'start_date': start_date_str, 'end_date': end_date_str,
    }
    return render(request, 'stock/home.html', contexto)

# --- VIEWS DE CLIENTES ---

@login_required
def lista_clientes_view(request):
    """Mostra uma lista de todos os clientes, com paginação."""
    clientes_list = Cliente.objects.all().order_by('nome')
    paginator = Paginator(clientes_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    contexto = {'page_obj': page_obj}
    return render(request, 'stock/lista_clientes.html', contexto)

@login_required
def adicionar_cliente_view(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        Cliente.objects.create(
            nome=nome, nif=request.POST.get('nif'), telefone=request.POST.get('telefone'), 
            email=request.POST.get('email'), endereco=request.POST.get('endereco')
        )
        messages.success(request, _("O cliente '{nome}' foi adicionado com sucesso!").format(nome=nome))
        return redirect('lista_clientes')
    return render(request, 'stock/adicionar_cliente.html')

@login_required
def editar_cliente_view(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        cliente.nome = request.POST.get('nome')
        cliente.nif = request.POST.get('nif')
        cliente.telefone = request.POST.get('telefone')
        cliente.email = request.POST.get('email')
        cliente.endereco = request.POST.get('endereco')
        cliente.save()
        messages.success(request, _("Os dados do cliente '{nome}' foram atualizados com sucesso!").format(nome=cliente.nome))
        return redirect('lista_clientes')
    contexto = {'cliente': cliente}
    return render(request, 'stock/editar_cliente.html', contexto)

@login_required
def apagar_cliente_view(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == 'POST':
        try:
            nome_cliente = cliente.nome
            cliente.delete()
            messages.success(request, _("O cliente '{nome}' foi apagado com sucesso.").format(nome=nome_cliente))
        except models.ProtectedError:
            messages.error(request, _("O cliente '{nome}' não pode ser apagado porque já tem faturas associadas a ele.").format(nome=cliente.nome))
        return redirect('lista_clientes')
    contexto = {'cliente': cliente}
    return render(request, 'stock/cliente_confirm_delete.html', contexto)

# --- VIEWS DE PRODUTOS ---

@login_required
def lista_produtos_view(request):
    """Mostra uma lista de todos os produtos, com paginação."""
    produtos_list = Produto.objects.all().order_by('nome')
    paginator = Paginator(produtos_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    contexto = {'page_obj': page_obj}
    return render(request, 'stock/lista_produtos.html', contexto)

@login_required
def adicionar_produto_view(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        Produto.objects.create(
            nome=nome, calibre=request.POST.get('calibre'), descricao=request.POST.get('descricao'),
            unidade_medida=request.POST.get('unidade_medida'), 
            estoque_atual=Decimal(request.POST.get('estoque_atual', '0.00')),
            preco_por_unidade=Decimal(request.POST.get('preco_por_unidade', '0.00'))
        )
        messages.success(request, _("O produto '{nome}' foi adicionado com sucesso!").format(nome=nome))
        return redirect('lista_produtos')
    contexto = {'unidades': Produto.UNIDADES}
    return render(request, 'stock/adicionar_produto.html', contexto)

@login_required
def editar_produto_view(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    if request.method == 'POST':
        produto.nome = request.POST.get('nome')
        produto.calibre = request.POST.get('calibre')
        produto.descricao = request.POST.get('descricao')
        produto.unidade_medida = request.POST.get('unidade_medida')
        produto.estoque_atual = Decimal(request.POST.get('estoque_atual', '0.00'))
        produto.preco_por_unidade = Decimal(request.POST.get('preco_por_unidade', '0.00'))
        produto.save()
        messages.success(request, _("O produto '{nome}' foi atualizado com sucesso!").format(nome=produto.nome))
        return redirect('lista_produtos')
    contexto = {'produto': produto, 'unidades': Produto.UNIDADES}
    return render(request, 'stock/editar_produto.html', contexto)

@login_required
def apagar_produto_view(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    if request.method == 'POST':
        try:
            nome_produto = produto.nome
            produto.delete()
            messages.success(request, _("O produto '{nome}' foi apagado com sucesso.").format(nome=nome_produto))
        except models.ProtectedError:
            messages.error(request, _("O produto '{nome}' não pode ser apagado porque já está associado a faturas existentes.").format(nome=produto.nome))
        return redirect('lista_produtos')
    contexto = {'produto': produto}
    return render(request, 'stock/produto_confirm_delete.html', contexto)

# --- VIEWS DE FATURAS ---

@login_required
def criar_fatura_view(request):
    if request.method == 'GET':
        contexto = { 'clientes': Cliente.objects.all(), 'produtos': Produto.objects.all().order_by('nome') }
        return render(request, 'stock/criar_fatura.html', contexto)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                cliente_id = request.POST.get('cliente')
                taxa_igv = Decimal(request.POST.get('taxa_igv'))
                itens_json = request.POST.getlist('items[]')
                if not itens_json: raise ValueError(_("A fatura deve ter pelo menos um item."))
                cliente = Cliente.objects.get(id=cliente_id)
                
                ano_atual = date.today().year
                faturas_no_ano = Fatura.objects.filter(data_emissao__year=ano_atual).count()
                novo_numero_seq = faturas_no_ano + 1
                numero_final_fatura = f"{ano_atual}-{novo_numero_seq:04d}"
                
                nova_fatura = Fatura.objects.create(
                    cliente=cliente,
                    numero_fatura=numero_final_fatura,
                    taxa_igv=taxa_igv,
                    utilizador=request.user
                )
                for item_str in itens_json:
                    item_data = json.loads(item_str)
                    produto_id = item_data['produto_id']
                    quantidade = Decimal(item_data['quantidade'])
                    produto = Produto.objects.get(id=produto_id)
                    if produto.estoque_atual < quantidade: raise ValueError(_("Estoque insuficiente para {produto_nome}. Disponível: {estoque}").format(produto_nome=produto.nome, estoque=produto.estoque_atual))
                    ItemFatura.objects.create(fatura=nova_fatura, produto=produto, quantidade=quantidade, preco_unitario=Decimal(item_data['preco_unitario']))
                    produto.estoque_atual -= quantidade
                    produto.save()
                messages.success(request, _("Fatura {numero} criada com sucesso!").format(numero=nova_fatura.numero_fatura))
                return redirect('detalhe_fatura', fatura_id=nova_fatura.id)
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao gerar a fatura: {erro}").format(erro=e))
            contexto_erro = { 'clientes': Cliente.objects.all(), 'produtos': Produto.objects.all().order_by('nome') }
            return render(request, 'stock/criar_fatura.html', contexto_erro)
    return redirect('home')

@login_required
def editar_fatura_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                cliente_id = request.POST.get('cliente')
                taxa_igv = Decimal(request.POST.get('taxa_igv'))
                itens_json = request.POST.getlist('items[]')
                if not itens_json: raise ValueError(_("A fatura deve ter pelo menos um item."))
                fatura.cliente = Cliente.objects.get(id=cliente_id)
                fatura.taxa_igv = taxa_igv
                fatura.save()
                for item_antigo in fatura.itens.all():
                    item_antigo.produto.estoque_atual += item_antigo.quantidade
                    item_antigo.produto.save()
                fatura.itens.all().delete()
                for item_str in itens_json:
                    item_data = json.loads(item_str)
                    produto_id = item_data['produto_id']
                    quantidade = Decimal(item_data['quantidade'])
                    produto = Produto.objects.get(id=produto_id)
                    if produto.estoque_atual < quantidade: raise ValueError(_("Estoque insuficiente para {produto_nome}. Disponível: {estoque}").format(produto_nome=produto.nome, estoque=produto.estoque_atual))
                    ItemFatura.objects.create(fatura=fatura, produto=produto, quantidade=quantidade, preco_unitario=Decimal(item_data['preco_unitario']))
                    produto.estoque_atual -= quantidade
                    produto.save()
                messages.success(request, _("Fatura {numero} atualizada com sucesso!").format(numero=fatura.numero_fatura))
                return redirect('detalhe_fatura', fatura_id=fatura.id)
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao salvar as alterações: {erro}").format(erro=e))
            contexto_erro = { 'fatura': fatura, 'clientes': Cliente.objects.all(), 'produtos': Produto.objects.all().order_by('nome') }
            return render(request, 'stock/editar_fatura.html', contexto_erro)
    else: # GET request
        itens_atuais = []
        for item in fatura.itens.all():
            itens_atuais.append({ 'produto_id': item.produto.id, 'produto_nome': f"{item.produto.nome} ({item.produto.calibre})" if item.produto.calibre else item.produto.nome, 'quantidade': str(item.quantidade), 'preco_unitario': str(item.preco_unitario), 'subtotal': str(item.subtotal), })
        contexto = { 'fatura': fatura, 'clientes': Cliente.objects.all(), 'produtos': Produto.objects.all().order_by('nome'), 'itens_atuais_json': json.dumps(itens_atuais) }
        return render(request, 'stock/editar_fatura.html', contexto)

@login_required
def lista_faturas_view(request):
    """Mostra o histórico de todas as faturas criadas, com paginação."""
    todas_as_faturas_list = Fatura.objects.all().order_by('-data_emissao')
    paginator = Paginator(todas_as_faturas_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    contexto = {'page_obj': page_obj}
    return render(request, 'stock/lista_faturas.html', contexto)

@login_required
def detalhe_fatura_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    dados_empresa = DadosEmpresa.objects.first()
    contexto = { 'fatura': fatura, 'dados_empresa': dados_empresa, }
    return render(request, 'stock/detalhe_fatura.html', contexto)

@login_required
def toggle_fatura_paga_view(request, fatura_id):
    if request.method == 'POST':
        fatura = get_object_or_404(Fatura, id=fatura_id)
        fatura.paga = not fatura.paga
        fatura.save()
        if fatura.paga:
            messages.success(request, _("A fatura {numero} foi marcada como PAGA.").format(numero=fatura.numero_fatura))
        else:
            messages.info(request, _("A fatura {numero} foi marcada como NÃO PAGA.").format(numero=fatura.numero_fatura))
    return redirect('lista_faturas')

@login_required
def fatura_print_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    dados_empresa = DadosEmpresa.objects.first()
    contexto = { 'fatura': fatura, 'dados_empresa': dados_empresa, }
    return render(request, 'stock/fatura_print.html', contexto)