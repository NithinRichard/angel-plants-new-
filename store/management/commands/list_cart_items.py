from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Cart, CartItem, Product

class Command(BaseCommand):
    help = 'List all cart items across all users with detailed status information'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get all carts
        carts = Cart.objects.all().order_by('-updated_at')
        self.stdout.write(f'Found {carts.count()} carts in total')
        
        for cart in carts:
            self.stdout.write(self.style.SUCCESS(f'\nCart ID: {cart.id} - User: {cart.user.username if cart.user else "Anonymous"} - Status: {cart.status} - Last Updated: {cart.updated_at}'))
            
            # Get all items in this cart
            items = CartItem.objects.filter(cart=cart).select_related('product')
            self.stdout.write(f'  Items in cart: {items.count()}')
            
            for item in items:
                product = item.product
                if product:
                    status = 'ACTIVE' if product.is_active else 'INACTIVE'
                    stock_status = f'Stock: {product.quantity}'
                    if product.track_quantity and product.quantity < item.quantity:
                        stock_status = self.style.ERROR(f'{stock_status} (Insufficient stock for quantity: {item.quantity})')
                    else:
                        stock_status = self.style.SUCCESS(stock_status)
                        
                    self.stdout.write(
                        f'  - Product: {product.name} (ID: {product.id}) - ' \
                        f'Qty: {item.quantity} - Status: {status} - {stock_status} - ' \
                        f'Active: {product.is_active} - Track Qty: {product.track_quantity}'
                    )
                else:
                    self.stdout.write(self.style.ERROR(f'  - [MISSING PRODUCT] CartItem ID: {item.id} - No associated product'))
            
            # Show cart totals
            self.stdout.write(f'  Cart Total: {cart.total} - Updated: {cart.updated_at}')
            
            # Check for associated order
            if hasattr(cart, 'order'):
                self.stdout.write(self.style.WARNING(f'  !! This cart is associated with Order: {cart.order.order_number}'))
                
        self.stdout.write('\nNote: Check for carts with items but no associated order, or items with insufficient stock.')
