#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime

def backup_database():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()
    
    from django.conf import settings
    from django.core import management
    
    # Create backups directory if it doesn't exist
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'db_backup_{timestamp}.json')
    
    print(f"\n=== Creating database backup: {backup_file} ===")
    
    # Dump database to JSON, excluding contenttypes, auth.Permission, and profiles app if it exists
    with open(backup_file, 'w', encoding='utf-8') as f:
        try:
            management.call_command('dumpdata', 
                                '--exclude=contenttypes', 
                                '--exclude=auth.Permission',
                                '--exclude=profiles',  # Exclude profiles app if it exists
                                stdout=f)
        except Exception as e:
            print(f"Warning: {str(e)}")
            print("Continuing with backup...")
            management.call_command('dumpdata', 
                                '--exclude=contenttypes', 
                                '--exclude=auth.Permission',
                                stdout=f)
    
    print(f"Backup created successfully at: {backup_file}\n")

if __name__ == "__main__":
    backup_database()
