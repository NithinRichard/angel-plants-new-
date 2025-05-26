#!/usr/bin/env bash
# exit on error
set -o errexit

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Update pip and install build dependencies
echo "Upgrading pip and installing build dependencies..."
python -m pip install --upgrade pip
pip install wheel setuptools

# Install system dependencies (for psycopg2)
echo "Installing system dependencies..."
apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements-vercel.txt

# Install additional required packages
pip install gunicorn whitenoise

# Create necessary directories
mkdir -p staticfiles

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser (uncomment and modify as needed)
# echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'password') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

echo "Build completed successfully!"
