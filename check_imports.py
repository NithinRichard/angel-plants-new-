import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
django.setup()

# Now try to import the models
try:
    from store import models
    print("Successfully imported models!")
    
    # Check if we can access the models
    try:
        from django.apps import apps
        app_config = apps.get_app_config('store')
        print("\nModels in store app:")
        for model in app_config.get_models():
            print(f"- {model.__name__}")
    except Exception as e:
        print(f"\nError getting models: {e}")
    
except Exception as e:
    print(f"Error importing models: {e}")
    raise
