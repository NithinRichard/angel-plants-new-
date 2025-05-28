from django.apps import AppConfig
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'
    
    def ready(self):
        # Import signals and connect them
        from . import signals
        from .cart_signals import create_user_cart, update_cart_totals_on_item_change, \
            update_cart_on_item_delete, convert_cart_to_order, merge_guest_cart_with_user
        
        # Connect the profile and cart creation signal
        signals.ready()
        
        # Connect cart signals
        User = get_user_model()
        
        # Connect cart creation signal for new users
        post_save.connect(create_user_cart, sender=User)
        
        # Import models here to avoid AppRegistryNotReady error
        from .models import CartItem, Order
        
        # Connect cart item signals
        post_save.connect(update_cart_totals_on_item_change, sender=CartItem)
        post_save.connect(update_cart_totals_on_item_change, sender=Order)
        
        # Connect cart item deletion signal
        from django.db.models.signals import pre_delete
        pre_delete.connect(update_cart_on_item_delete, sender=CartItem)
        
        # Connect order creation signal
        post_save.connect(convert_cart_to_order, sender=Order)
        
        # Connect guest cart merge signal
        post_save.connect(merge_guest_cart_with_user, sender=User)
