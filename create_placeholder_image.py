from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_image():
    # Create a 400x400 image with a light gray background
    width, height = 400, 400
    background_color = (240, 240, 240)  # Light gray
    text_color = (200, 200, 200)  # Lighter gray for text
    
    # Create a new image with RGB mode
    image = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(image)
    
    # Add a border
    border_color = (220, 220, 220)
    draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=2)
    
    # Add some text
    try:
        # Try to use a nice font if available
        font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        # Fall back to default font
        font = ImageFont.load_default()
    
    text = "No Image"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Position text in the center
    position = ((width - text_width) // 2, (height - text_height) // 2)
    draw.text(position, text, fill=text_color, font=font)
    
    # Create the images directory if it doesn't exist
    os.makedirs('static/images', exist_ok=True)
    
    # Save the image
    image_path = os.path.join('static', 'images', 'placeholder-product.png')
    image.save(image_path)
    print(f"Created placeholder image at: {image_path}")

if __name__ == "__main__":
    create_placeholder_image()


