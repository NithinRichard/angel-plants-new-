"""
Signals for the store app
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction

# Import the Profile model inside the function to avoid circular imports

def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Create or update the user profile
    """
    # Import here to avoid AppRegistryNotReady error
    from .models import Profile
    
    if created:
        Profile.objects.get_or_create(user=instance)
    elif hasattr(instance, 'profile'):
        instance.profile.save()

# Connect the signal when Django is ready
def ready():
    from django.db.models.signals import post_save
    from django.apps import apps
    
    User = apps.get_model('auth', 'User')
    post_save.connect(create_or_update_user_profile, sender=User)
    
    # Also handle the custom user model if it exists
    try:
        from django.conf import settings
        if hasattr(settings, 'AUTH_USER_MODEL'):
            CustomUser = apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])
            if CustomUser != User:
                post_save.connect(create_or_update_user_profile, sender=CustomUser)
    except (LookupError, AttributeError):
        pass
