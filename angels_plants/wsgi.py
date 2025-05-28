"""
WSGI config for angels_plants project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os
import sys
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

try:
    # Add the project directory to the Python path
    project_path = str(Path(__file__).parent.parent)
    if project_path not in sys.path:
        sys.path.append(project_path)
    
    # Set the default Django settings module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    logger.info("DJANGO_SETTINGS_MODULE set to: %s", os.environ['DJANGO_SETTINGS_MODULE'])
    
    # Import Django and set up the application
    import django
    from django.core.wsgi import get_wsgi_application
    
    # Initialize Django
    django.setup()
    
    # Create the WSGI application
    application = get_wsgi_application()
    logger.info("WSGI application initialized successfully")
    
except Exception as e:
    logger.critical("Failed to initialize WSGI application", exc_info=True)
    if 'application' not in locals():
        # If we can't create the application, return a simple 500 response
        from django.http import HttpResponseServerError
        from django.conf import settings
        
        def application(environ, start_response):
            response = HttpResponseServerError(
                "Internal Server Error. Check the server logs for more details.",
                content_type="text/plain"
            )
            return response(environ, start_response)
