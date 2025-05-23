from .models import Category, Cart, CartItem, Wishlist
from django.conf import settings


def categories(request):
    """
    Context processor for categories.
    """
    return {
        'categories': Category.objects.all().order_by('name')
    }


def cart(request):
    """
    Context processor for cart information.
    """
    context = {}
    if hasattr(request, 'user') and request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user, status='active')
            cart_items = CartItem.objects.filter(cart=cart)
            cart_count = sum(item.quantity for item in cart_items)
            cart_total = sum(item.total_price for item in cart_items)
            
            context.update({
                'cart': cart,
                'cart_count': cart_count,
                'cart_total': cart_total,
                'cart_items': cart_items
            })
        except Cart.DoesNotExist:
            context.update({
                'cart': None,
                'cart_count': 0,
                'cart_total': 0,
                'cart_items': []
            })
    else:
        # For anonymous users, use session-based cart
        cart = request.session.get('cart', {})
        cart_count = sum(item.get('quantity', 0) for item in cart.values())
        cart_total = sum(float(item.get('price', 0)) * item.get('quantity', 0) for item in cart.values())
        
        context.update({
            'cart_count': cart_count,
            'cart_total': cart_total,
            'cart_items': []
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
