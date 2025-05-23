import os
import base64
import requests
from io import BytesIO
from django.core.files import File
from django.core.management.base import BaseCommand
from django.core.files.temp import NamedTemporaryFile
from store.models import Category, Product, ProductImage
from django.utils.text import slugify
from django.core.files.base import ContentFile
from django.conf import settings
from PIL import Image

# High-quality plant images from Pexels with proper attribution
PLANT_IMAGES = {
    # Indoor Plants
    'Snake Plant': {
        'url': 'https://images.pexels.com/photos/4503273/pexels-photo-4503273.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'A beautiful Snake Plant with tall, upright leaves.'
    },
    'ZZ Plant': {
        'url': 'https://images.pexels.com/photos/4503751/pexels-photo-4503751.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Healthy ZZ Plant with glossy green leaves.'
    },
    'Pothos': {
        'url': 'https://natalielinda.com/wp-content/uploads/2018/11/Cream-pothos.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Golden Pothos with heart-shaped leaves.'
    },
    'Peace Lily': {
        'url': 'https://scarlettgardens.com/wp-content/uploads/2021/04/peacelily.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Elegant Peace Lily with white flowers.'
    },
    'Fiddle Leaf Fig': {
        'url': 'https://img.freepik.com/premium-photo/isolated-fiddle-leaf-fig-popular-elegant-plant-feat-top-view-white-background_655090-577069.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Stately Fiddle Leaf Fig tree.'
    },
    'Monstera Deliciosa': {
        'url': 'https://images.pexels.com/photos/6208086/pexels-photo-6208086.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Lush Monstera with beautiful leaf fenestrations.'
    },
    'Rubber Plant': {
        'url': 'https://images.pexels.com/photos/6208087/pexels-photo-6208087.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Glossy-leaved Rubber Plant.'
    },
    'Bird of Paradise': {
        'url': 'https://images.pexels.com/photos/6208089/pexels-photo-6208089.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Tropical Bird of Paradise plant.'
    },
    'Calathea': {
        'url': 'https://images.pexels.com/photos/6208088/pexels-photo-6208088.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Ornate Calathea with patterned leaves.'
    },
    'Spider Plant': {
        'url': 'https://images.pexels.com/photos/4503271/pexels-photo-4503271.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Variegated Spider Plant with baby plantlets.'
    },
    
    # Outdoor Plants
    'Lavender': {
        'url': 'https://hdwpro.com/wp-content/uploads/2020/09/Landscape-Lavender-Flower.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Beautiful purple Lavender flowers.'
    },
    'Rose Bush': {
        'url': 'https://i.pinimg.com/736x/20/2c/cf/202ccf0fbadb04765bc0c5045fa4b927.jpg',
        'photographer': 'Marta Dzedyshko',
        'description': 'Vibrant red rose bush.'
    },
    'Hydrangea': {
        'url': 'https://images.pexels.com/photos/4503272/pexels-photo-4503272.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Lush blue Hydrangea bush.'
    },
    'Japanese Maple': {
        'url': 'https://images.pexels.com/photos/4503274/pexels-photo-4503274.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Beautiful Japanese Maple tree.'
    },
    'Boxwood': {
        'url': 'https://images.pexels.com/photos/4503275/pexels-photo-4503275.jpeg',
        'photographer': 'Elina Volkova',
        'description': 'Neatly trimmed Boxwood hedge.'
    },
    'Sunflower': {
        'url': 'https://www.lovethegarden.com/sites/default/files/content/articles/uk/giant-sunflowers.jpg',
        'photographer': 'Pixabay',
        'description': 'Bright yellow sunflower.'
    },
    'Tulip': {
        'url': 'https://gardentabs.com/wp-content/uploads/2019/10/Tulip-pots.jpg',
        'photographer': 'Pixabay',
        'description': 'Colorful tulip flowers.'
    },
    'Hydrangea': {
        'url': 'https://www.thespruce.com/thmb/Q4CCplOCaSx9TcldQEdqjyayq9o=/5161x3440/filters:fill(auto,1)/siasconset--nantucket--massachusetts-10143762-5b208b0a303713003625cdd8.jpg',
        'photographer': 'Lina Kivaka',
        'description': 'Beautiful blue hydrangea flowers.'
    },
    
    # Succulents
    'Echeveria': {
        'url': 'echeveria.jpg',  # This will be a local file in the media directory
        'photographer': 'Local',
        'description': 'Rosette-shaped Echeveria succulent.',
        'local_image': True  # Flag to indicate we'll use a local image
    },
    'Aloe Vera': {
        'url': 'https://greenripegarden.com/wp-content/uploads/2020/04/Aloe-Vera-Plant-2048x1365.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Healthy Aloe Vera plant.'
    },
    'Jade Plant': {
        'url': 'https://www.plantcarefully.com/wp-content/uploads/jade-plant-11.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Mature Jade Plant.'
    },
    'String of Pearls': {
        'url': 'https://gardengotime.com/wp-content/uploads/2021/07/sting-of-pearls-plant.jpgg',
        'photographer': 'Elina Volkova',
        'description': 'Beautiful String of Pearls succulent.'
    },
    'Hens and Chicks': {
        'url': 'https://cdn.mos.cms.futurecdn.net/fWVhKzdtsJFSyG6xNxQYtR-1536-80.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Hens and Chicks succulent arrangement.'
    },
    
    # Flowering Plants
    'Orchid': {
        'url': 'https://cdn.pixabay.com/photo/2022/01/06/09/21/orchid-6919028_1280.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Elegant white orchid.'
    },
    'African Violet': {
        'url': 'https://www.almanac.com/sites/default/files/image_nodes/african-violet-houseplant.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Vibrant African Violet.'
    },
    'Anthurium': {
        'url': 'https://cdn.mos.cms.futurecdn.net/JhYRFDeFNKgUsjkT2fcu6a.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Red Anthurium with glossy leaves.'
    },
    'Bromeliad': {
        'url': 'https://www.gardenmandy.com/wp-content/uploads/2018/08/Bromeliad-Flower-1920x1440.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Colorful Bromeliad plant.'
    },
    'Kalanchoe': {
        'url': 'https://plantly.io/wp-content/uploads/2023/03/Kalanchoe_blossfeldiorum2.jpg',
        'photographer': 'Elina Volkova',
        'description': 'Blooming Kalanchoe plant.'
    }
}

class Command(BaseCommand):
    help = 'Populate the database with plant data'

    def download_image(self, instance, image_url, folder):
        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                # Create the directory if it doesn't exist
                os.makedirs(os.path.join(settings.MEDIA_ROOT, folder), exist_ok=True)
                
                # Get the file extension from the URL
                file_extension = os.path.splitext(image_url)[1]
                if not file_extension:
                    file_extension = '.jpg'  # Default to jpg if no extension found
                
                # Create a unique filename
                filename = f"{slugify(instance.name)}{file_extension}"
                filepath = os.path.join(folder, filename)
                
                # Save the image
                instance.image.save(filename, ContentFile(response.content), save=True)
                self.stdout.write(f'Downloaded image for {instance.name}')
            else:
                self.stderr.write(f'Failed to download image for {instance.name}: {response.status_code}')
        except Exception as e:
            self.stderr.write(f'Error downloading image for {instance.name}: {str(e)}')

    def handle(self, *args, **options):
        # Create categories if they don't exist
        categories_data = [
            {
                'name': 'Indoor Plants',
                'slug': 'indoor-plants',
                'description': 'Beautiful plants that thrive indoors',
                'image_url': 'https://images.unsplash.com/photo-1485955900006-10f4d324d411'
            },
            {
                'name': 'Outdoor Plants',
                'slug': 'outdoor-plants',
                'description': 'Perfect plants for your garden',
                'image_url': 'https://images.unsplash.com/photo-1465146344425-f00d5f5c8f07'
            },
            {
                'name': 'Succulents',
                'slug': 'succulents',
                'description': 'Low-maintenance plants that store water',
                'image_url': 'https://images.pexels.com/photos/1903965/pexels-photo-1903965.jpeg'
            }
        ]

        self.stdout.write('Creating categories...')
        categories = {}
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description']
                }
            )
            
            # Download and save category image
            if not category.image:
                self.download_image(category, cat_data['image_url'], 'categories')
                
            categories[cat_data['slug']] = category
            self.stdout.write(f'Created category: {category.name}')

        # Create sample products
        products_data = [
            # Indoor Plants
            {
                'name': 'Monstera Deliciosa',
                'slug': 'monstera-deliciosa',
                'sku': 'MONST-001',
                'description': 'A popular tropical plant with distinctive split leaves',
                'price': 49.99,
                'quantity': 10,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['Monstera Deliciosa']['url']
            },
            {
                'name': 'Snake Plant',
                'slug': 'snake-plant',
                'sku': 'SNAKE-001',
                'description': 'A hardy plant that purifies indoor air',
                'price': 29.99,
                'quantity': 15,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['Snake Plant']['url']
            },
            {
                'name': 'ZZ Plant',
                'slug': 'zz-plant',
                'sku': 'ZZPLANT-001',
                'description': 'A low-maintenance plant with glossy green leaves',
                'price': 34.99,
                'quantity': 8,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['ZZ Plant']['url']
            },
            {
                'name': 'Pothos',
                'slug': 'pothos',
                'sku': 'POTHOS-001',
                'description': 'Easy-to-care trailing plant with heart-shaped leaves',
                'price': 24.99,
                'quantity': 20,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['Pothos']['url']
            },
            {
                'name': 'Rubber Plant',
                'slug': 'rubber-plant',
                'sku': 'RUBBER-001',
                'description': 'A popular houseplant with large, glossy leaves',
                'price': 39.99,
                'quantity': 12,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['Rubber Plant']['url']
            },
            {
                'name': 'Bird of Paradise',
                'slug': 'bird-of-paradise',
                'sku': 'BIRD-001',
                'description': 'Tropical plant with large, banana-like leaves',
                'price': 59.99,
                'quantity': 7,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['Bird of Paradise']['url']
            },
            {
                'name': 'Calathea',
                'slug': 'calathea',
                'sku': 'CALAT-001',
                'description': 'Ornamental plant with beautifully patterned leaves',
                'price': 32.99,
                'quantity': 14,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['Calathea']['url']
            },
            {
                'name': 'Spider Plant',
                'slug': 'spider-plant',
                'sku': 'SPIDER-001',
                'description': 'Easy-to-grow plant with arching leaves and baby plantlets',
                'price': 19.99,
                'quantity': 25,
                'category': categories['indoor-plants'],
                'image_url': PLANT_IMAGES['Spider Plant']['url']
            },
            
            # Outdoor Plants
            {
                'name': 'Lavender',
                'slug': 'lavender',
                'sku': 'LAV-001',
                'description': 'Fragrant purple flowers that attract pollinators',
                'price': 14.99,
                'quantity': 30,
                'category': categories['outdoor-plants'],
                'image_url': PLANT_IMAGES['Lavender']['url']
            },
            {
                'name': 'Rose Bush',
                'slug': 'rose-bush',
                'sku': 'ROSE-001',
                'description': 'Classic flowering shrub with beautiful blooms',
                'price': 24.99,
                'quantity': 18,
                'category': categories['outdoor-plants'],
                'image_url': PLANT_IMAGES['Rose Bush']['url']
            },
            {
                'name': 'Hydrangea',
                'slug': 'hydrangea',
                'sku': 'HYDRA-001',
                'description': 'Large clusters of flowers that change color based on soil pH',
                'price': 34.99,
                'quantity': 15,
                'category': categories['outdoor-plants'],
                'image_url': PLANT_IMAGES['Hydrangea']['url']
            },
            {
                'name': 'Japanese Maple',
                'slug': 'japanese-maple',
                'sku': 'JMAPLE-001',
                'description': 'Ornamental tree with delicate, colorful foliage',
                'price': 89.99,
                'quantity': 5,
                'category': categories['outdoor-plants'],
                'image_url': PLANT_IMAGES['Japanese Maple']['url']
            },
            {
                'name': 'Boxwood',
                'slug': 'boxwood',
                'sku': 'BOX-001',
                'description': 'Evergreen shrub perfect for hedges and topiaries',
                'price': 29.99,
                'quantity': 22,
                'category': categories['outdoor-plants'],
                'image_url': PLANT_IMAGES['Boxwood']['url']
            },
            {
                'name': 'Echeveria',
                'slug': 'echeveria',
                'sku': 'ECH-001',
                'description': 'Beautiful rosette-forming succulent',
                'price': 19.99,
                'quantity': 20,
                'category': categories['succulents'],
                'image_url': {
                    'base64': True
                }
            }
        ]

        self.stdout.write('\nAdding plants...')
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                slug=product_data['slug'],
                defaults={
                    'name': product_data['name'],
                    'sku': product_data['sku'],
                    'description': product_data['description'],
                    'price': product_data['price'],
                    'quantity': product_data['quantity'],
                    'category': product_data['category']
                }
            )
            
            # Handle product image
            if not product.image:
                # Check if this is a base64-encoded image
                if isinstance(product_data['image_url'], dict) and product_data['image_url'].get('base64'):
                    try:
                        # Create a simple green placeholder image
                        img = Image.new('RGB', (400, 300), color=(73, 109, 65))  # Dark green color
                        
                        # Add text to the image
                        from PIL import ImageDraw, ImageFont
                        draw = ImageDraw.Draw(img)
                        try:
                            font = ImageFont.truetype("arial.ttf", 40)
                        except:
                            font = ImageFont.load_default()
                        
                        # Add text
                        text = "Echeveria\nPlaceholder"
                        text_bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = text_bbox[2] - text_bbox[0]
                        text_height = text_bbox[3] - text_bbox[1]
                        x = (400 - text_width) // 2
                        y = (300 - text_height) // 2
                        draw.text((x, y), text, fill=(255, 255, 255), font=font)
                        
                        # Save to a BytesIO object
                        img_io = BytesIO()
                        img.save(img_io, format='JPEG')
                        img_io.seek(0)
                        
                        # Save to the product
                        product.image.save(f"{slugify(product.name)}.jpg", File(img_io), save=True)
                        self.stdout.write(f'Created placeholder image for {product.name}')
                    except Exception as e:
                        self.stderr.write(f'Error creating placeholder for {product.name}: {str(e)}')
                else:
                    # Download image from URL
                    self.download_image(product, product_data['image_url'], 'products')
            
            self.stdout.write(f'Created product: {product.name}')

        self.stdout.write(self.style.SUCCESS('Successfully populated database with plants'))
