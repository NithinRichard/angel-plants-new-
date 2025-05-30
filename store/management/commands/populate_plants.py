from django.core.management.base import BaseCommand
from store.models import Category, Product
import requests
from django.core.files.base import ContentFile
from django.core.files import File
from io import BytesIO
from PIL import Image
import os

class Command(BaseCommand):
    help = 'Populate the database with demo plants'

    def download_image(self, image_url, slug):
        """Download image from URL and return a Django File object"""
        try:
            response = requests.get(image_url, stream=True, timeout=10)
            response.raise_for_status()
            
            # Create a simple image if the URL fails
            if not response.ok:
                return self.create_placeholder_image(slug)
                
            # Try to open with PIL to verify it's a valid image
            img = Image.open(BytesIO(response.content))
            img.verify()  # Verify it's an image
            img = Image.open(BytesIO(response.content))  # Need to reopen after verify
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            # Save to BytesIO
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=85)
            img_file = ContentFile(img_io.getvalue())
            
            return img_file
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error downloading image: {str(e)}'))
            return self.create_placeholder_image(slug)
    
    def create_placeholder_image(self, slug):
        """Create a placeholder image with text"""
        try:
            # Create a simple green image
            img = Image.new('RGB', (400, 300), color=(73, 109, 65))
            
            # Add text
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            # Try to use a nice font, fallback to default
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default()
                
            text = f"Plant Image\n{slug}"
            text_width = draw.textlength(text, font=font)
            text_height = 60  # Approximate height for two lines
            
            x = (400 - text_width) // 2
            y = (300 - text_height) // 2
            
            draw.text((x, y), text, fill=(255, 255, 255), font=font)
            
            # Save to BytesIO
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=85)
            return ContentFile(img_io.getvalue())
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating placeholder: {str(e)}'))
            return None

    def handle(self, *args, **options):
        # Create categories if they don't exist
        indoor, _ = Category.objects.get_or_create(
            name='Indoor Plants',
            slug='indoor-plants',
            defaults={
                'description': 'Beautiful plants that thrive indoors',
                'is_active': True
            }
        )

        outdoor, _ = Category.objects.get_or_create(
            name='Outdoor Plants',
            slug='outdoor-plants',
            defaults={
                'description': 'Perfect plants for your garden',
                'is_active': True
            }
        )

        # Demo plants data with multiple image sources for redundancy
        plants = [
            # Indoor Plants
            {
                'name': 'Snake Plant',
                'slug': 'snake-plant',
                'description': 'A hardy, low-maintenance plant that purifies the air.',
                'price': 24.99,
                'category': indoor,
                'image_urls': [
                    'https://images.pexels.com/photos/1903965/pexels-photo-1903965.jpeg',
                    'https://images.unsplash.com/photo-1593482892291-3dbeca4d3328',
                ],
                'stock': 50,
                'is_active': True
            },
            {
                'name': 'ZZ Plant',
                'slug': 'zz-plant',
                'description': 'A tough plant that thrives in low light conditions.',
                'price': 29.99,
                'category': indoor,
                'image_urls': [
                    'https://images.pexels.com/photos/4503751/pexels-photo-4503751.jpeg',
                    'https://images.unsplash.com/photo-1605152276897-4f618f831968',
                ],
                'stock': 35,
                'is_active': True
            },
            # Add more plants with multiple image URLs...
        ]

        # Add plants to database
        for plant_data in plants:
            # Remove image_urls from plant data as it's not a model field
            image_urls = plant_data.pop('image_urls', [])
            
            # Create or update the plant
            plant, created = Product.objects.update_or_create(
                slug=plant_data['slug'],
                defaults=plant_data
            )

            # Only try to set image if it's a new plant or the image is missing
            if created or not plant.image:
                img_file = None
                
                # Try each URL until we get a valid image
                for url in image_urls:
                    try:
                        img_file = self.download_image(url, plant.slug)
                        if img_file:
                            break
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Failed to download {url}: {str(e)}'))
                
                if img_file:
                    try:
                        image_name = f"{plant.slug}.jpg"
                        if plant.image:  # If image exists, delete it first
                            plant.image.delete(save=False)
                        plant.image.save(image_name, img_file, save=True)
                        self.stdout.write(self.style.SUCCESS(f'Successfully added image for {plant.name}'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error saving image for {plant.name}: {str(e)}'))
                else:
                    self.stdout.write(self.style.WARNING(f'No valid image found for {plant.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Skipping {plant.name} - image already exists'))

            status = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{status} {plant.name}'))

        self.stdout.write(self.style.SUCCESS('Successfully populated database with demo plants!'))