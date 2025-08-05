# ficheiro: stock/admin.py
import os
import shutil
import sqlite3
from datetime import date
from django.conf import settings
from django.utils import timezone
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django import forms
from django.core.mail import EmailMessage, get_connection
from .models import (
    Produto, Cliente, Fatura, ItemFatura, DadosEmpresa, Configuracao, 
    GuiaTransporte, ItemGuia, BackupConfig
)

@admin.action(description=_("Resetar numeração para faturas selecionadas (usar com cuidado)"))
def resetar_numeracao(modeladmin, request, queryset):
    ano_atual = date.today().year
    faturas_para_apagar = queryset.filter(data_emissao__year=ano_atual)
    count = faturas_para_apagar.count()
    if count > 0:
        for fatura in faturas_para_apagar:
            for item in fatura.itens.all():
                if item.quantidade is not None:
                    item.produto.estoque_atual += item.quantidade
                    item.produto.save()
        faturas_para_apagar.delete()
        messages.success(request, f"{count} faturas do ano {ano_atual} foram apagadas e o estoque foi devolvido.")
    else:
        messages.warning(request, "Nenhuma fatura do ano atual foi selecionada para resetar.")

class ItemFaturaInline(admin.TabularInline):
    model = ItemFatura
    extra = 1
    fields = ('produto', 'quantidade', 'preco_unitario', 'get_subtotal_display')
    readonly_fields = ('get_subtotal_display',)
    
    @admin.display(description=_('Subtotal (CFA)'))
    def get_subtotal_display(self, obj):
        if obj.subtotal is not None:
            formatted_num = "{:,.2f}".format(obj.subtotal)
            return formatted_num.replace(",", "X").replace(".", ",").replace("X", ".")
        return "0,00"

@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ('numero_fatura', 'cliente', 'data_emissao', 'formatted_total_geral', 'formatted_valor_a_pagar', 'paga')
    readonly_fields = ('subtotal', 'valor_desconto', 'subtotal_apos_desconto', 'valor_igv', 'total_geral', 'valor_a_pagar')
    inlines = [ItemFaturaInline]
    list_filter = ('paga', 'data_emissao', 'cliente')
    search_fields = ('numero_fatura', 'cliente__nome')
    actions = [resetar_numeracao]

    @admin.display(description=_('Total Geral (CFA)'), ordering='total_geral')
    def formatted_total_geral(self, obj):
        if obj.total_geral is not None:
            formatted_num = "{:,.2f}".format(obj.total_geral)
            return formatted_num.replace(",", "X").replace(".", ",").replace("X", ".")
        return "0,00"

    @admin.display(description=_('Valor a Pagar (CFA)'), ordering='valor_a_pagar')
    def formatted_valor_a_pagar(self, obj):
        if obj.valor_a_pagar is not None:
            formatted_num = "{:,.2f}".format(obj.valor_a_pagar)
            return formatted_num.replace(",", "X").replace(".", ",").replace("X", ".")
        return "0,00"

class ItemGuiaInline(admin.TabularInline):
    model = ItemGuia
    extra = 1

@admin.register(GuiaTransporte)
class GuiaTransporteAdmin(admin.ModelAdmin):
    list_display = ('numero_guia', 'get_cliente', 'data_emissao', 'morada_descarga', 'matricula_veiculo')
    inlines = [ItemGuiaInline]
    list_filter = ('data_emissao', 'fatura__cliente')
    search_fields = ('numero_guia', 'fatura__cliente__nome', 'matricula_veiculo')
    readonly_fields = ('fatura',)

    @admin.display(description=_('Cliente'), ordering='fatura__cliente__nome')
    def get_cliente(self, obj):
        return obj.fatura.cliente if obj.fatura else None

class ConfiguracaoAdminForm(forms.ModelForm):
    password_remetente = forms.CharField(widget=forms.PasswordInput, required=False)
    class Meta:
        model = Configuracao
        fields = '__all__'

@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    form = ConfiguracaoAdminForm
    fieldsets = (
        (_('Alertas'), {'fields': ('limite_alerta_estoque',)}),
        (_('Configurações de Envio de Email'), {
            'fields': ('email_remetente', 'password_remetente'),
            'description': _("Insira aqui as credenciais do email que será usado para enviar faturas e guias.")
        }),
    )
    def has_add_permission(self, request): return not Configuracao.objects.exists()
    def has_delete_permission(self, request, obj=None): return False

@admin.register(BackupConfig)
class BackupConfigAdmin(admin.ModelAdmin):
    @admin.action(description=_("Executar Backup por Email Agora"))
    def run_backup_now(self, request, queryset):
        config = queryset.first()
        if not config:
            self.message_user(request, _("Nenhuma configuração de backup selecionada."), messages.ERROR)
            return
        temp_backup_dir = os.path.join(settings.BASE_DIR, 'temp_backup_dir')
        try:
            if not config.recipient_email: raise ValueError(_("Email de destino para backups não configurado."))
            email_config = Configuracao.objects.first()
            if not email_config or not email_config.email_remetente or not email_config.password_remetente:
                 raise ValueError(_("Email de envio ou palavra-passe não configurados nas Configurações Gerais."))
            os.makedirs(temp_backup_dir, exist_ok=True)
            timestamp = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
            db_path = settings.DATABASES['default']['NAME']
            backup_db_path = os.path.join(temp_backup_dir, f'db_backup_{timestamp}.sqlite3')
            shutil.copyfile(db_path, backup_db_path)
            zip_path = shutil.make_archive(os.path.join(temp_backup_dir, f'media_backup_{timestamp}'), 'zip', settings.MEDIA_ROOT)
            subject = _("Backup do Sistema Pedreira - {}").format(timestamp)
            body = _("Em anexo seguem os ficheiros de backup do sistema (base de dados e ficheiros de media).")
            email = EmailMessage(subject, body, email_config.email_remetente, [config.recipient_email])
            email.attach_file(backup_db_path)
            email.attach_file(zip_path)
            connection = get_connection(host=settings.EMAIL_HOST, port=settings.EMAIL_PORT, username=email_config.email_remetente, password=email_config.password_remetente, use_tls=settings.EMAIL_USE_TLS)
            connection.send_messages([email])
            config.last_backup_status = _("Sucesso")
            self.message_user(request, _("Backup enviado por email com sucesso para {}!").format(config.recipient_email))
        except Exception as e:
            config.last_backup_status = _("Falhou: {}").format(str(e))
            self.message_user(request, _("Ocorreu um erro durante o backup: {}").format(e), messages.ERROR)
        finally:
            config.last_backup_time = timezone.now()
            config.save()
            if os.path.exists(temp_backup_dir): shutil.rmtree(temp_backup_dir)

    actions = ['run_backup_now']
    fieldsets = (
        (_('Configuração do Backup'), {'fields': ('recipient_email', 'schedule')}),
        (_('Estado do Último Backup'), {'fields': ('last_backup_status', 'last_backup_time',),}),
    )
    readonly_fields = ('last_backup_status', 'last_backup_time')
    def has_add_permission(self, request): return not BackupConfig.objects.exists()
    def has_delete_permission(self, request, obj=None): return False

admin.site.register(Produto)
admin.site.register(Cliente)
admin.site.register(DadosEmpresa)

admin.site.site_header = "Administração - SOMAGEC MINING BISSAU"
admin.site.site_title = "Portal de Administração"
admin.site.index_title = "Bem-vindo ao Portal de Administração"