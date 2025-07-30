# stock/models.py --- FICHEIRO COMPLETO E CORRIGIDO

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.conf import settings
from datetime import date, timedelta

class Produto(models.Model):
    UNIDADES = [('ton', _('Tonelada')), ('m3', _('Metro Cúbico')), ('un', _('Unidade'))]
    nome = models.CharField(_('nome'), max_length=100)
    calibre = models.CharField(_('calibre'), max_length=50, blank=True)
    descricao = models.TextField(_('descrição'), blank=True)
    unidade_medida = models.CharField(_('unidade de medida'), max_length=3, choices=UNIDADES, default='ton')
    estoque_atual = models.DecimalField(_('estoque atual'), max_digits=10, decimal_places=2, default=0.00)
    preco_por_unidade = models.DecimalField(_('preço por unidade'), max_digits=10, decimal_places=2)
    # --- CAMPOS DE HISTÓRICO ADICIONADOS ---
    criado_em = models.DateTimeField(auto_now_add=True, null=True)
    atualizado_em = models.DateTimeField(auto_now=True, null=True)
    utilizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos_criados')
    modificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='produtos_modificados')
    def __str__(self): return f"{self.nome} ({self.calibre})" if self.calibre else self.nome
    @property
    def foi_modificado(self):
        if not self.criado_em or not self.atualizado_em:
            return False
        return self.atualizado_em > self.criado_em + timedelta(seconds=1)
    
    class Meta:
        verbose_name = _("Produto")
        verbose_name_plural = _("Produtos")

class Cliente(models.Model):
    nome = models.CharField(_('nome'), max_length=200)
    nif = models.CharField(_('NIF/Contribuinte'), max_length=50, blank=True)
    endereco = models.CharField(_('endereço'), max_length=255, blank=True)
    telefone = models.CharField(_('telefone'), max_length=50, blank=True)
    email = models.EmailField(_('email'), blank=True)
    # --- CAMPOS DE HISTÓRICO ADICIONADOS ---
    criado_em = models.DateTimeField(auto_now_add=True, null=True)
    atualizado_em = models.DateTimeField(auto_now=True, null=True)
    utilizador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_criados')
    modificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_modificados')
    @property
    def foi_modificado(self):
        if not self.criado_em or not self.atualizado_em:
            return False
        return self.atualizado_em > self.criado_em + timedelta(seconds=1)
    def __str__(self): return self.nome

    class Meta:
        verbose_name = _("Cliente")
        verbose_name_plural = _("Clientes")

class Fatura(models.Model):
    cliente = models.ForeignKey(Cliente, verbose_name=_('cliente'), on_delete=models.PROTECT)
    utilizador = models.ForeignKey(User, verbose_name=_('Criado por'), on_delete=models.SET_NULL, null=True, blank=True)
    data_emissao = models.DateField(_('data de emissão'), default=timezone.now)
    modificado_por = models.ForeignKey(User, related_name='faturas_modificadas', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Modificado por'))
    numero_fatura = models.CharField(_('número da fatura'), max_length=50, unique=True, blank=True)
    paga = models.BooleanField(_('paga'), default=False)
    taxa_igv = models.DecimalField(_('Taxa IGV (%)'), max_digits=5, decimal_places=2, default=17.00)
    
    desconto = models.DecimalField(_('desconto (%)'), max_digits=5, decimal_places=2, default=0.00, help_text=_("Percentagem de desconto (ex: 5 para 5%)"))
    adiantamento = models.DecimalField(_('adiantamento (€)'), max_digits=10, decimal_places=2, default=0.00, help_text=_("Valor do adiantamento em euros"))

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)


    @property
    def subtotal(self): 
        return sum(item.subtotal for item in self.itens.all()) if self.itens.all() else Decimal('0.00')

    @property
    def valor_desconto(self):
        return self.subtotal * (self.desconto / Decimal(100))

    @property
    def subtotal_apos_desconto(self):
        return self.subtotal - self.valor_desconto

    @property
    def valor_igv(self): 
        return self.subtotal_apos_desconto * (self.taxa_igv / Decimal(100))

    @property
    def total_geral(self): 
        return self.subtotal_apos_desconto + self.valor_igv

    @property
    def valor_a_pagar(self):
        valor_final = self.total_geral - self.adiantamento
        return max(valor_final, Decimal('0.00'))

    # --- FUNÇÃO ADICIONADA AQUI ---
    @property
    def foi_modificada(self):
        # Lógica: se a data de atualização for mais de 1 segundo
        # depois da data de criação, consideramos como modificada.
        if not self.criado_em or not self.atualizado_em:
            return False
        return self.atualizado_em > self.criado_em + timedelta(seconds=1)
    
    def __str__(self): return f"Fatura {self.numero_fatura} - {self.cliente.nome}" if self.numero_fatura else f"Nova Fatura para {self.cliente.nome}"

    class Meta:
        verbose_name = _("Fatura")
        verbose_name_plural = _("Faturas")

class ItemFatura(models.Model):
    fatura = models.ForeignKey(Fatura, related_name='itens', on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, verbose_name=_('produto'), on_delete=models.PROTECT)
    quantidade = models.DecimalField(_('quantidade'), max_digits=10, decimal_places=2, null=True, blank=True)
    preco_unitario = models.DecimalField(_('preço unitário'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    @property
    def subtotal(self):
        if self.quantidade and self.preco_unitario:
            return self.quantidade * self.preco_unitario
        return Decimal('0.00')
    
    def __str__(self): 
        if self.quantidade and self.produto:
            return f"{self.quantidade} x {self.produto.nome}"
        return _("Novo item de fatura")

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

class Configuracao(models.Model):
    limite_alerta_estoque = models.PositiveIntegerField(_('Limite para Alerta de Estoque Baixo'), default=10, help_text=_("Quando o estoque de um produto for igual ou inferior a este valor, será mostrado um alerta."))
    email_remetente = models.EmailField(_('Email de Envio'), max_length=255, blank=True, help_text=_("O endereço de email que será usado para enviar as faturas e guias (ex: seu.email@gmail.com)."))
    password_remetente = models.CharField(_('Password de Aplicação do Email'), max_length=255, blank=True, help_text=_("A palavra-passe de aplicação de 16 caracteres gerada pelo seu provedor de email (ex: Gmail)."))

    def __str__(self):
        return str(_("Configurações Gerais"))

    def save(self, *args, **kwargs):
        if not self.pk and Configuracao.objects.exists():
            raise ValidationError(_('Só pode existir uma instância de Configuração. Edite a existente.'))
        return super(Configuracao, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _("Configuração")
        verbose_name_plural = _("Configurações")

class GuiaTransporte(models.Model):
    fatura = models.OneToOneField(Fatura, verbose_name=_('fatura de origem'), on_delete=models.CASCADE, related_name='guia_transporte')
    utilizador = models.ForeignKey(User, verbose_name=_('Criado por'), on_delete=models.SET_NULL, null=True, blank=True)
    data_emissao = models.DateField(_('data de emissão'), default=timezone.now)
    numero_guia = models.CharField(_('número da guia'), max_length=50, unique=True, blank=True)
    morada_carga = models.CharField(_('morada de carga'), max_length=255, help_text=_("Local onde os bens são carregados."))
    morada_descarga = models.CharField(_('morada de descarga'), max_length=255, help_text=_("Local onde os bens são descarregados."))
    matricula_veiculo = models.CharField(_('matrícula do veículo'), max_length=50, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    @property
    def cliente(self):
        return self.fatura.cliente

    def __str__(self):
        return f"Guia #{self.numero_guia} - {self.fatura.cliente.nome}"

    class Meta:
        verbose_name = _("Guia de Transporte")
        verbose_name_plural = _("Guias de Transporte")
        ordering = ['-data_emissao', '-numero_guia']

class ItemGuia(models.Model):
    guia = models.ForeignKey(GuiaTransporte, related_name='itens', on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, verbose_name=_('produto'), on_delete=models.PROTECT)
    quantidade = models.DecimalField(_('quantidade'), max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade} x {self.produto.nome} na Guia #{self.guia.numero_guia}"

    class Meta:
        verbose_name = _("Item da Guia")
        verbose_name_plural = _("Itens da Guia")

class BackupConfig(models.Model):
    SCHEDULE_CHOICES = [
        ('MANUAL', _('Manual (apenas através do botão no admin)')),
        ('DIARIO', _('Diário')),
        ('SEMANAL', _('Semanal')),
    ]
    schedule = models.CharField(
        _('Frequência do Backup Automático'),
        max_length=10,
        choices=SCHEDULE_CHOICES,
        default='MANUAL',
        help_text=_("Define a frequência com que os backups automáticos devem ser executados.")
    )
    recipient_email = models.EmailField(
        _('Email de Destino para Backups'),
        help_text=_("O endereço de email para onde os ficheiros de backup serão enviados.")
    )
    last_backup_status = models.CharField(
        _('Estado do Último Backup'),
        max_length=255,
        default=_("Nunca executado"),
        editable=False
    )
    last_backup_time = models.DateTimeField(
        _('Data do Último Backup'),
        null=True,
        blank=True,
        editable=False
    )

    def __str__(self):
        return str(_("Configuração de Backup por Email"))

    def save(self, *args, **kwargs):
        if not self.pk and BackupConfig.objects.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError(_('Só pode existir uma instância de Configuração de Backup. Edite a existente.'))
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Configuração de Backup")
        verbose_name_plural = _("Configuração de Backup")