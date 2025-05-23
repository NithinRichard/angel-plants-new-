"""
Test settings for running tests.
"""
from .settings import *  # noqa

# Use an in-memory SQLite database for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable logging
LOGGING = {}

# Use faster password hasher for testing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable caching for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Use a simpler session engine for faster tests
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Disable CSRF for testing
MIDDLEWARE = [
    m for m in MIDDLEWARE 
    if m != 'django.middleware.csrf.CsrfViewMiddleware'
]

# Set test email backend
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Razorpay test credentials
RAZORPAY_KEY_ID = 'test_key_id'
RAZORPAY_KEY_SECRET = 'test_key_secret'
RAZORPAY_WEBHOOK_SECRET = 'test_webhook_secret'
