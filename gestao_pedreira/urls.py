# ficheiro: gestao_pedreira/urls.py

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

# 1. IMPORTAR A NOSSA NOVA VIEW
from stock.views import CustomLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),
    
    # 2. SUBSTITUIR auth_views.LoginView PELA NOSSA CustomLoginView
    path('accounts/login/', CustomLoginView.as_view(template_name='registration/login.html'), name='login'),
    
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('stock.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)