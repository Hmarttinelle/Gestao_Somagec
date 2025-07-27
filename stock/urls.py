# --- Ficheiro Corrigido: stock/urls.py ---

from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('produtos/', views.lista_produtos_view, name='lista_produtos'),
    path('faturas/nova/', views.criar_fatura_view, name='criar_fatura'),
    path('faturas/', views.lista_faturas_view, name='lista_faturas'),
    path('faturas/<int:fatura_id>/', views.detalhe_fatura_view, name='detalhe_fatura'),
    path('faturas/<int:fatura_id>/editar/', views.editar_fatura_view, name='editar_fatura'),
    path('faturas/<int:fatura_id>/toggle_paga/', views.toggle_fatura_paga_view, name='toggle_fatura_paga'),
    
    # A LINHA QUE ESTAVA EM FALTA
    path('faturas/<int:fatura_id>/print/', views.fatura_print_view, name='fatura_print'),
    path('clientes/', views.lista_clientes_view, name='lista_clientes'),
    path('clientes/adicionar/', views.adicionar_cliente_view, name='adicionar_cliente'),
    path('clientes/<int:cliente_id>/editar/', views.editar_cliente_view, name='editar_cliente'),
    path('clientes/<int:cliente_id>/apagar/', views.apagar_cliente_view, name='apagar_cliente'),
    path('produtos/adicionar/', views.adicionar_produto_view, name='adicionar_produto'),
    path('produtos/<int:produto_id>/editar/', views.editar_produto_view, name='editar_produto'),
    path('produtos/<int:produto_id>/apagar/', views.apagar_produto_view, name='apagar_produto'),
]