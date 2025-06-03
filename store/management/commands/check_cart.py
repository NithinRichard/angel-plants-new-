from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from store.models import Cart, CartItem, Product

class Command(BaseCommand):
    help = 'Inspect the contents of a user\'s cart'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to check cart for')

    def handle(self, *args, **options):
        User = get_user_model()
        
        try:
            user = User.objects.get(username=options['username'])
            self.stdout.write(self.style.SUCCESS(f'Found user: {user.username} (ID: {user.id})'))
            
            # Get active cart
            cart = Cart.objects.filter(user=user, status='active').first()
            if not cart:
                self.stdout.write(self.style.WARNING('No active cart found for user'))
                return
                
            self.stdout.write(self.style.SUCCESS(f'Active cart ID: {cart.id}'))
            
            # Get all cart items
            items = CartItem.objects.filter(cart=cart).select_related('product')
            self.stdout.write(f'Total items in cart: {items.count()}')
            
            if not items.exists():
                self.stdout.write(self.style.WARNING('Cart is empty'))
                return
                
            # Display cart items
            self.stdout.write('\nCart Items:')
            for item in items:
                status = 'ACTIVE' if item.product and item.product.is_active else 'INACTIVE'
                self.stdout.write(
                    f"- {item.product.name if item.product else 'DELETED PRODUCT'} "
                    f"(ID: {item.product.id if item.product else 'N/A'}) - "
                    f"Qty: {item.quantity}, "
                    f"Status: {status}"
                )
                
                if not item.product:
                    self.stdout.write(self.style.ERROR('  Product does not exist!'))
                elif not item.product.is_active:
                    self.stdout.write(self.style.WARNING('  Product is inactive'))
                    
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {options["username"]} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
