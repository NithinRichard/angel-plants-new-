#!/bin/bash

# Install Python dependencies
pip install -r requirements.txt

# Install project dependencies
pip install -r ../requirements-vercel.txt

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate
