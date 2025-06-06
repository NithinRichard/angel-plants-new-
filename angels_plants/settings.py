"""
Django settings for angels_plants project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import configparser

# Build paths inside the project like this: BASE_DIR / 'subdir'
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv()

# Load database configuration from config.ini
config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, 'config.ini'))

# Get database settings from config.ini
DB_ENGINE = config.get('Database', 'ENGINE')
DB_NAME = config.get('Database', 'NAME')
DB_USER = config.get('Database', 'USER')
DB_PASSWORD = config.get('Database', 'PASSWORD')
DB_HOST = config.get('Database', 'HOST')
DB_PORT = config.get('Database', 'PORT')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'  # Change this in production

# SECURITY WARNING: don't run with debug turned on in production!
# Debug settings
DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

# Security settings
ALLOWED_HOSTS = ['nithinrichard.pythonanywhere.com', 'www.angel-plants.com', 'localhost', '127.0.0.1']
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# Add this if you're using HTTPS
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_filters',
    'widget_tweaks',
    'store',
    'payment',
    'accounts',
    'api',
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

ROOT_URLCONF = 'angels_plants.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.media',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart',
            ],
        },
    },
]

WSGI_APPLICATION = 'angels_plants.wsgi.application'

# Database
# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Database configuration using config.ini
DATABASES = {
    'default': {
        'ENGINE': DB_ENGINE,
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'sql_mode': 'traditional',
        },
    }
}

# Password validation
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'staticfiles'),
    os.path.join(BASE_DIR, 'store', 'static'),  # For app-specific static files
]

# Media files (user uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Ensure the directories exist
os.makedirs(STATIC_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT, exist_ok=True)

# URL to use if the authentication system requires a user to log in.
LOGIN_URL = 'accounts:login'

# Default URL to redirect to after a user logs in.
LOGIN_REDIRECT_URL = '/accounts/'

# URL to redirect to after a user logs out.
LOGOUT_REDIRECT_URL = '/'

# The number of days a password reset link is valid for
PASSWORD_RESET_TIMEOUT = 86400  # 1 day in seconds

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Razorpay Configuration - Live Mode
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')

# Verify that required Razorpay credentials are set
if not all([RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET]):
    raise ValueError("Missing Razorpay configuration. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables.")

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'nithinrichard1@gmail.com')  # Your Gmail address
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'xgfg adcs wlhs xvqd')  # Your App Password
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'nithinrichard1@gmail.com')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'noreply@angel-plants.com')

# Test email settings for development
TEST_EMAIL = os.getenv('TEST_EMAIL', 'nithinrichard1@gmail.com')  # Email to send test emails to

# Email timeout in seconds
EMAIL_TIMEOUT = 10

# Ensure logs directory exists
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
try:
    os.makedirs(LOGS_DIR, exist_ok=True)
    # Set permissions if needed (0o755 = rwxr-xr-x)
    os.chmod(LOGS_DIR, 0o755)
except Exception as e:
    print(f"Warning: Could not create logs directory at {LOGS_DIR}: {e}")

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, 'django_errors.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': True,
        },
        'store': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
        '': {  # Root logger
            'handlers': ['console', 'file', 'error_file'],
            'level': 'WARNING',
        },
    },
}


