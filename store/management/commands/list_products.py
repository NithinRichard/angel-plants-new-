from django.core.management.base import BaseCommand
from store.models import Product

class Command(BaseCommand):
    help = 'List all products with their status'

    def handle(self, *args, **options):
        products = Product.objects.all().order_by('name')
        
        if not products.exists():
            self.stdout.write(self.style.WARNING('No products found in the database.'))
            return
            
        self.stdout.write(self.style.SUCCESS(f'Found {products.count()} products in the database:'))
        
        active_count = 0
        for product in products:
            status = self.style.SUCCESS('Active') if product.is_active else self.style.ERROR('Inactive')
            self.stdout.write(f'ID: {product.id}, Name: {product.name}, Status: {status}, Price: {product.price}, Quantity: {product.quantity}')
            if product.is_active:
                active_count += 1
                
        self.stdout.write(f'\nTotal active products: {active_count}/{products.count()}')
        
        if active_count == 0:
            self.stdout.write(self.style.ERROR('\nWARNING: There are no active products in the database!'))
            self.stdout.write(self.style.WARNING('This is why the cart appears empty. Products must be marked as active to appear in the store.'))
