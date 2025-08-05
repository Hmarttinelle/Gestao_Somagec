# --- Ficheiro Corrigido: stock/urls.py ---

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    
    # URLs de Faturas
    path('faturas/nova/', views.criar_fatura_view, name='criar_fatura'),
    path('faturas/', views.lista_faturas_view, name='lista_faturas'),
    path('faturas/<int:fatura_id>/', views.detalhe_fatura_view, name='detalhe_fatura'),
    path('faturas/<int:fatura_id>/editar/', views.editar_fatura_view, name='editar_fatura'),
    path('faturas/<int:fatura_id>/toggle_paga/', views.toggle_fatura_paga_view, name='toggle_fatura_paga'),
    path('faturas/<int:fatura_id>/print/', views.fatura_print_view, name='fatura_print'),
    path('faturas/<int:fatura_id>/pdf/', views.fatura_pdf_view, name='fatura_pdf'),
    path('faturas/<int:fatura_id>/enviar_email/', views.enviar_fatura_email_view, name='enviar_fatura_email'),
    path('faturas/<int:fatura_id>/criar_guia/', views.criar_guia_desde_fatura_view, name='criar_guia_desde_fatura'),

    # URLs de Clientes
    path('clientes/', views.lista_clientes_view, name='lista_clientes'),
    path('clientes/adicionar/', views.adicionar_cliente_view, name='adicionar_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.editar_cliente_view, name='editar_cliente'),
    path('clientes/<int:cliente_id>/apagar/', views.apagar_cliente_view, name='apagar_cliente'),
    
    # URLs de Produtos
    path('produtos/', views.lista_produtos_view, name='lista_produtos'),
    path('produtos/adicionar/', views.adicionar_produto_view, name='adicionar_produto'),
    path('produtos/<int:produto_id>/editar/', views.editar_produto_view, name='editar_produto'),
    path('produtos/<int:produto_id>/apagar/', views.apagar_produto_view, name='apagar_produto'),

    # URLs PARA GUIAS DE TRANSPORTE
    path('guias/', views.lista_guias_view, name='lista_guias'),
    path('guias/<int:guia_id>/', views.detalhe_guia_view, name='detalhe_guia'),
    path('guias/<int:guia_id>/editar/', views.editar_guia_view, name='editar_guia'),
    path('guias/<int:guia_id>/print/', views.guia_print_view, name='guia_print'),
    path('guias/<int:guia_id>/pdf/', views.guia_pdf_view, name='guia_pdf'), # <-- NOVA ROTA
    path('guias/<int:guia_id>/enviar_email/', views.enviar_guia_email_view, name='enviar_guia_email'),
]