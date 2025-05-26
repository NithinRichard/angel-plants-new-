#!/bin/bash

# Exit on error
set -e

# Install dependencies
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements-vercel.txt

# Create the API directory if it doesn't exist
mkdir -p api

# Create the index.py file for Vercel
cat > api/index.py << 'EOL'
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

def handler(event, context):
    """Handle the request using Django's WSGI application"""
    from io import BytesIO
    from urllib.parse import parse_qs
    
    # Parse the event
    body = event.get('body', '')
    if event.get('isBase64Encoded', False):
        import base64
        body = base64.b64decode(body)
    
    # Create WSGI environment
    environ = {
        'REQUEST_METHOD': event.get('httpMethod', 'GET'),
        'PATH_INFO': event.get('path', '/'),
        'QUERY_STRING': event.get('rawQueryString', ''),
        'wsgi.input': BytesIO(body.encode() if isinstance(body, str) else body),
        'wsgi.errors': sys.stderr,
        'wsgi.url_scheme': event.get('headers', {}).get('x-forwarded-proto', 'http'),
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'SERVER_NAME': event.get('headers', {}).get('host', 'localhost'),
        'SERVER_PORT': '443' if event.get('headers', {}).get('x-forwarded-proto') == 'https' else '80',
        'CONTENT_TYPE': event.get('headers', {}).get('content-type', ''),
        'CONTENT_LENGTH': str(len(body)) if body else '',
        **{f'HTTP_{k.upper().replace("-", "_")}': v for k, v in event.get('headers', {}).items()}
    }
    
    # Call the WSGI application
    response = application(environ, lambda status, headers: None)
    
    # Convert the response to the format expected by Vercel
    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': b''.join(response.streaming_content if hasattr(response, 'streaming_content') else [response.content]).decode('utf-8')
    }
EOL

# Create a requirements.txt in the api directory
cp requirements-vercel.txt api/requirements.txt

# Create a runtime.txt in the api directory
echo "python3.9" > api/runtime.txt

# Create a vercel.json file if it doesn't exist
if [ ! -f vercel.json ]; then
    echo "Creating vercel.json..."
    cat > vercel.json << 'EOL2'
{
  "version": 2,
  "builds": [
    {
      "src": "vercel_wsgi.py",
      "use": "@vercel/python"
    },
    {
      "src": "staticfiles/",
      "use": "@vercel/static"
    },
    {
      "src": "media/",
      "use": "@vercel/static"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/media/(.*)",
      "dest": "/media/$1"
    },
    {
      "src": "/admin/.*",
      "dest": "/vercel_wsgi.py"
    },
    {
      "src": "/(.*)",
      "dest": "/vercel_wsgi.py"
    }
  ]
}
EOL2
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "Warning: collectstatic failed but continuing..."

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput || echo "Warning: migrations failed but continuing..."

echo "Build completed successfully!"
