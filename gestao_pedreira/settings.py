# Versão Final

from pathlib import Path
from django.utils.translation import gettext_lazy as _
import os
import dj_database_url # Importa a biblioteca para a base de dados

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# --- CONFIGURAÇÕES DE PRODUÇÃO (MODIFICADAS) ---

# SECURITY WARNING: keep the secret key used in production secret!
# A chave secreta agora é lida de uma variável de ambiente para segurança.
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-+ry1ntjps!m4lnepj20qzpp*mw*2q#f_td3=kvs63f^qx&2koz')

# SECURITY WARNING: don't run with debug turned on in production!
# O modo DEBUG será 'False' online e 'True' apenas se você definir a variável localmente.
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# A Render vai configurar os hosts permitidos automaticamente.
ALLOWED_HOSTS = []
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# --- FIM DAS MODIFICAÇÕES DE PRODUÇÃO ---


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # Adicionado para ficheiros estáticos
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'stock',
    'cloudinary',          # <-- ADICIONE AQUI
    'cloudinary_storage',  # <-- E AQUI
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Adicionado para ficheiros estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', 
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gestao_pedreira.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Recomendo ter um DIRS global
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', # Adicionado o 'debug'
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gestao_pedreira.wsgi.application'


# Database
# Configuração dinâmica: usa PostgreSQL online e SQLite localmente.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}",
        conn_max_age=600
    )
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
LANGUAGE_CODE = 'pt'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [ os.path.join(BASE_DIR, 'locale'), ]


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Login/Logout URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# As configurações de email já usam variáveis de ambiente, o que é perfeito!
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASS')

# --- CONFIGURAÇÃO DO CLOUDINARY PARA FICHEIROS DE MÉDIA ---
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

# Diz ao Django para usar o Cloudinary para todos os ficheiros de média
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'