"""Settings for the original Django payment coursework, with local secrets externalised."""
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY to a newly generated local secret.')
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = [host.strip() for host in os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'crispy_forms', 'crispy_bootstrap5', 'django_extensions',
    'register.apps.RegisterConfig', 'payapp.apps.PayappConfig', 'rest_framework',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'webapps2026.urls'
INTERNAL_API_BASE = os.environ.get('INTERNAL_API_BASE',
    'http://127.0.0.1:8000' if DEBUG else 'https://localhost:8000')
INTERNAL_API_CA_BUNDLE = os.environ.get('INTERNAL_API_CA_BUNDLE') or True
LOGIN_URL = '/webapps2026/login/'
LOGIN_REDIRECT_URL = '/webapps2026/'
LOGOUT_REDIRECT_URL = '/webapps2026/login/'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.debug',
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'webapps2026.wsgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'webapps.db',
    # SQLite ignores select_for_update(); reserve the writer before reading balances.
    'OPTIONS': {'transaction_mode': 'IMMEDIATE', 'timeout': 20},
}}
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
X_FRAME_OPTIONS = 'DENY'

INITIAL_BALANCE_GBP = 1000
ALLOWED_CURRENCIES = ['GBP', 'USD', 'EUR']
EXCHANGE_RATES = {
    'GBP': {'GBP': 1.00, 'USD': 1.27, 'EUR': 1.17},
    'USD': {'GBP': 0.79, 'USD': 1.00, 'EUR': 0.92},
    'EUR': {'GBP': 0.85, 'USD': 1.09, 'EUR': 1.00},
}
CRISPY_TEMPLATE_PACK = 'bootstrap5'
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
