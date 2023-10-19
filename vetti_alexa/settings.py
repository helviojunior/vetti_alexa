"""
Django settings for vetti_alexa project.

Generated by 'django-admin startproject' using Django 4.2.6.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
from pathlib import Path
import configparser, datetime

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-n^bjx89&*9+0i$i1d8-y@rfsn#r&ng6xv75978-%7__uh9$z2)'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


START_TIME = datetime.datetime.now()
APPEND_SLASH = True
APP_STARTED = int(datetime.datetime.now().timestamp())

SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_EXPIRE_SECONDS = 60 * 60  # 60 minutos


# Application definition

INSTALLED_APPS = [
  'django.contrib.admin',
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.messages',
  'django.contrib.staticfiles',

  'fullurl',
  "django_filters",
  "rest_framework",
  "rest_framework.authtoken",
  'django_crontab',
  'corsheaders',

  'manager'
]

MIDDLEWARE = [
  'django.middleware.security.SecurityMiddleware',
  'django.contrib.sessions.middleware.SessionMiddleware',
  'django_session_timeout.middleware.SessionTimeoutMiddleware',
  'corsheaders.middleware.CorsMiddleware',
  'django.middleware.common.CommonMiddleware',
  'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'django.middleware.clickjacking.XFrameOptionsMiddleware'
]

ROOT_URLCONF = 'vetti_alexa.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'vetti_alexa.wsgi.application'


# Configurações críticas em arquivo .ini
config = configparser.ConfigParser()
config.read(f'{BASE_DIR}/config.ini')

auto_search = True
config_password = None
user_password = None
try:
    auto_search = config['VETTI'].get('auto_search', True)
    config_password = config['VETTI']['config_password'] or None
    user_password = config['VETTI']['user_password'] or None
except:
    pass

VETTI = {
    'auto_search': auto_search,
    'config_password': config_password,
    'user_password': user_password
}

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'pt-BR'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_L10N = True

USE_TZ = False

USE_THOUSAND_SEPARATOR = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'  # Usado para dev
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # usado em produção

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


chat_id = None
bot_id = None
try:
    chat_id = config['TELEGRAM']['chat_id'] or None
    bot_id = config['TELEGRAM']['bot_id'] or None
except:
    pass

TELEGRAM = {
    'chat_id': chat_id,
    'bot_id': bot_id
}

interfaces = []
try:
    interfaces = [i.strip().lower() for i in config['ALEXA']['interfaces'].split(",")]
except:
    pass

ALEXA = {
    'interfaces': interfaces
}

PASSWORD_HASHERS = [
  'django.contrib.auth.hashers.BCryptSHA256PasswordHasher'
]


REST_FRAMEWORK = {
  'DEFAULT_PERMISSION_CLASSES': (
    'rest_framework.permissions.IsAuthenticated',
    # 'rest_framework.permissions.IsAuthenticatedOrReadOnly',
  ),
  'DEFAULT_AUTHENTICATION_CLASSES': (
    'rest_framework.authentication.TokenAuthentication',
    'rest_framework_simplejwt.authentication.JWTAuthentication',
  ),
}


LOGGING = {
  'version': 1,
  'disable_existing_loggers': True,
  'formatters': {
    'standard': {
      'format': "[Manager] [%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
      'datefmt': "%d/%b/%Y %H:%M:%S"
    }
  },
  'handlers': {
    'console': {
      'class': 'logging.StreamHandler',
    },
    'syslog': {
      'class': 'logging.handlers.SysLogHandler',
      'formatter': 'standard',
      'facility': 'user',
      # uncomment next line if rsyslog works with unix socket only (UDP reception disabled)
      # 'address': '/dev/log'
    }
  },
  'loggers': {
    'django': {
      'handlers': ['syslog'],
      'level': 'INFO',
      'disabled': False,
      'propagate': True
    }
  }
}

SESSION_COOKIE_HTTPONLY = True

CORS_ORIGIN_ALLOW_ALL = True  # If this is used then `CORS_ORIGIN_WHITELIST` will not have any effect
CORS_ALLOW_CREDENTIALS = True
# CORS_ORIGIN_WHITELIST = [
#    'http://localhost:3030',
# ] # If this is used, then not need to use `CORS_ORIGIN_ALLOW_ALL = True`
# CORS_ORIGIN_REGEX_WHITELIST = [
#    'http://localhost:3030',
# ]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CRONJOBS = [

    ('* * * * *', 'manager.cron.search_vetti'),
    ('* * * * *', 'manager.cron.alexa_plugs'),

]