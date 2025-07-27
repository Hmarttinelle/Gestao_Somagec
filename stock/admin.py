# ficheiro: stock/admin.py

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from .models import Produto, Cliente, Fatura, ItemFatura, DadosEmpresa
from datetime import date

# --- NOVA AÇÃO ADMINISTRATIVA ---
@admin.action(description=_("Resetar numeração para faturas selecionadas (usar com cuidado)"))
def resetar_numeracao(modeladmin, request, queryset):
    """
    Ação para apagar faturas e reiniciar a contagem do ano.
    Esta é uma ação PERIGOSA e deve ser usada com cuidado.
    """
    ano_atual = date.today().year
    # Filtra apenas as faturas do ano atual dentro das selecionadas
    faturas_para_apagar = queryset.filter(data_emissao__year=ano_atual)
    
    count = faturas_para_apagar.count()
    
    if count > 0:
        # Devolve o estoque dos itens antes de apagar as faturas
        for fatura in faturas_para_apagar:
            for item in fatura.itens.all():
                item.produto.estoque_atual += item.quantidade
                item.produto.save()
        
        # Apaga as faturas selecionadas
        faturas_para_apagar.delete()
        
        messages.success(request, f"{count} faturas do ano {ano_atual} foram apagadas e o estoque foi devolvido.")
    else:
        messages.warning(request, "Nenhuma fatura do ano atual foi selecionada para resetar.")

# --- FIM DA NOVA AÇÃO ---


class ItemFaturaInline(admin.TabularInline):
    model = ItemFatura
    extra = 1

@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ('numero_fatura', 'cliente', 'data_emissao', 'total_final', 'paga')
    readonly_fields = ('subtotal', 'valor_igv', 'total_final')
    inlines = [ItemFaturaInline]
    # Adiciona a nova ação ao admin das faturas
    actions = [resetar_numeracao]

# Registos simples para os outros modelos
admin.site.register(Produto)
admin.site.register(Cliente)
admin.site.register(DadosEmpresa)

# Personalização dos títulos do Admin
admin.site.site_header = "Administração - SOMAGEC MINING BISSAU"
admin.site.site_title = "Portal de Administração"
admin.site.index_title = "Bem-vindo ao Portal de Administração"