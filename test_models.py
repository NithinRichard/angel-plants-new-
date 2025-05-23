import os
import sys
import django
from django.conf import settings

# Configure minimal Django settings
DEBUG = True
SECRET_KEY = 'test'
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'store',
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Apply settings
settings.configure(
    DEBUG=DEBUG,
    SECRET_KEY=SECRET_KEY,
    INSTALLED_APPS=INSTALLED_APPS,
    DATABASES=DATABASES,
)

# Set up Django
django.setup()

# Now try to import the models
try:
    from store.models import Wishlist
    print("Successfully imported Wishlist model!")
    print(f"Fields: {[f.name for f in Wishlist._meta.get_fields()]}")
except Exception as e:
    print(f"Error importing Wishlist model: {e}")
    raise
