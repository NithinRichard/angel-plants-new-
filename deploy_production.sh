#!/bin/bash

# Exit on error
set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx

# Create a systemd service for Gunicorn
sudo tee /etc/systemd/system/gunicorn.service << EOF
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:$(pwd)/angels_plants.sock angels_plants.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
sudo tee /etc/nginx/sites-available/angels_plants << EOF
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root $(pwd);
    }

    location /media/ {
        root $(pwd);
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$(pwd)/angels_plants.sock;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/angels_plants /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx

# Set up PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE yourdbname;"
sudo -u postgres psql -c "CREATE USER yourdbuser WITH PASSWORD 'yourdbpassword';"
sudo -u postgres psql -c "ALTER ROLE yourdbuser SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE yourdbuser SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE yourdbuser SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE yourdbname TO yourdbuser;"

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations and collect static files
python manage.py migrate
python manage.py collectstatic --noinput

# Set proper permissions
sudo chown -R www-data:www-data $(pwd)
sudo chmod -R 755 $(pwd)/static
sudo chmod -R 755 $(pwd)/media

# Start and enable Gunicorn
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# Restart Nginx
sudo systemctl restart nginx

echo "Deployment complete! Your site should now be live."
