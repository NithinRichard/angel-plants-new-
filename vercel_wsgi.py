import os
import sys
from django.core.wsgi import get_wsgi_application

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')

# This application object is used by any WSGI server configured to use this file.
application = get_wsgi_()

# Apply WSGI middleware here if needed
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
