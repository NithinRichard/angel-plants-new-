import sys
import os

def check_models():
    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    import django
    django.setup()
    
    # Now try to import the models
    try:
        from store import models
        print("Successfully imported models!")
        return True
    except Exception as e:
        print(f"Error importing models: {e}")
        return False

if __name__ == "__main__":
    check_models()
