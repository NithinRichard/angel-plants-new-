"""
WSGI config for angels_plants project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
