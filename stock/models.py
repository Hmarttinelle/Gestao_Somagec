# --- Ficheiro Corrigido com Nomes de Modelos Traduzíveis: stock/models.py ---

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.contrib.auth.models import User

class Produto(models.Model):
    UNIDADES = [('ton', _('Tonelada')), ('m3', _('Metro Cúbico')), ('un', _('Unidade'))]
    nome = models.CharField(_('nome'), max_length=100)
    calibre = models.CharField(_('calibre'), max_length=50, blank=True)
    descricao = models.TextField(_('descrição'), blank=True)
    unidade_medida = models.CharField(_('unidade de medida'), max_length=3, choices=UNIDADES, default='ton')
    estoque_atual = models.DecimalField(_('estoque atual'), max_digits=10, decimal_places=2, default=0.00)
    preco_por_unidade = models.DecimalField(_('preço por unidade'), max_digits=10, decimal_places=2)
    def __str__(self): return f"{self.nome} ({self.calibre})" if self.calibre else self.nome
    
    class Meta:
        verbose_name = _("Produto")
        verbose_name_plural = _("Produtos")

class Cliente(models.Model):
    nome = models.CharField(_('nome'), max_length=200)
    nif = models.CharField(_('NIF/Contribuinte'), max_length=50, blank=True)
    endereco = models.CharField(_('endereço'), max_length=255, blank=True)
    telefone = models.CharField(_('telefone'), max_length=50, blank=True)
    email = models.EmailField(_('email'), blank=True)
    def __str__(self): return self.nome

    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")

class Fatura(models.Model):
    cliente = models.ForeignKey(Cliente, verbose_name=_('cliente'), on_delete=models.PROTECT)
    utilizador = models.ForeignKey(User, verbose_name=_('Criado por'), on_delete=models.SET_NULL, null=True, blank=True)
    data_emissao = models.DateField(_('data de emissão'), default=timezone.now)
    numero_fatura = models.CharField(_('número da fatura'), max_length=50, unique=True, blank=True)
    paga = models.BooleanField(_('paga'), default=False)
    taxa_igv = models.DecimalField(_('Taxa IGV (%)'), max_digits=5, decimal_places=2, default=17.00)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    @property
    def subtotal(self): return sum(item.subtotal for item in self.itens.all())
    @property
    def valor_igv(self): return self.subtotal * (self.taxa_igv / Decimal(100))
    @property
    def total_final(self): return self.subtotal + self.valor_igv
    def __str__(self): return f"Fatura {self.numero_fatura} - {self.cliente.nome}"

    class Meta:
        verbose_name = _("Fatura")
        verbose_name_plural = _("Faturas")

class ItemFatura(models.Model):
    fatura = models.ForeignKey(Fatura, related_name='itens', on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, verbose_name=_('produto'), on_delete=models.PROTECT)
    quantidade = models.DecimalField(_('quantidade'), max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField(_('preço unitário'), max_digits=10, decimal_places=2)
    @property
    def subtotal(self): return self.quantidade * self.preco_unitario
    def __str__(self): return f"{self.quantidade} x {self.produto.nome}"

class DadosEmpresa(models.Model):
    nome_empresa = models.CharField(_('Nome da Empresa'), max_length=255)
    logotipo = models.ImageField(_('Logotipo'), upload_to='logos/', null=True, blank=True)
    endereco = models.TextField(_('Endereço'))
    nif = models.CharField(_('NIF'), max_length=50)
    telefone = models.CharField(_('Telefone'), max_length=50)
    email = models.EmailField(_('Email'))
    dados_pagamento = models.TextField(_('Dados de Pagamento'), help_text="Ex: IBAN, conta bancária, etc.")
    def __str__(self): return self.nome_empresa
    class Meta:
        verbose_name = _("Dados da Empresa")
        verbose_name_plural = _("Dados da Empresa")