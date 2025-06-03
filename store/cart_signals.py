"""
Signals related to the shopping cart functionality.
"""
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from .models import Cart, CartItem, Order, OrderItem


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_cart(sender, instance, created, **kwargs):
    """
    Create a new cart when a new user is created.
    """
    if created:
        Cart.objects.get_or_create(
            user=instance,
            defaults={'status': 'active'}
        )


@receiver(post_save, sender=CartItem)
def update_cart_totals_on_item_change(sender, instance, **kwargs):
    """
    Update cart's updated_at timestamp when a cart item is added or updated.
    """
    if instance.cart:
        instance.cart.save()


@receiver(pre_delete, sender=CartItem)
def update_cart_on_item_delete(sender, instance, **kwargs):
    """
    Update cart's updated_at timestamp when a cart item is deleted.
    """
    if instance.cart:
        instance.cart.save()


@receiver(post_save, sender=Order)
def convert_cart_to_order(sender, instance, created, **kwargs):
    """
    When an order is created from a cart, update the cart status and clear its items.
    """
    if not created:
        return
        
    # Get the cart safely
    cart = getattr(instance, 'cart', None)
    if not cart:
        return
        
    try:
        # Update cart status
        cart.status = 'converted'
        cart.save()
        
        # Clear the cart items
        cart.items.all().delete()
    except Exception as e:
        # Log the error but don't fail the order creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating cart status after order creation: {str(e)}", 
                    exc_info=True)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def merge_guest_cart_with_user(sender, instance, created, **kwargs):
    """
    If a user had a guest cart before logging in, merge it with their user cart.
    """
    if not created and hasattr(instance, '_guest_cart'):
        guest_cart = instance._guest_cart
        user_cart, created = Cart.objects.get_or_create(
            user=instance,
            defaults={'status': 'active'}
        )
        
        if not created:
            # Merge guest cart items into user cart
            for item in guest_cart.items.all():
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=item.product,
                    defaults={
                        'quantity': item.quantity,
                        'price': item.price
                    }
                )
                if not created:
                    cart_item.quantity += item.quantity
                    cart_item.save()
            
            # Delete the guest cart
            guest_cart.delete()
            del instance._guest_cart
