# ficheiro: gestao_pedreira/urls.py

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
# NOVOS IMPORTS
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('stock.urls')),
]

# NOVA LINHA PARA SERVIR FICHEIROS DE MÉDIA EM DESENVOLVIMENTO
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)