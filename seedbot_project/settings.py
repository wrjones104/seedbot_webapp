import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_PATH = BASE_DIR.parent / 'seedbot2000' / '.env'
load_dotenv(dotenv_path=ENV_PATH)

SECRET_KEY = os.getenv('SECRET_KEY')
WC_API_KEY = os.getenv('new_api_key')
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
ENV_TYPE = os.getenv('ENVIRONMENT', 'dev')

if ENV_TYPE == "prod":
    DEBUG = False
    ALLOWED_HOSTS = ['seedbot.net', 'www.seedbot.net']
    CSRF_TRUSTED_ORIGINS = ['https://seedbot.net', 'https://www.seedbot.net']
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Celery settings for Production
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
else:
    DEBUG = True
    ALLOWED_HOSTS = []
    # Celery settings for Development
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'


# --- Celery Configuration Options ---
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'


# --- Application Definition ---
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'django.contrib.sites', 'django.contrib.redirects',
    'presets',
    'allauth', 'allauth.account', 'allauth.socialaccount',
    'allauth.socialaccount.providers.discord',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.redirects.middleware.RedirectFallbackMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'seedbot_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'seedbot_project.wsgi.application'

# --- Database Configuration ---
DATABASES = {
    'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'},
    'seedbot_db': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'seedbot2000' / 'db' / 'seeDBot.sqlite',
    }
}
DATABASE_ROUTERS = ['seedbot_project.db_router.SeedBotRouter']

# --- Password validation, Internationalization, etc. ---
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Static and Media Files ---
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
# This path now correctly points to where the Celery task is saving the seeds.
MEDIA_ROOT = BASE_DIR.parent / 'seedbot2000' / 'WorldsCollide' / 'seeds'


# --- Django-Allauth & Sites Framework ---
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend', 'allauth.account.auth_backends.AuthenticationBackend']
SITE_ID = 1
LOGIN_REDIRECT_URL = '/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SOCIALACCOUNT_PROVIDERS = {
    'discord': {
        'SCOPE': ['identify', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

SOCIALACCOUNT_AUTO_SIGNUP = True

ACCOUNT_EMAIL_VERIFICATION = "none"

SOCIALACCOUNT_LOGIN_ON_GET = True