from django.core.management.base import BaseCommand
from store.models import Category, Product
import requests
from django.core.files.base import ContentFile
from django.core.files import File
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os

class Command(BaseCommand):
    help = 'Populate the database with demo plants'

    def create_placeholder_image(self, text, width=400, height=300):
        """Create a placeholder image with text"""
        try:
            # Create a simple green image
            img = Image.new('RGB', (width, height), color=(73, 109, 65))
            draw = ImageDraw.Draw(img)
            
            # Use default font
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default()
            
            # Add text
            text = str(text)  # Ensure text is a string
            lines = text.split('\n')
            y_offset = 20
            
            for line in lines:
                text_bbox = draw.textbbox((0, 0), line, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                x = (width - text_width) // 2
                draw.text((x, y_offset), line, fill=(255, 255, 255), font=font)
                y_offset += 35  # Line height
            
            # Save to BytesIO
            img_io = BytesIO()
            img.save(img_io, format='JPEG', quality=85)
            img_io.seek(0)
            return ContentFile(img_io.getvalue())
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating placeholder: {str(e)}'))
            return None

    def download_image(self, image_url, slug):
        """Download image from URL and return a Django File object"""
        try:
            response = requests.get(image_url, stream=True, timeout=10)
            response.raise_for_status()
            
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
            img_io.seek(0)
            return ContentFile(img_io.getvalue())
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error downloading image from {image_url}: {str(e)}'))
            return None

    def set_plant_image(self, plant, image_urls=None):
        """Set image for plant, trying multiple URLs if provided"""
        if not image_urls:
            image_urls = []
        
        # Try each URL until we get a valid image
        for url in image_urls:
            try:
                img_file = self.download_image(url, plant.slug)
                if img_file:
                    image_name = f"{plant.slug}.jpg"
                    if plant.image:  # If image exists, delete it first
                        plant.image.delete(save=False)
                    plant.image.save(image_name, img_file, save=True)
                    self.stdout.write(self.style.SUCCESS(f'Successfully added image for {plant.name} from {url}'))
                    return True
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to process {url}: {str(e)}'))
        
        # If no URL worked, create a placeholder
        placeholder = self.create_placeholder_image(plant.name)
        if placeholder:
            image_name = f"{plant.slug}_placeholder.jpg"
            if plant.image:  # If image exists, delete it first
                plant.image.delete(save=False)
            plant.image.save(image_name, placeholder, save=True)
            self.stdout.write(self.style.WARNING(f'Created placeholder for {plant.name}'))
            return True
        
        self.stdout.write(self.style.ERROR(f'Failed to set image for {plant.name}'))
        return False

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
            # Add more plants as needed
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

            # Set the image (will create a placeholder if download fails)
            self.set_plant_image(plant, image_urls)

            status = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{status} {plant.name}'))

        self.stdout.write(self.style.SUCCESS('Successfully populated database with demo plants!'))