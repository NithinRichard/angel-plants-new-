from PIL import Image, ImageDraw, ImageFont
import os
import django
from django.core.files import File
from django.utils.text import slugify
from decimal import Decimal

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
django.setup()

from store.models import Product, Category, ProductTag

def create_placeholder_image(text, width=300, height=300, bg_color=(240, 240, 240), text_color=(150, 150, 150)):
    """Create a placeholder image with the given text."""
    # Create a new image with the specified background color
    image = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try to use a nice font if available, otherwise use default
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate text size and position
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw the text
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Draw a border
    border = 2
    draw.rectangle([(border, border), (width - border, height - border)], outline=text_color, width=1)
    
    return image

def create_sample_products():
    # Create a category if it doesn't exist
    indoor_category, _ = Category.objects.get_or_create(
        name='Indoor Plants',
        slug='indoor-plants',
        defaults={
            'description': 'Beautiful plants that thrive indoors',
            'is_active': True
        }
    )

    # Sample products data
    products_data = [
        {
            'name': 'Monstera Deliciosa',
            'price': Decimal('49.99'),
            'compare_at_price': Decimal('69.99'),
            'quantity': 20,
            'description': 'The Monstera Deliciosa, also known as the Swiss Cheese Plant, is a popular tropical plant known for its distinctive split leaves. Perfect for adding a touch of the tropics to your home.',
            'short_description': 'Large, glossy leaves with distinctive splits and holes.',
            'care_instructions': 'Water when top inch of soil is dry. Prefers bright, indirect light. Mist occasionally.',
            'light_requirements': 'Bright, indirect light',
            'watering_needs': 'Moderate',
            'mature_size': '6-8 feet tall',
            'difficulty_level': 'easy',
            'is_featured': True,
            'is_bestseller': True,
        },
        {
            'name': 'Snake Plant',
            'price': Decimal('29.99'),
            'compare_at_price': Decimal('39.99'),
            'quantity': 30,
            'description': 'The Snake Plant, or Sansevieria, is one of the most resilient houseplants. It\'s known for its upright, sword-like leaves and ability to purify indoor air.',
            'short_description': 'Tall, upright leaves with distinctive patterns.',
            'care_instructions': 'Water sparingly. Tolerates low light but prefers bright, indirect light.',
            'light_requirements': 'Low to bright indirect light',
            'watering_needs': 'Low',
            'mature_size': '2-4 feet tall',
            'difficulty_level': 'easy',
            'is_featured': True,
            'is_bestseller': True,
        },
        {
            'name': 'Fiddle Leaf Fig',
            'price': Decimal('79.99'),
            'compare_at_price': Decimal('99.99'),
            'quantity': 15,
            'description': 'The Fiddle Leaf Fig is a stunning plant with large, violin-shaped leaves. It makes a dramatic statement in any room.',
            'short_description': 'Large, glossy leaves shaped like violins.',
            'care_instructions': 'Keep soil moist but not soggy. Needs bright, indirect light.',
            'light_requirements': 'Bright, indirect light',
            'watering_needs': 'Moderate',
            'mature_size': '6-10 feet tall',
            'difficulty_level': 'moderate',
            'is_featured': True,
            'is_bestseller': False,
        },
        {
            'name': 'ZZ Plant',
            'price': Decimal('34.99'),
            'compare_at_price': Decimal('44.99'),
            'quantity': 25,
            'description': 'The ZZ Plant is a low-maintenance plant with glossy, dark green leaves. It\'s perfect for beginners and can thrive in low-light conditions.',
            'short_description': 'Glossy, dark green leaves on upright stems.',
            'care_instructions': 'Water when soil is completely dry. Tolerates low light.',
            'light_requirements': 'Low to bright indirect light',
            'watering_needs': 'Low',
            'mature_size': '2-3 feet tall',
            'difficulty_level': 'easy',
            'is_featured': False,
            'is_bestseller': True,
        },
        {
            'name': 'Pothos Golden',
            'price': Decimal('24.99'),
            'compare_at_price': Decimal('34.99'),
            'quantity': 35,
            'description': 'The Golden Pothos is a versatile trailing plant with heart-shaped leaves. It\'s perfect for hanging baskets or climbing up moss poles.',
            'short_description': 'Heart-shaped leaves with golden variegation.',
            'care_instructions': 'Water when top inch of soil is dry. Tolerates various light conditions.',
            'light_requirements': 'Low to bright indirect light',
            'watering_needs': 'Moderate',
            'mature_size': '6-10 feet long',
            'difficulty_level': 'easy',
            'is_featured': False,
            'is_bestseller': True,
        }
    ]

    # Create products
    for product_data in products_data:
        # Generate SKU
        sku = f"PLT-{slugify(product_data['name'])[:8].upper()}"
        
        # Create product
        product = Product.objects.create(
            name=product_data['name'],
            slug=slugify(product_data['name']),
            sku=sku,
            category=indoor_category,
            **{k: v for k, v in product_data.items() if k not in ['name']}
        )
        
        print(f"Created product: {product.name} (SKU: {product.sku})")

if __name__ == "__main__":
    # Create the media directory if it doesn't exist
    media_dir = os.path.join('media', 'products')
    os.makedirs(media_dir, exist_ok=True)
    
    # Create and save the placeholder image
    placeholder_path = os.path.join(media_dir, 'placeholder.jpg')
    placeholder = create_placeholder_image("No Image Available")
    placeholder.save(placeholder_path, 'JPEG')
    
    print(f"Created placeholder image at: {placeholder_path}")

    create_sample_products()
