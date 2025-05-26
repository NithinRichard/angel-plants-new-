import os
import sys
from django.core.wsgi import get_wsgi_application
from django.conf import settings

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')

# Get the WSGI application
application = get_wsgi_application()

def handler(request, context):
    """Handle the request using Django's WSGI application"""
    response = application({
        'REQUEST_METHOD': request.method,
        'PATH_INFO': request.path,
        'QUERY_STRING': request.query_string,
        'wsgi.input': request.body,
        'wsgi.errors': sys.stderr,
        'wsgi.url_scheme': 'https' if request.is_secure else 'http',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'SERVER_NAME': request.host,
        'SERVER_PORT': '443' if request.is_secure else '80',
        'CONTENT_TYPE': request.content_type or '',
        'CONTENT_LENGTH': str(len(request.body)) if request.body else '',
        **request.headers
    })
    
    # Convert the WSGI response to a Vercel response
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': b''.join(response.streaming_content if hasattr(response, 'streaming_content') else [response.content]).decode('utf-8')
    }
