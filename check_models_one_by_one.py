import os
import sys
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
try:
    django.setup()
    print("Django setup complete")
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

# Get all model names from the store app
try:
    from django.apps import apps
    app_config = apps.get_app_config('store')
    model_names = [model.__name__ for model in app_config.get_models()]
    print(f"Found {len(model_names)} models in store app")
    
    # Try to import each model one by one
    for model_name in model_names:
        try:
            print(f"\nTrying to import {model_name}...")
            model = app_config.get_model(model_name)
            print(f"Successfully imported {model_name}")
            print(f"Fields: {[f.name for f in model._meta.get_fields()]}")
        except Exception as e:
            print(f"Error importing {model_name}: {e}")
            
except Exception as e:
    print(f"Error getting models: {e}")
    raise
