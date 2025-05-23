#!/usr/bin/env python
import os
import sys
import django

def setup_database():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()
    
    from django.core.management import execute_from_command_line
    
    print("\n=== Setting up database ===")
    
    # Run migrations
    print("\nRunning migrations...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    # Create superuser if it doesn't exist
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not User.objects.filter(is_superuser=True).exists():
        print("\nCreating superuser...")
        username = input("Enter admin username (default: admin): ") or "admin"
        email = input("Enter admin email: ")
        password = input("Enter admin password: ")
        
        User.objects.create_superuser(username, email, password)
        print("Superuser created successfully!")
    else:
        print("\nSuperuser already exists.")
    
    print("\n=== Database setup complete ===\n")

if __name__ == "__main__":
    setup_database()
