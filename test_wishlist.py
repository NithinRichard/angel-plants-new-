import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
django.setup()

# Now try to import the Wishlist model
try:
    from store.models import Wishlist
    print("Successfully imported Wishlist model!")
    print(f"Fields: {[f.name for f in Wishlist._meta.get_fields()]}")
except Exception as e:
    print(f"Error importing Wishlist model: {e}")
    raise
