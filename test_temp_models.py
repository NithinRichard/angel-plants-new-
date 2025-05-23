import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
try:
    django.setup()
    print("Django setup complete")
except Exception as e:
    print(f"Error setting up Django: {e}")
    raise

# Now try to import the simplified model
try:
    print("\nTrying to import simplified Wishlist model...")
    from temp_models import Wishlist
    print("Successfully imported simplified Wishlist model!")
    print("Fields:", [f.name for f in Wishlist._meta.get_fields()])
except Exception as e:
    print(f"Error importing simplified Wishlist model: {e}")
    raise
