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
default_hosts = 'localhost,127.0.0.1,cosmos-prod.up.railway.app,cosmos.almaintel.com'
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default=default_hosts, cast=lambda v: [s.strip() for s in v.split(',')])

# CSRF trusted origins for Railway
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://cosmos-prod.up.railway.app,https://cosmos.almaintel.com',
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

# Second PostgreSQL database for events
# Try to get EVENTS_DATABASE_URL first (Railway format)
events_database_url = config('EVENTS_DATABASE_URL', default=None)

if events_database_url:
    # Remove quotes if present
    events_database_url = events_database_url.strip('"').strip("'")
    # Skip if it's still a variable reference (not expanded)
    if events_database_url and not events_database_url.startswith('${{'):
        # Add events database to DATABASES
        DATABASES['events'] = dj_database_url.parse(events_database_url)
    else:
        events_database_url = None

if not events_database_url or events_database_url.startswith('${{'):
    # Fall back to individual environment variables for events database
    DATABASES['events'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('EVENTS_DB_NAME', default='events_db'),
        'USER': config('EVENTS_DB_USER', default='postgres'),
        'PASSWORD': config('EVENTS_DB_PASSWORD', default=''),
        'HOST': config('EVENTS_DB_HOST', default='localhost'),
        'PORT': config('EVENTS_DB_PORT', default='5432'),
    }

# Events database table name (configurable)
EVENTS_TABLE_NAME = config('EVENTS_TABLE_NAME', default='events')
EVENTS_CONVERSATION_ID_COLUMN = config('EVENTS_CONVERSATION_ID_COLUMN', default='conversation_infobip_uuid')
EVENTS_TIMESTAMP_COLUMN = config('EVENTS_TIMESTAMP_COLUMN', default='datetime')
EVENTS_ORIGIN_COLUMN = config('EVENTS_ORIGIN_COLUMN', default='dialogue')

# Third PostgreSQL database for conversations
# Try to get CONVERSATIONS_DATABASE_URL first (Railway format)
conversations_database_url = config('CONVERSATIONS_DATABASE_URL', default=None)

if conversations_database_url:
    # Remove quotes if present
    conversations_database_url = conversations_database_url.strip('"').strip("'")
    # Skip if it's still a variable reference (not expanded)
    if conversations_database_url and not conversations_database_url.startswith('${{'):
        # Add conversations database to DATABASES
        DATABASES['conversations'] = dj_database_url.parse(conversations_database_url)
    else:
        conversations_database_url = None

if not conversations_database_url or conversations_database_url.startswith('${{'):
    # Fall back to individual environment variables for conversations database
    DATABASES['conversations'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('CONVERSATIONS_DB_NAME', default='conversations'),
        'USER': config('CONVERSATIONS_DB_USER', default='postgres'),
        'PASSWORD': config('CONVERSATIONS_DB_PASSWORD', default=''),
        'HOST': config('CONVERSATIONS_DB_HOST', default='localhost'),
        'PORT': config('CONVERSATIONS_DB_PORT', default='5432'),
    }

# Database routing for conversations models
DATABASE_ROUTERS = ['conversations.db_router.ConversationsRouter']

# Fourth PostgreSQL database for followups
# Try to get FOLLOWUPS_DATABASE_URL first (Railway format)
followups_database_url = config('FOLLOWUPS_DATABASE_URL', default=None)

if followups_database_url:
    # Remove quotes if present
    followups_database_url = followups_database_url.strip('"').strip("'")
    # Skip if it's still a variable reference (not expanded)
    if followups_database_url and not followups_database_url.startswith('${{'):
        # Add followups database to DATABASES
        DATABASES['followups'] = dj_database_url.parse(followups_database_url)
    else:
        followups_database_url = None

if not followups_database_url or followups_database_url.startswith('${{'):
    # Fall back to individual environment variables for followups database
    DATABASES['followups'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('FOLLOWUPS_DB_NAME', default='followups_db'),
        'USER': config('FOLLOWUPS_DB_USER', default='postgres'),
        'PASSWORD': config('FOLLOWUPS_DB_PASSWORD', default=''),
        'HOST': config('FOLLOWUPS_DB_HOST', default='localhost'),
        'PORT': config('FOLLOWUPS_DB_PORT', default='5432'),
    }

# Followups database table name (configurable)
FOLLOWUPS_TABLE_NAME = config('FOLLOWUPS_TABLE_NAME', default='follow_up')
FOLLOWUPS_AGENT_ID_COLUMN = config('FOLLOWUPS_AGENT_ID_COLUMN', default='agent_uuid')
FOLLOWUPS_TIMESTAMP_COLUMN = config('FOLLOWUPS_TIMESTAMP_COLUMN', default='follow_up_date')

# Fifth PostgreSQL database for analytics
# Try to get ANALYTICS_DATABASE_URL first (Railway format)
analytics_database_url = config('ANALYTICS_DATABASE_URL', default=None)

if analytics_database_url:
    # Remove quotes if present
    analytics_database_url = analytics_database_url.strip('"').strip("'")
    # Skip if it's still a variable reference (not expanded)
    if analytics_database_url and not analytics_database_url.startswith('${{'):
        # Add analytics database to DATABASES
        DATABASES['analytics'] = dj_database_url.parse(analytics_database_url)
    else:
        analytics_database_url = None

if not analytics_database_url or analytics_database_url.startswith('${{'):
    # Fall back to individual environment variables for analytics database
    DATABASES['analytics'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('ANALYTICS_DB_NAME', default='followups_db'),
        'USER': config('ANALYTICS_DB_USER', default='postgres'),
        'PASSWORD': config('ANALYTICS_DB_PASSWORD', default=''),
        'HOST': config('ANALYTICS_DB_HOST', default='localhost'),
        'PORT': config('ANALYTICS_DB_PORT', default='5432'),
    }

# Analytics database table name (configurable)
ANALYTICS_TABLE_NAME = config('ANALYTICS_TABLE_NAME', default='analytics')
ANALYTICS_AGENT_ID_COLUMN = config('ANALYTICS_AGENT_ID_COLUMN', default='agent_uuid')
ANALYTICS_TIMESTAMP_COLUMN = config('ANALYTICS_TIMESTAMP_COLUMN', default='created_at')

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
LOGIN_REDIRECT_URL = '/'  # Redirects to workspace (root)
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Custom authentication backend for single admin user
AUTHENTICATION_BACKENDS = [
    'conversations.authentication.SingleAdminBackend',
    'django.contrib.auth.backends.ModelBackend',  # Keep default for admin panel
]

# Hardcoded admin password hash (username: admin, password: TPVzYdZz2gNggOx-aVNk7w)
ADMIN_PASSWORD_HASH = config('ADMIN_PASSWORD_HASH', default='2131a8f17431fb7d944a05e6d8c1877437bbe5003fa82810a0c6702e10fab378')

# Chatbase Config
CHATBASE_AGENT_ID = config('CHATBASE_AGENT_ID', default='')
CHATBASE_SECRET_KEY = config('CHATBASE_SECRET_KEY', default='')

# Conversation Links Config
INFOBIP_CONVERSATIONS_URL = config('INFOBIP_CONVERSATIONS_URL', default='https://portal-ny2.infobip.com/conversations/my-work?conversationId=')
SHORT_LINK_DOMAIN = config('SHORT_LINK_DOMAIN', default='https://followupsbot-prod.up.railway.app/r/')