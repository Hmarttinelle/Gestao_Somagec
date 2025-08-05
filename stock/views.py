# --- Ficheiro 100% Completo: stock/views.py ---
import json
from decimal import Decimal
import pathlib # Importar a biblioteca pathlib
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction, models
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import (
    Produto, Cliente, Fatura, ItemFatura, DadosEmpresa, Configuracao,
    GuiaTransporte, ItemGuia
)
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
from django.core.paginator import Paginator
from django.db.models import Sum, F, Q

from django.http import HttpResponse
from django.core.mail import EmailMessage, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import views as auth_views

try:
    from weasyprint import HTML
except ImportError:
    HTML = None

# ... (O resto das suas views permanece exatamente igual) ...
@login_required
def home_view(request):
    hoje = date.today()
    
    todas_as_faturas = Fatura.objects.all()
    faturas_pagas = todas_as_faturas.filter(paga=True)
    num_pagas = faturas_pagas.count()
    total_recebido = sum(f.total_geral for f in faturas_pagas)

    faturas_nao_pagas = todas_as_faturas.filter(paga=False)
    num_nao_pagas = faturas_nao_pagas.count()
    valor_em_divida = sum(f.valor_a_pagar for f in faturas_nao_pagas)

    faturas_mes_atual = todas_as_faturas.filter(data_emissao__year=hoje.year, data_emissao__month=hoje.month)
    num_faturas_mes = faturas_mes_atual.count()
    total_faturado_mes = sum(f.total_geral for f in faturas_mes_atual)

    num_clientes = Cliente.objects.count()
    
    periodo = request.GET.get('periodo', '1m_daily')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    status_fatura = request.GET.get('status_fatura', 'todas')
    
    faturas_grafico = Fatura.objects.all()
    if status_fatura == 'pagas':
        faturas_grafico = faturas_grafico.filter(paga=True)
    elif status_fatura == 'nao_pagas':
        faturas_grafico = faturas_grafico.filter(paga=False)
    
    labels_grafico, dados_grafico = [], []
    
    if periodo == 'custom' and start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        mes_atual_iter = date(start_date.year, start_date.month, 1)
        while mes_atual_iter <= end_date:
            labels_grafico.append(mes_atual_iter.strftime('%b/%y'))
            faturas_do_mes = faturas_grafico.filter(data_emissao__year=mes_atual_iter.year, data_emissao__month=mes_atual_iter.month)
            total_com_igv = sum(f.total_geral for f in faturas_do_mes)
            dados_grafico.append(float(total_com_igv))
            mes_atual_iter += relativedelta(months=1)
            
    elif periodo == '1m_daily':
        mes_atual, ano_atual = hoje.month, hoje.year
        _, num_dias = calendar.monthrange(ano_atual, mes_atual)
        
        for dia in range(1, num_dias + 1):
            labels_grafico.append(str(dia))
            data_especifica = date(ano_atual, mes_atual, dia)
            faturas_do_dia = faturas_grafico.filter(data_emissao=data_especifica)
            total_do_dia = sum(f.total_geral for f in faturas_do_dia)
            dados_grafico.append(float(total_do_dia))

    else:
        num_meses = 3 if periodo == '3m' else 6
        for i in range(num_meses):
            mes_calculo = hoje - relativedelta(months=i)
            labels_grafico.append(mes_calculo.strftime('%b/%y'))
            faturas_do_mes = faturas_grafico.filter(data_emissao__year=mes_calculo.year, data_emissao__month=mes_calculo.month)
            total_do_mes = sum(f.total_geral for f in faturas_do_mes)
            dados_grafico.append(float(total_do_mes))
        labels_grafico.reverse()
        dados_grafico.reverse()
    
    config, created = Configuracao.objects.get_or_create(pk=1)
    limite_estoque_baixo = config.limite_alerta_estoque
    produtos_estoque_baixo = Produto.objects.filter(estoque_atual__lte=limite_estoque_baixo).order_by('estoque_atual')
    
    data_limite_30_dias = hoje - timedelta(days=30)
    top_clientes = Cliente.objects.annotate(total_gasto=Sum(F('fatura__itens__quantidade') * F('fatura__itens__preco_unitario'), filter=Q(fatura__data_emissao__gte=data_limite_30_dias))).order_by('-total_gasto').filter(total_gasto__gt=0)[:10]
    top_produtos = Produto.objects.annotate(total_vendido=Sum(F('itemfatura__quantidade') * F('itemfatura__preco_unitario'), filter=Q(itemfatura__fatura__data_emissao__gte=data_limite_30_dias))).order_by('-total_vendido').filter(total_vendido__gt=0)[:10]
    
    contexto = {
        'total_faturado_mes': total_faturado_mes, 'num_faturas_mes': num_faturas_mes,
        'num_clientes': num_clientes, 'produtos_estoque_baixo': produtos_estoque_baixo,
        'limite_estoque_baixo': limite_estoque_baixo, 'labels_grafico': json.dumps(labels_grafico),
        'dados_grafico': json.dumps(dados_grafico), 'periodo_selecionado': periodo,
        'start_date': start_date_str, 'end_date': end_date_str,
        'status_fatura_selecionado': status_fatura, 'top_clientes': top_clientes,
        'top_produtos': top_produtos, 'num_pagas': num_pagas,
        'total_recebido': total_recebido, 'num_nao_pagas': num_nao_pagas,
        'valor_em_divida': valor_em_divida,
    }
    return render(request, 'stock/home.html', contexto)

@login_required
def lista_clientes_view(request):
    q_nome = request.GET.get('q_nome', '')
    q_telefone = request.GET.get('q_telefone', '')
    clientes = Cliente.objects.all().order_by('nome')
    if q_nome:
        clientes = clientes.filter(nome__icontains=q_nome)
    if q_telefone:
        clientes = clientes.filter(telefone__icontains=q_telefone)
    paginator = Paginator(clientes, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'stock/lista_clientes.html', {'page_obj': page_obj})

@login_required
def adicionar_cliente_view(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        Cliente.objects.create(
            nome=nome, 
            nif=request.POST.get('nif'), 
            telefone=request.POST.get('telefone'), 
            email=request.POST.get('email'), 
            endereco=request.POST.get('endereco'),
            utilizador=request.user 
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
        cliente.modificado_por = request.user
        cliente.save()
        messages.success(request, _("Os dados do cliente '{nome}' foram atualizados com sucesso!").format(nome=cliente.nome))
        return redirect('lista_clientes')
    return render(request, 'stock/editar_cliente.html', {'cliente': cliente})

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
    return render(request, 'stock/cliente_confirm_delete.html', {'cliente': cliente})

@login_required
def lista_produtos_view(request):
    produtos_list = Produto.objects.all().order_by('nome')
    paginator = Paginator(produtos_list, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'stock/lista_produtos.html', {'page_obj': page_obj})

@login_required
def adicionar_produto_view(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        Produto.objects.create(
            nome=nome, calibre=request.POST.get('calibre'), descricao=request.POST.get('descricao'), 
            unidade_medida=request.POST.get('unidade_medida'), 
            estoque_atual=Decimal(request.POST.get('estoque_atual', '0.00')), 
            preco_por_unidade=Decimal(request.POST.get('preco_por_unidade', '0.00')),
            utilizador=request.user
        )
        messages.success(request, _("O produto '{nome}' foi adicionado com sucesso!").format(nome=nome))
        return redirect('lista_produtos')
    return render(request, 'stock/adicionar_produto.html', {'unidades': Produto.UNIDADES})

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
        produto.modificado_por = request.user
        produto.save()
        messages.success(request, _("O produto '{nome}' foi atualizado com sucesso!").format(nome=produto.nome))
        return redirect('lista_produtos')
    return render(request, 'stock/editar_produto.html', {'produto': produto, 'unidades': Produto.UNIDADES})

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
    return render(request, 'stock/produto_confirm_delete.html', {'produto': produto})

@login_required
def criar_fatura_view(request):
    if request.method == 'GET':
        return render(request, 'stock/criar_fatura.html', { 'clientes': Cliente.objects.all(), 'produtos': Produto.objects.all().order_by('nome') })
    if request.method == 'POST':
        try:
            with transaction.atomic():
                cliente_id = request.POST.get('cliente')
                if not cliente_id: raise ValueError(_("Por favor, selecione um cliente."))
                taxa_igv = Decimal(request.POST.get('taxa_igv', '17.00'))
                desconto = Decimal(request.POST.get('desconto', '0.00'))
                adiantamento = Decimal(request.POST.get('adiantamento', '0.00'))
                itens_json = request.POST.getlist('items[]')
                if not itens_json: raise ValueError(_("A fatura deve ter pelo menos um item."))
                cliente = Cliente.objects.get(id=cliente_id)
                ano_atual = date.today().year
                ultima_fatura_ano = Fatura.objects.filter(data_emissao__year=ano_atual).order_by('numero_fatura').last()
                novo_numero_seq = 1
                if ultima_fatura_ano and ultima_fatura_ano.numero_fatura:
                    try:
                        novo_numero_seq = int(ultima_fatura_ano.numero_fatura.split('-')[-1]) + 1
                    except (ValueError, IndexError):
                        novo_numero_seq = Fatura.objects.filter(data_emissao__year=ano_atual).count() + 1
                numero_final_fatura = f"{ano_atual}-{novo_numero_seq:04d}"
                nova_fatura = Fatura.objects.create(cliente=cliente, numero_fatura=numero_final_fatura, taxa_igv=taxa_igv, desconto=desconto, adiantamento=adiantamento, utilizador=request.user)
                for item_str in itens_json:
                    item_data = json.loads(item_str)
                    produto = Produto.objects.get(id=item_data['produto_id'])
                    quantidade = Decimal(item_data['quantidade'])
                    if produto.estoque_atual < quantidade: raise ValueError(_("Estoque insuficiente para {produto_nome}. Disponível: {estoque}").format(produto_nome=produto.nome, estoque=produto.estoque_atual))
                    ItemFatura.objects.create(fatura=nova_fatura, produto=produto, quantidade=quantidade, preco_unitario=Decimal(item_data['preco_unitario']))
                    produto.estoque_atual -= quantidade
                    produto.save()
                messages.success(request, _("Fatura {numero} criada com sucesso!").format(numero=nova_fatura.numero_fatura))
                return redirect('detalhe_fatura', fatura_id=nova_fatura.id)
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao gerar a fatura: {erro}").format(erro=e))
            return render(request, 'stock/criar_fatura.html', { 'clientes': Cliente.objects.all(), 'produtos': Produto.objects.all().order_by('nome') })
    return redirect('home')

@login_required
def editar_fatura_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for item_antigo in fatura.itens.all():
                    item_antigo.produto.estoque_atual += item_antigo.quantidade
                    item_antigo.produto.save()
                fatura.itens.all().delete()
                cliente_id = request.POST.get('cliente')
                if not cliente_id: raise ValueError(_("O campo cliente não pode estar vazio."))
                itens_json = request.POST.getlist('items[]')
                if not itens_json: raise ValueError(_("A fatura deve ter pelo menos um item."))
                fatura.cliente = Cliente.objects.get(id=cliente_id)
                fatura.taxa_igv = Decimal(request.POST.get('taxa_igv', '17.00'))
                fatura.desconto = Decimal(request.POST.get('desconto', '0.00'))
                fatura.adiantamento = Decimal(request.POST.get('adiantamento', '0.00'))
                fatura.modificado_por = request.user
                fatura.save()
                for item_str in itens_json:
                    item_data = json.loads(item_str)
                    produto = Produto.objects.get(id=item_data['produto_id'])
                    quantidade = Decimal(item_data['quantidade'])
                    if produto.estoque_atual < quantidade: raise ValueError(_("Estoque insuficiente para {produto_nome}. Disponível: {estoque}").format(produto_nome=produto.nome, estoque=produto.estoque_atual))
                    ItemFatura.objects.create(fatura=fatura, produto=produto, quantidade=quantidade, preco_unitario=Decimal(item_data['preco_unitario']))
                    produto.estoque_atual -= quantidade
                    produto.save()
                messages.success(request, _("Fatura {numero} atualizada com sucesso!").format(numero=fatura.numero_fatura))
                return redirect('detalhe_fatura', fatura_id=fatura.id)
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao salvar as alterações: {erro}").format(erro=e))
            return redirect('editar_fatura', fatura_id=fatura.id)
    itens_atuais = [{'produto_id': item.produto.id, 'produto_nome': f"{item.produto.nome} ({item.produto.calibre})" if item.produto.calibre else item.produto.nome, 'quantidade': str(item.quantidade), 'preco_unitario': str(item.preco_unitario), 'subtotal': str(item.subtotal)} for item in fatura.itens.all()]
    return render(request, 'stock/editar_fatura.html', {'fatura': fatura, 'clientes': Cliente.objects.all(), 'produtos': Produto.objects.all().order_by('nome'), 'itens_atuais_json': json.dumps(itens_atuais)})

@login_required
def lista_faturas_view(request):
    q_numero = request.GET.get('q_numero', '')
    q_cliente = request.GET.get('q_cliente', '')
    q_data = request.GET.get('q_data', '')
    q_paga = request.GET.get('q_paga', '')
    q_periodo = request.GET.get('q_periodo', '')
    faturas = Fatura.objects.all().order_by('-data_emissao', '-numero_fatura')
    if q_numero: faturas = faturas.filter(numero_fatura__icontains=q_numero)
    if q_cliente: faturas = faturas.filter(cliente__nome__icontains=q_cliente)
    if q_data:
        try: faturas = faturas.filter(data_emissao=datetime.strptime(q_data, '%Y-%m-%d').date())
        except (ValueError, TypeError): pass
    if q_paga == 'sim': faturas = faturas.filter(paga=True)
    if q_paga == 'nao': faturas = faturas.filter(paga=False)
    if q_periodo == 'mes_atual':
        hoje = date.today()
        faturas = faturas.filter(data_emissao__year=hoje.year, data_emissao__month=hoje.month)
    paginator = Paginator(faturas, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'stock/lista_faturas.html', {'page_obj': page_obj})

@login_required
def detalhe_fatura_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    return render(request, 'stock/detalhe_fatura.html', {'fatura': fatura})

@login_required
def toggle_fatura_paga_view(request, fatura_id):
    if request.method == 'POST':
        fatura = get_object_or_404(Fatura, id=fatura_id)
        fatura.paga = not fatura.paga
        fatura.modificado_por = request.user
        fatura.save()
        messages.success(request, _("A fatura {numero} foi marcada como PAGA.").format(numero=fatura.numero_fatura) if fatura.paga else _("A fatura {numero} foi marcada como NÃO PAGA.").format(numero=fatura.numero_fatura))
    return redirect('lista_faturas')

@login_required
def fatura_print_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    return render(request, 'stock/fatura_print.html', {'fatura': fatura})

@login_required
def fatura_pdf_view(request, fatura_id):
    if HTML is None:
        return HttpResponse("WeasyPrint não está instalado.", status=501)
    fatura = get_object_or_404(Fatura, id=fatura_id)
    dados_empresa = DadosEmpresa.objects.first()
    logo_uri = None
    if dados_empresa and dados_empresa.logotipo and hasattr(dados_empresa.logotipo, 'path'):
        logo_path = pathlib.Path(dados_empresa.logotipo.path)
        logo_uri = logo_path.as_uri()
    contexto = {'fatura': fatura, 'dados_empresa': dados_empresa, 'logo_uri': logo_uri}
    html_string = render_to_string('stock/fatura_pdf.html', contexto)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="fatura_{fatura.numero_fatura}.pdf"'
    return response

# --- VIEW ATUALIZADA ---
@login_required
def enviar_fatura_email_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    if request.method == 'POST':
        if not fatura.cliente.email:
            messages.error(request, _("O cliente '{nome}' não tem um endereço de email associado.").format(nome=fatura.cliente.nome))
            return redirect('detalhe_fatura', fatura_id=fatura.id)
        if HTML is None:
            messages.error(request, "A biblioteca WeasyPrint não está instalada. O PDF não pode ser gerado.")
            return redirect('detalhe_fatura', fatura_id=fatura.id)
        try:
            config = Configuracao.objects.first()
            if not config or not config.email_remetente or not config.password_remetente:
                messages.error(request, _("As credenciais de email não estão configuradas na área de administração."))
                return redirect('detalhe_fatura', fatura_id=fatura.id)
            dados_empresa = DadosEmpresa.objects.first()

            # Corpo do email em texto simples
            corpo_email = _("""
            Caro(a) {cliente_nome},

            Segue em anexo a fatura com o número {numero_fatura}.

            Com os melhores cumprimentos,
            {nome_empresa}
            """).format(
                cliente_nome=fatura.cliente.nome,
                numero_fatura=fatura.numero_fatura,
                nome_empresa=dados_empresa.nome_empresa if dados_empresa else 'A nossa empresa'
            )
            
            # Lógica para gerar o PDF para o anexo
            logo_uri = None
            if dados_empresa and dados_empresa.logotipo and hasattr(dados_empresa.logotipo, 'path'):
                logo_path = pathlib.Path(dados_empresa.logotipo.path)
                logo_uri = logo_path.as_uri()
            contexto_pdf = {'fatura': fatura, 'dados_empresa': dados_empresa, 'logo_uri': logo_uri}
            html_string = render_to_string('stock/fatura_pdf.html', contexto_pdf)
            pdf_em_memoria = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
            
            assunto = _("Fatura Nº {numero_fatura} da {nome_empresa}").format(
                numero_fatura=fatura.numero_fatura, 
                nome_empresa=dados_empresa.nome_empresa if dados_empresa else ''
            )
            
            email = EmailMessage(
                assunto,
                corpo_email, # Usar o corpo em texto simples
                config.email_remetente,
                [fatura.cliente.email]
            )
            email.attach(f'Fatura-{fatura.numero_fatura}.pdf', pdf_em_memoria, 'application/pdf')

            connection = get_connection(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT, username=config.email_remetente, password=config.password_remetente, use_tls=settings.EMAIL_USE_TLS)
            connection.send_messages([email])
            messages.success(request, _("Fatura enviada com sucesso para {email}.").format(email=fatura.cliente.email))
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao enviar o email: {erro}").format(erro=e))
    return redirect('detalhe_fatura', fatura_id=fatura.id)

@login_required
def lista_guias_view(request):
    todas_as_guias_list = GuiaTransporte.objects.all()
    paginator = Paginator(todas_as_guias_list, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'stock/lista_guias.html', {'page_obj': page_obj})

@login_required
def criar_guia_desde_fatura_view(request, fatura_id):
    fatura = get_object_or_404(Fatura, id=fatura_id)
    if hasattr(fatura, 'guia_transporte'):
        messages.info(request, _("Já existe uma guia de transporte para esta fatura."))
        return redirect('detalhe_guia', guia_id=fatura.guia_transporte.id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                ano_atual = date.today().year
                ultima_guia_ano = GuiaTransporte.objects.filter(data_emissao__year=ano_atual).order_by('numero_guia').last()
                novo_numero_seq = 1
                if ultima_guia_ano and ultima_guia_ano.numero_guia:
                    try: novo_numero_seq = int(ultima_guia_ano.numero_guia.split('-')[-1]) + 1
                    except (ValueError, IndexError): novo_numero_seq = GuiaTransporte.objects.filter(data_emissao__year=ano_atual).count() + 1
                numero_final_guia = f"{ano_atual}-{novo_numero_seq:04d}"
                nova_guia = GuiaTransporte.objects.create(fatura=fatura, numero_guia=numero_final_guia, morada_carga=request.POST.get('morada_carga', ''), morada_descarga=request.POST.get('morada_descarga', ''), matricula_veiculo=request.POST.get('matricula_veiculo', ''), utilizador=request.user)
                for item_fatura in fatura.itens.all(): ItemGuia.objects.create(guia=nova_guia, produto=item_fatura.produto, quantidade=item_fatura.quantidade)
                messages.success(request, _("Guia de Transporte {numero} criada com sucesso a partir da fatura {fatura_num}.").format(numero=nova_guia.numero_guia, fatura_num=fatura.numero_fatura))
                return redirect('detalhe_guia', guia_id=nova_guia.id)
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao gerar a guia: {erro}").format(erro=e))
            return redirect('detalhe_fatura', fatura_id=fatura.id)
    return render(request, 'stock/criar_guia_desde_fatura.html', {'fatura': fatura, 'dados_empresa': DadosEmpresa.objects.first()})

@login_required
def detalhe_guia_view(request, guia_id):
    guia = get_object_or_404(GuiaTransporte, id=guia_id)
    return render(request, 'stock/detalhe_guia.html', {'guia': guia})

@login_required
def editar_guia_view(request, guia_id):
    guia = get_object_or_404(GuiaTransporte, id=guia_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                guia.morada_carga = request.POST.get('morada_carga', '')
                guia.morada_descarga = request.POST.get('morada_descarga', '')
                guia.matricula_veiculo = request.POST.get('matricula_veiculo', '')
                guia.save()
                messages.success(request, _("Guia de Transporte {numero} atualizada com sucesso!").format(numero=guia.numero_guia))
                return redirect('detalhe_guia', guia_id=guia.id)
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao salvar as alterações: {erro}").format(erro=e))
            return redirect('editar_guia', guia_id=guia.id)
    return render(request, 'stock/editar_guia.html', {'guia': guia})

@login_required
def guia_print_view(request, guia_id):
    guia = get_object_or_404(GuiaTransporte, id=guia_id)
    return render(request, 'stock/guia_print.html', {'guia': guia, 'dados_empresa': DadosEmpresa.objects.first()})

@login_required
def guia_pdf_view(request, guia_id):
    if HTML is None:
        return HttpResponse("WeasyPrint não está instalado.", status=501)
    guia = get_object_or_404(GuiaTransporte, id=guia_id)
    dados_empresa = DadosEmpresa.objects.first()
    logo_uri = None
    if dados_empresa and dados_empresa.logotipo and hasattr(dados_empresa.logotipo, 'path'):
        logo_path = pathlib.Path(dados_empresa.logotipo.path)
        logo_uri = logo_path.as_uri()
    contexto = {
        'guia': guia,
        'dados_empresa': dados_empresa,
        'logo_uri': logo_uri,
    }
    html_string = render_to_string('stock/guia_pdf.html', contexto)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="guia_{guia.numero_guia}.pdf"'
    return response

@login_required
def enviar_guia_email_view(request, guia_id):
    guia = get_object_or_404(GuiaTransporte, id=guia_id)
    if request.method == 'POST':
        if not guia.cliente.email:
            messages.error(request, _("O cliente '{nome}' não tem um endereço de email associado.").format(nome=guia.cliente.nome))
            return redirect('detalhe_guia', guia_id=guia.id)
        if HTML is None:
            messages.error(request, "A biblioteca WeasyPrint não está instalada. O PDF não pode ser gerado.")
            return redirect('detalhe_guia', guia_id=guia.id)
        try:
            config = Configuracao.objects.first()
            if not config or not config.email_remetente or not config.password_remetente:
                messages.error(request, _("As credenciais de email não estão configuradas na área de administração."))
                return redirect('detalhe_guia', guia_id=guia.id)
            dados_empresa = DadosEmpresa.objects.first()
            
            corpo_email = f"Caro(a) {guia.cliente.nome},\n\nSegue em anexo a Guia de Transporte com o número {guia.numero_guia}.\n\nCom os melhores cumprimentos,\n{dados_empresa.nome_empresa if dados_empresa else 'A nossa empresa'}"
            
            logo_uri = None
            if dados_empresa and dados_empresa.logotipo and hasattr(dados_empresa.logotipo, 'path'):
                logo_path = pathlib.Path(dados_empresa.logotipo.path)
                logo_uri = logo_path.as_uri()
            
            contexto_pdf = {'guia': guia, 'dados_empresa': dados_empresa, 'logo_uri': logo_uri}
            html_string = render_to_string('stock/guia_pdf.html', contexto_pdf)
            pdf_em_memoria = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
            
            assunto = _("Guia de Transporte Nº {numero_guia} da {nome_empresa}").format(numero_guia=guia.numero_guia, nome_empresa=dados_empresa.nome_empresa if dados_empresa else '')
            
            email = EmailMessage(assunto, corpo_email, config.email_remetente, [guia.cliente.email])
            email.attach(f'Guia-{guia.numero_guia}.pdf', pdf_em_memoria, 'application/pdf')
            connection = get_connection(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT, username=config.email_remetente, password=config.password_remetente, use_tls=settings.EMAIL_USE_TLS)
            connection.send_messages([email])
            messages.success(request, _("Guia de Transporte enviada com sucesso para {email}.").format(email=guia.cliente.email))
        except Exception as e:
            messages.error(request, _("Ocorreu um erro ao enviar o email: {erro}").format(erro=e))
    return redirect('detalhe_guia', guia_id=guia.id)


class CustomLoginView(auth_views.LoginView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dados_empresa'] = DadosEmpresa.objects.first()
        return context