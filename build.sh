#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install PostgreSQL client (required for psycopg2)
echo "Installing PostgreSQL client..."
sudo apt-get update && sudo apt-get install -y libpq-dev

# Install build dependencies
pip install --upgrade pip
pip install gunicorn whitenoise

# Install project dependencies
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser (uncomment and modify as needed)
# echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@example.com', 'password') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

echo "Build completed successfully!"
