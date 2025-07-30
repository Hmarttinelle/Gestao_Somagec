# Ficheiro: stock/templatetags/stock_tags.py

from django import template

register = template.Library()

@register.simple_tag
def url_params_minus_page(request_get):
    """
    Retorna os parâmetros da URL (Query String) do request.GET,
    mas remove o parâmetro 'page' para evitar duplicação na paginação.
    """
    params = request_get.copy()
    params.pop('page', None)  # Remove a chave 'page' de forma segura
    return params.urlencode()