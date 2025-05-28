"""
Utility functions for cart operations.
"""
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from .models import Cart, CartItem, Product


def get_cart_for_request(request):
    """
    Get or create a cart for the current request.
    Handles both authenticated and anonymous users.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        # For authenticated users, get or create a cart in the database
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            status='active',
            defaults={'status': 'active'}
        )
        return cart, False  # False indicates this is not a guest cart
    else:
        # For anonymous users, use session-based cart
        if 'guest_cart' not in request.session:
            request.session['guest_cart'] = {}
        return request.session['guest_cart'], True  # True indicates this is a guest cart


def add_to_cart(request, product_id, quantity=1, update_quantity=False):
    """
    Add a product to the cart or update the quantity if it already exists.
    
    Args:
        request: The HTTP request object
        product_id: The ID of the product to add
        quantity: The quantity to add (default: 1)
        update_quantity: If True, set quantity to the given value instead of adding to existing
    
    Returns:
        tuple: (success: bool, message: str, cart_item: CartItem or None)
    """
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return False, "Product not found", None
    
    if quantity < 1:
        return False, "Invalid quantity", None
    
    # Check if there's enough stock
    if quantity > product.quantity:
        return False, f"Only {product.quantity} items available in stock", None
    
    cart, is_guest_cart = get_cart_for_request(request)
    
    if is_guest_cart:
        # Handle guest cart (session-based)
        guest_cart = cart
        product_id_str = str(product_id)
        
        if product_id_str in guest_cart and not update_quantity:
            # Update quantity if product already in cart
            guest_cart[product_id_str]['quantity'] += quantity
        else:
            # Add new item to cart
            guest_cart[product_id_str] = {
                'product_id': product_id,
                'name': product.name,
                'price': str(product.price),  # Convert Decimal to string for JSON serialization
                'quantity': quantity,
                'image': product.get_thumbnail_url() if product.images.exists() else ''
            }
        
        # Save the session
        request.session.modified = True
        return True, "Product added to cart", None
    else:
        # Handle authenticated user's cart (database-based)
        with transaction.atomic():
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={
                    'quantity': quantity,
                    'price': product.price
                }
            )
            
            if not created:
                if update_quantity:
                    cart_item.quantity = quantity
                else:
                    cart_item.quantity += quantity
                cart_item.save()
            
            # Update cart timestamps
            cart.save()
            
            return True, "Product added to cart", cart_item


def remove_from_cart(request, product_id):
    """
    Remove a product from the cart.
    
    Args:
        request: The HTTP request object
        product_id: The ID of the product to remove
    
    Returns:
        tuple: (success: bool, message: str)
    """
    cart, is_guest_cart = get_cart_for_request(request)
    
    if is_guest_cart:
        # Handle guest cart (session-based)
        product_id_str = str(product_id)
        if product_id_str in cart:
            del cart[product_id_str]
            request.session.modified = True
            return True, "Product removed from cart"
        return False, "Product not found in cart"
    else:
        # Handle authenticated user's cart (database-based)
        try:
            cart_item = CartItem.objects.get(
                cart=cart,
                product_id=product_id
            )
            cart_item.delete()
            cart.save()  # Update cart timestamps
            return True, "Product removed from cart"
        except CartItem.DoesNotExist:
            return False, "Product not found in cart"


def get_cart_items(request):
    """
    Get all items in the cart with product details.
    
    Returns:
        dict: {
            'items': list of cart items with product details,
            'total': total cart value,
            'count': total number of items in cart
        }
    """
    cart, is_guest_cart = get_cart_for_request(request)
    
    if is_guest_cart:
        # Handle guest cart (session-based)
        product_ids = list(cart.keys())
        products = Product.objects.filter(id__in=product_ids).in_bulk()
        
        items = []
        total = Decimal('0.00')
        count = 0
        
        for product_id, item in cart.items():
            if product_id in products:
                product = products[product_id]
                quantity = int(item.get('quantity', 0))
                price = Decimal(str(item.get('price', '0.00')))
                item_total = price * quantity
                
                items.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price,
                    'total_price': item_total,
                    'is_guest_item': True
                })
                
                total += item_total
                count += quantity
        
        return {
            'items': items,
            'total': total,
            'count': count,
            'is_guest_cart': True
        }
    else:
        # Handle authenticated user's cart (database-based)
        cart_items = CartItem.objects.filter(cart=cart).select_related('product')
        
        items = []
        total = Decimal('0.00')
        count = 0
        
        for item in cart_items:
            item_total = item.price * item.quantity
            
            items.append({
                'product': item.product,
                'quantity': item.quantity,
                'price': item.price,
                'total_price': item_total,
                'is_guest_item': False,
                'id': item.id
            })
            
            total += item_total
            count += item.quantity
        
        return {
            'items': items,
            'total': total,
            'count': count,
            'is_guest_cart': False,
            'cart_id': cart.id
        }
