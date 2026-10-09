import os
import dj_database_url
from pathlib import Path
from decouple import config, Csv

# ── Base ────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ────────────────────────────
SECRET_KEY = config(
  'SECRET_KEY',
  default='django-insecure-change-me-in-production'
)

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
  'ALLOWED_HOSTS',
  default='localhost,127.0.0.1,0.0.0.0',
  cast=Csv()
)

# Railway provides RAILWAY_STATIC_URL
# Add it to allowed hosts automatically
RAILWAY_STATIC_URL = os.environ.get(
  'RAILWAY_STATIC_URL', ''
)
if RAILWAY_STATIC_URL:
  ALLOWED_HOSTS.append(RAILWAY_STATIC_URL)

# Allow all Railway subdomains
RAILWAY_PUBLIC_DOMAIN = os.environ.get(
  'RAILWAY_PUBLIC_DOMAIN', ''
)
if RAILWAY_PUBLIC_DOMAIN:
  ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

# ── Applications ─────────────────────────
INSTALLED_APPS = [
  'django.contrib.admin',
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.sessions',
  'django.contrib.messages',
  'django.contrib.staticfiles',
  'rest_framework',
  'rest_framework_simplejwt',
  'rest_framework_simplejwt.token_blacklist',
  'corsheaders',
  'core.apps.CoreConfig',
]

# ── Middleware ───────────────────────────
MIDDLEWARE = [
  'django.middleware.gzip.GZipMiddleware',
  'django.middleware.security.SecurityMiddleware',
  'whitenoise.middleware.WhiteNoiseMiddleware',
  # WhiteNoise must be second after security
  'django.contrib.sessions.middleware.SessionMiddleware',
  'corsheaders.middleware.CorsMiddleware',
  'django.middleware.common.CommonMiddleware',
  'django.middleware.csrf.CsrfViewMiddleware',
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'django.contrib.messages.middleware.MessageMiddleware',
  'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'futb_events.urls'

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

WSGI_APPLICATION = 'futb_events.wsgi.application'

# ── Database ─────────────────────────────
# Uses DATABASE_URL on Railway (PostgreSQL)
# Falls back to local PostgreSQL for dev
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
  # Production — Railway PostgreSQL
  DATABASES = {
    'default': dj_database_url.parse(
      DATABASE_URL,
      conn_max_age=600,
      conn_health_checks=True,
    )
  }
else:
  # Local development — your existing config
  DATABASES = {
    'default': {
      'ENGINE': 'django.db.backends.postgresql',
      'NAME': config('DB_NAME', default='futb_events_db'),
      'USER': config('DB_USER', default='postgres'),
      'PASSWORD': config('DB_PASSWORD', default=''),
      'HOST': config('DB_HOST', default='localhost'),
      'PORT': config('DB_PORT', default='5432'),
    }
  }

# ── Auth ─────────────────────────────────
AUTH_USER_MODEL = 'core.User'

AUTH_PASSWORD_VALIDATORS = [
  {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
  {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
  {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
  {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── REST Framework ───────────────────────
REST_FRAMEWORK = {
  'DEFAULT_AUTHENTICATION_CLASSES': [
    'rest_framework_simplejwt.authentication.JWTAuthentication',
  ],
  'DEFAULT_PERMISSION_CLASSES': [
    'rest_framework.permissions.IsAuthenticated',
  ],
  'DEFAULT_RENDERER_CLASSES': [
    'rest_framework.renderers.JSONRenderer',
  ],
}

# ── JWT ──────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
  'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
  'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
  'ROTATE_REFRESH_TOKENS': True,
  'BLACKLIST_AFTER_ROTATION': True,
  'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS ─────────────────────────────────
# Allow all origins for UAT
# (restrict to specific domains after UAT is complete)
CORS_ALLOW_ALL_ORIGINS = True

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

# ── Internationalisation ─────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# ── Static Files ─────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise compression and caching
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Media Files ──────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ── Email ────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='FUTB Smart Campus <noreply@futb.edu.ng>')

# ── Firebase ─────────────────────────────
FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS_PATH', default='firebase-credentials.json')

# ── Paystack ─────────────────────────────
PAYSTACK_SECRET_KEY = config('PAYSTACK_SECRET_KEY', default='')

# ── Google OAuth ──────────────────────────
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')

# ── Security Headers (production) ────────
if not DEBUG:
  SECURE_BROWSER_XSS_FILTER = True
  SECURE_CONTENT_TYPE_NOSNIFF = True
  X_FRAME_OPTIONS = 'DENY'
  SECURE_HSTS_SECONDS = 3600
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True

# ── Default Field ────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Logging ──────────────────────────────
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'handlers': {
    'console': {
      'class': 'logging.StreamHandler',
    },
  },
  'root': {
    'handlers': ['console'],
    'level': 'INFO',
  },
  'loggers': {
    'django': {
      'handlers': ['console'],
      'level': 'INFO',
      'propagate': False,
    },
    'core': {
      'handlers': ['console'],
      'level': 'INFO',
      'propagate': False,
    },
  },
}
