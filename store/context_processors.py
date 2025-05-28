from .models import Category, Cart, CartItem, Wishlist
from django.conf import settings


def categories(request):
    """
    Context processor for categories.
    """
    return {
        'categories': Category.objects.all().order_by('name')
    }


def get_or_create_cart(request):
    """
    Helper function to get or create a cart for the current user.
    Handles both authenticated and anonymous users.
    """
    from .models import Cart, CartItem
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        # For authenticated users, get or create a cart in the database
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            status='active',
            defaults={'status': 'active'}
        )
        
        # If user had a guest cart, merge it with their user cart
        if 'guest_cart' in request.session:
            from django.utils import timezone
            from decimal import Decimal
            
            guest_cart = request.session['guest_cart']
            for product_id, item in guest_cart.items():
                try:
                    from .models import Product
                    product = Product.objects.get(id=product_id)
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=product,
                        defaults={
                            'quantity': item['quantity'],
                            'price': Decimal(str(item['price']))
                        }
                    )
                    if not created:
                        cart_item.quantity += item['quantity']
                        cart_item.save()
                except (Product.DoesNotExist, (ValueError, KeyError)):
                    continue
            
            # Remove the guest cart from the session
            del request.session['guest_cart']
            request.session.modified = True
        
        return cart
    else:
        # For anonymous users, use a session-based cart
        if 'guest_cart' not in request.session:
            request.session['guest_cart'] = {}
        return None


def cart(request):
    """
    Context processor for cart information.
    Handles both authenticated and anonymous users.
    """
    from decimal import Decimal
    from .models import Product, CartItem
    
    context = {
        'cart': None,
        'cart_count': 0,
        'cart_total': 0,
        'cart_items': [],
        'is_guest_cart': False
    }
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        # For authenticated users
        try:
            cart = get_or_create_cart(request)
            if cart:
                cart_items = list(CartItem.objects.filter(cart=cart).select_related('product'))
                cart_count = sum(item.quantity for item in cart_items)
                cart_total = sum(
                    Decimal(str(item.price)) * item.quantity 
                    for item in cart_items
                    if hasattr(item, 'price')
                )
                
                context.update({
                    'cart': cart,
                    'cart_count': cart_count,
                    'cart_total': cart_total,
                    'cart_items': cart_items,
                    'is_guest_cart': False
                })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in cart context processor: {str(e)}")
    else:
        # For anonymous users, use session-based cart
        guest_cart = request.session.get('guest_cart', {})
        cart_items = []
        cart_total = Decimal('0.00')
        
        # Get product details for items in the guest cart
        product_ids = list(guest_cart.keys())
        products = Product.objects.in_bulk(product_ids)
        
        for product_id, item in guest_cart.items():
            if product_id in products:
                product = products[product_id]
                quantity = item.get('quantity', 0)
                price = Decimal(str(item.get('price', 0)))
                total_price = price * quantity
                
                cart_items.append({
                    'product': product,
                    'quantity': quantity,
                    'price': price,
                    'total_price': total_price,
                    'is_guest_item': True
                })
                
                cart_total += total_price
        
        context.update({
            'cart_count': sum(item['quantity'] for item in cart_items),
            'cart_total': cart_total,
            'cart_items': cart_items,
            'is_guest_cart': True
        })
    
    return context


def wishlist_count(request):
    """
    Context processor for wishlist count.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'wishlist_count': 0}
    
    try:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting wishlist count: {str(e)}")
        wishlist_count = 0
    
    return {
        'wishlist_count': wishlist_count
    }


def contact_info(request):
    """
    Context processor for contact information.
    """
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', "Angel's Plant Shop"),
        'CONTACT_EMAIL': getattr(settings, 'CONTACT_EMAIL', 'contact@example.com'),
        'CONTACT_PHONE': getattr(settings, 'CONTACT_PHONE', '+1 (555) 123-4567'),
        'BUSINESS_ADDRESS': getattr(settings, 'BUSINESS_ADDRESS', '123 Plant St, Greenery City, GC 12345'),
        'BUSINESS_HOURS': getattr(settings, 'BUSINESS_HOURS', [
            'Monday - Friday: 9:00 AM - 6:00 PM',
            'Saturday: 10:00 AM - 4:00 PM',
            'Sunday: Closed'
        ])
    }
