from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Cart, CartItem, Product

class Command(BaseCommand):
    help = 'Inspect the cart system for a specific user'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Email of the user to inspect')

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get user by email or use the first user if not specified
        if options['email']:
            user = User.objects.get(email=options['email'])
        else:
            user = User.objects.first()
            
        if not user:
            self.stdout.write(self.style.ERROR('No users found in the database.'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Inspecting cart for user: {user.email}'))
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            user=user,
            status='active',
            defaults={'status': 'active'}
        )
        
        self.stdout.write(f'Cart ID: {cart.id}, Status: {cart.status}, Created: {created}')
        
        # Get cart items
        items = CartItem.objects.filter(cart=cart).select_related('product')
        self.stdout.write(f'Number of items in cart: {items.count()}')
        
        for item in items:
            self.stdout.write(f'\nItem ID: {item.id}')
            self.stdout.write(f'Product: {item.product.name if item.product else "No product"} (ID: {item.product.id if item.product else "N/A"})')
            self.stdout.write(f'Quantity: {item.quantity}, Price: {item.price}, Total: {item.total_price}')
            self.stdout.write(f'Product active: {item.product.is_active if item.product else False}')
            
        # Check for any inactive products in the cart
        inactive_items = items.filter(product__is_active=False)
        if inactive_items.exists():
            self.stdout.write(self.style.WARNING(f'\nWARNING: Found {inactive_items.count()} inactive products in the cart'))
            
        # Check for any items with missing products
        missing_products = items.filter(product__isnull=True)
        if missing_products.exists():
            self.stdout.write(self.style.WARNING(f'\nWARNING: Found {missing_products.count()} items with missing products'))
            
        # Check if there are any active products in the database
        active_products = Product.objects.filter(is_active=True).count()
        self.stdout.write(f'\nTotal active products in database: {active_products}')
