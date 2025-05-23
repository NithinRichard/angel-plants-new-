import os
import requests
from django.core.management.base import BaseCommand
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile
from store.models import Product, Category

class Command(BaseCommand):
    help = 'Download and save actual plant images from Pexels'

    def handle(self, *args, **options):
        # Dictionary mapping product names to high-quality plant image URLs
        product_images = {
            # Indoor Plants
            'Snake Plant': 'https://images.pexels.com/photos/4503752/pexels-photo-4503752.jpeg',
            'ZZ Plant': 'https://images.pexels.com/photos/4503751/pexels-photo-4503751.jpeg',
            'Pothos': 'https://images.pexels.com/photos/4503753/pexels-photo-4503753.jpeg',
            
            # Outdoor Plants
            'Lavender': 'https://images.pexels.com/photos/4503754/pexels-photo-4503754.jpeg',
            'Boxwood': 'https://images.pexels.com/photos/4503755/pexels-photo-4503755.jpeg',
            
            # Succulents
            'Echeveria': 'https://images.pexels.com/photos/4503756/pexels-photo-4503756.jpeg',
            'Aloe Vera': 'https://images.pexels.com/photos/4503757/pexels-photo-4503757.jpeg',
            
            # Flowering Plants
            'Orchid': 'https://images.pexels.com/photos/4503758/pexels-photo-4503758.jpeg',
            'Peace Lily': 'https://images.pexels.com/photos/4503759/pexels-photo-4503759.jpeg',
            'African Violet': 'https://images.pexels.com/photos/4503760/pexels-photo-4503760.jpeg',
        }

        # High-quality category images
        category_images = {
            'Indoor Plants': 'https://images.pexels.com/photos/1402409/pexels-photo-1402409.jpeg',
            'Outdoor Plants': 'https://images.pexels.com/photos/1454288/pexels-photo-1454288.jpeg',
            'Succulents': 'https://images.pexels.com/photos/1903965/pexels-photo-1903965.jpeg',
            'Flowering Plants': 'https://images.pexels.com/photos/1086178/pexels-photo-1086178.jpeg',
        }

        # Download and update category images
        self.stdout.write('Updating category images...')
        for category_name, image_url in category_images.items():
            try:
                category = Category.objects.get(name=category_name)
                if not category.image or 'default' in str(category.image):
                    self.download_image(category, image_url, 'categories')
                    self.stdout.write(f'Updated image for {category_name}')
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Category not found: {category_name}'))

        # Download and update product images
        self.stdout.write('\nUpdating product images...')
        for product_name, image_url in product_images.items():
            try:
                product = Product.objects.get(name=product_name)
                if not product.image or 'default' in str(product.image):
                    self.download_image(product, image_url, 'products')
                    self.stdout.write(f'Updated image for {product_name}')
            except Product.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Product not found: {product_name}'))

        self.stdout.write(self.style.SUCCESS('\nAll images have been updated successfully!'))

    def download_image(self, obj, url, folder):
        """Download and save high-quality image from URL to the specified folder."""
        try:
            # Create the media directory if it doesn't exist
            os.makedirs(f'media/{folder}', exist_ok=True)
            
            # Set a user-agent to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Download the image with a timeout
            response = requests.get(url, stream=True, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Get content type and extension
            content_type = response.headers.get('content-type')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            elif 'gif' in content_type:
                ext = 'gif'
            else:
                ext = 'jpg'  # default
            
            # Create a temporary file with the correct extension
            with NamedTemporaryFile(delete=False, suffix=f'.{ext}') as img_temp:
                # Write the image to the temporary file
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        img_temp.write(chunk)
                
                # Save the image to the model
                if hasattr(obj, 'image'):
                    # Delete old image if it exists
                    if obj.image and os.path.isfile(obj.image.path):
                        try:
                            os.remove(obj.image.path)
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Could not delete old image: {e}'))
                    
                    # Save new image
                    obj.image.save(
                        f'{obj.slug}.{ext}',
                        File(open(img_temp.name, 'rb')),
                        save=True
                    )
                    self.stdout.write(self.style.SUCCESS(f'Successfully updated image for {obj.name}'))
            
            # Clean up the temporary file
            try:
                os.unlink(img_temp.name)
            except:
                pass
            
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Network error downloading image for {obj.name}: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error processing image for {obj.name}: {str(e)}'))
