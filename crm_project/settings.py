"""
Django settings for crm_project project.
"""

from pathlib import Path
from decouple import config
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# Allow Railway domain and any configured hosts
default_hosts = 'localhost,127.0.0.1,cosmos-prod.up.railway.app'
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default=default_hosts, cast=lambda v: [s.strip() for s in v.split(',')])

# CSRF trusted origins for Railway
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://cosmos-prod.up.railway.app',
    cast=lambda v: [s.strip() for s in v.split(',')]
)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'conversations',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'crm_project.urls'

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

WSGI_APPLICATION = 'crm_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# PostgreSQL Configuration
# Railway provides DATABASE_URL, but we also support individual variables

# Try to get DATABASE_URL first (Railway format)
# Railway variable references like ${{Service.Variable}} should be expanded by Railway
# But if it comes through with quotes, strip them
database_url = config('DATABASE_URL', default=None)

if database_url:
    # Remove quotes if present (Railway sometimes passes quoted values)
    database_url = database_url.strip('"').strip("'")
    # Skip if it's still a variable reference (not expanded)
    if database_url and not database_url.startswith('${{'):
        # Parse DATABASE_URL (Railway format: postgresql://user:password@host:port/dbname)
        DATABASES = {
            'default': dj_database_url.parse(database_url)
        }
    else:
        # Variable not expanded, use fallback
        database_url = None

if not database_url or database_url.startswith('${{'):
    # Fall back to individual environment variables
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='railway'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

# MongoDB Configuration
# Support both MONGO_URL (Railway) and MONGODB_URL (legacy)
# Check for MONGO_URL first, then fall back to MONGODB_URL
if os.environ.get('MONGO_URL'):
    MONGODB_URL = config('MONGO_URL')
else:
    MONGODB_URL = config('MONGODB_URL', default='mongodb://localhost:27017/')
MONGODB_DB_NAME = config('MONGODB_DB_NAME', default='crm_db')
MONGODB_COLLECTION_NAME = config('MONGODB_COLLECTION_NAME', default='conversations')


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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# WhiteNoise configuration for static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Authentication settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Custom authentication backend for single admin user
AUTHENTICATION_BACKENDS = [
    'conversations.authentication.SingleAdminBackend',
    'django.contrib.auth.backends.ModelBackend',  # Keep default for admin panel
]

# Hardcoded admin password hash (username: admin, password: TPVzYdZz2gNggOx-aVNk7w)
ADMIN_PASSWORD_HASH = config('ADMIN_PASSWORD_HASH', default='2131a8f17431fb7d944a05e6d8c1877437bbe5003fa82810a0c6702e10fab378')

