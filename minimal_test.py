import os
import sys
import django
from django.conf import settings

# Minimal Django settings
settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    },
    INSTALLED_APPS=[
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'store',
    ],
    USE_I18N=True,
    USE_L10N=True,
)

# Set up Django
django.setup()

print("Django setup complete")

# Now try to import the models
try:
    from store.models import Wishlist
    print("Successfully imported Wishlist model!")
except Exception as e:
    print(f"Error importing Wishlist model: {e}")
    raise
