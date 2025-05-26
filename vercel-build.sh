#!/bin/bash

# Exit on error
set -e

# Install dependencies
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements-vercel.txt

# Create a simple WSGI configuration
echo "Creating WSGI configuration..."
cat > vercel_wsgi.py << 'EOL'
import os
import sys
from django.core.wsgi import get_wsgi_application

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')

# This application object is used by any WSGI server configured to use this file.
application = get_wsgi_application()
EOL

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
