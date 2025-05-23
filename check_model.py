import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
try:
    django.setup()
    print("Django setup complete")
except Exception as e:
    print(f"Error setting up Django: {e}")
    sys.exit(1)

# Now try to import the models one by one
try:
    print("\nTrying to import Wishlist model...")
    from store.models import Wishlist
    print("Successfully imported Wishlist model!")
    print("Fields:", [f.name for f in Wishlist._meta.get_fields()])
except Exception as e:
    print(f"Error importing Wishlist model: {e}")

try:
    print("\nTrying to import Product model...")
    from store.models import Product
    print("Successfully imported Product model!")
except Exception as e:
    print(f"Error importing Product model: {e}")
