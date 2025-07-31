# Em stock/context_processors.py

from .models import DadosEmpresa

def dados_empresa_processor(request):
    # Vai buscar o primeiro (e único) objeto DadosEmpresa
    dados = DadosEmpresa.objects.first()
    # Retorna um dicionário que será adicionado a todos os contextos
    return {'dados_empresa': dados}