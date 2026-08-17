"""
Django settings for DebTab.

Every environment-specific value is read from an environment variable (or a local
.env file via python-decouple). Defaults are chosen so that a *missing* variable
fails safe in production rather than silently doing the dangerous thing.
"""

import sys
from pathlib import Path

import dj_database_url
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent


def _csv(name, default=''):
    """Read a comma-separated env var into a clean list."""
    raw = config(name, default=default)
    return [item.strip() for item in raw.split(',') if item.strip()]


# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------

# FIX #6: DEBUG now defaults to False. Previously it defaulted to True, so a
# missing or misspelled env var on the host would silently run production with
# debug enabled, exposing settings, env vars and tracebacks to the public.
DEBUG = config('DEBUG', default=False, cast=bool)

# Are we running a management command that must work without full config?
_RUNNING_SETUP_COMMAND = any(
    cmd in sys.argv for cmd in ('collectstatic', 'makemigrations', 'check')
)

# FIX #7: no hardcoded production secret. A dev fallback is only used when
# DEBUG is on; in production a missing SECRET_KEY is a hard, loud failure
# instead of a site where every session cookie is forgeable.
_DEV_SECRET = 'django-insecure-dev-only-do-not-use-in-production'
SECRET_KEY = config('SECRET_KEY', default='')
if not SECRET_KEY:
    if DEBUG or _RUNNING_SETUP_COMMAND:
        SECRET_KEY = _DEV_SECRET
    else:
        raise RuntimeError(
            'SECRET_KEY environment variable is not set. Refusing to start in '
            'production without one. Set it in the Render dashboard under '
            'Environment > Environment Variables.'
        )

# FIX #4: the real domain is included by default. render.yaml previously
# advertised only ".onrender.com", which meant a redeploy from the blueprint
# produced a site that returned 400 on every single request.
ALLOWED_HOSTS = _csv(
    'ALLOWED_HOSTS',
    default='getdebtab.com,www.getdebtab.com,.onrender.com,localhost,127.0.0.1',
)

# FIX #5: CSRF_TRUSTED_ORIGINS and SECURE_PROXY_SSL_HEADER must be set together.
# Render terminates TLS at its proxy and forwards plain HTTP, so without the
# proxy header Django believes the request is insecure and skips the CSRF
# referer check entirely. Turning on one without the other breaks every form
# on the site with a 403.
CSRF_TRUSTED_ORIGINS = _csv(
    'CSRF_TRUSTED_ORIGINS',
    default='https://getdebtab.com,https://www.getdebtab.com,https://*.onrender.com',
)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Production hardening. All disabled under DEBUG so local development over
# plain HTTP still works.
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=not DEBUG, cast=bool)
# Render's internal health check reaches the container over plain HTTP. Without
# this exemption the redirect turns every health check into a 301 and Render
# concludes the service is down.
SECURE_REDIRECT_EXEMPT = [r'^healthz$']
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
if not DEBUG:
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Keep people logged in for two weeks rather than dropping them on browser close.
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=1209600, cast=int)

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_bootstrap5',
    'apps.accounts',
    'apps.tournaments',
    'apps.participants',
    'apps.venues',
    'apps.motions',
    'apps.draw',
    'apps.results',
    'apps.standings',
    'apps.feedback',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # serves static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'debtab.urls'

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

WSGI_APPLICATION = 'debtab.wsgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# FIX #2: conn_health_checks=True. conn_max_age keeps connections open for ten
# minutes, but without a health check Django hands a dead socket to the next
# request whenever the database or a connection pooler has closed it in the
# meantime. That produced intermittent, apparently random 500s
# ("server closed the connection unexpectedly") on a free tier that idles out.
#
# FIX #3: SSL is no longer hardcoded off. It was disabled for Railway back in
# commit 2546871 and then silently carried over. Managed Postgres providers
# (Supabase, Neon) require TLS, so this now defaults to on and can be turned
# off only by explicit opt-out.
_database_url = config('DATABASE_URL', default='')

if _database_url:
    DATABASES = {
        'default': dj_database_url.parse(
            _database_url,
            conn_max_age=config('DB_CONN_MAX_AGE', default=600, cast=int),
            conn_health_checks=True,
            ssl_require=config('DB_SSL_REQUIRE', default=True, cast=bool),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='debtab'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 600,
            'CONN_HEALTH_CHECKS': True,
        }
    }

# Connection poolers running in transaction mode (Supabase port 6543, PgBouncer)
# cannot support server-side cursors. Harmless to leave on for a session-mode
# pooler or a direct connection.
DISABLE_SERVER_SIDE_CURSORS = config(
    'DISABLE_SERVER_SIDE_CURSORS', default=False, cast=bool
)

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = config('TIME_ZONE', default='UTC')
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# FIX #10 (bonus): STATICFILES_STORAGE was removed in Django 5.1, so the old
# line was being silently ignored and WhiteNoise's compression was never
# applied. The STORAGES dict is the supported form.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# A template referencing a static file that is not in the manifest raises at
# render time under ManifestStaticFilesStorage, turning a missing icon into a
# site-wide 500. Non-strict mode degrades to serving the unhashed path instead.
WHITENOISE_MANIFEST_STRICT = False
WHITENOISE_MAX_AGE = 31536000

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/tournaments/'
LOGOUT_REDIRECT_URL = '/'

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='DebTab <noreply@getdebtab.com>')
EMAIL_TIMEOUT = 10

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

# FIX #1: this is the change that mattered most. There was no LOGGING config at
# all, so with DEBUG=False Django wrote tracebacks to the 'django.request'
# logger, which had no handler attached — they went nowhere. The result was a
# blank "Server Error (500)" page AND an empty log stream, which is why this
# outage was invisible for weeks. Everything now goes to stderr, which Render
# captures and displays in the Logs tab.

LOG_LEVEL = config('LOG_LEVEL', default='INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stderr,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        # Full tracebacks for any unhandled 500, regardless of DEBUG.
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': config('DB_LOG_LEVEL', default='WARNING'),
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
