"""
Signals for the store app
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from .models import Order, OrderStatusUpdate


def track_order_status_change(sender, instance, **kwargs):
    """
    Track order status changes and create status updates
    """
    if not instance.pk:  # New order
        return
        
    try:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:  # Status changed
            OrderStatusUpdate.create_status_update(
                order=instance,
                status=instance.status,
                note=f"Order status changed from {old_instance.get_status_display()} to {instance.get_status_display()}"
            )
            
            # Update delivery dates based on status
            if instance.status == Order.Status.DELIVERED and not instance.actual_delivery_date:
                instance.actual_delivery_date = timezone.now()
    except sender.DoesNotExist:
        pass  # New instance


def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update the user profile and cart when a user is created or updated
    """
    # Import here to avoid AppRegistryNotReady error
    from .models import Profile, Cart
    
    if created:
        # Create profile if it doesn't exist
        Profile.objects.get_or_create(user=instance)
        
        # Create a new cart for the user
        Cart.objects.get_or_create(
            user=instance,
            defaults={'status': 'active'}
        )
    elif hasattr(instance, 'profile'):
        instance.profile.save()


def create_cart_for_new_user(user):
    """Helper function to create a cart for a new user"""
    from .models import Cart
    Cart.objects.get_or_create(
        user=user,
        defaults={'status': 'active'}
    )


# Connect the signals when Django is ready
def ready():
    from django.db.models.signals import post_save, pre_save
    from django.apps import apps
    
    # Connect user signals
    User = apps.get_model('auth', 'User')
    post_save.connect(create_or_update_user_profile, sender=User)
    
    # Connect order signals
    post_save.connect(track_order_status_change, sender=Order)
    
    # Also handle the custom user model if it exists
    try:
        if hasattr(settings, 'AUTH_USER_MODEL'):
            CustomUser = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])
            if CustomUser != User:
                post_save.connect(create_or_update_user_profile, sender=CustomUser)
    except (LookupError, AttributeError):
        pass
    
    # Import and connect other signals
    from . import cart_signals  # noqa
    
    # Ensure the signal is connected when Django starts
    from django.db.models.signals import post_migrate
    from django.apps import AppConfig
    
    class StoreConfig(AppConfig):
        name = 'store'
        
        def ready(self):
            # Connect signals
            post_save.connect(create_or_update_user_profile, sender=User)
            
            # Connect to post_migrate to ensure signals are connected after migrations
            post_migrate.connect(lambda *args, **kwargs: None, sender=self)
