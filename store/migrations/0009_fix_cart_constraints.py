from django.db import migrations

def clean_duplicate_carts(apps, schema_editor):
    """Clean up any duplicate active carts."""
    Cart = apps.get_model('store', 'Cart')
    
    # Get all users with multiple active carts
    from django.db.models import Count
    
    # Find users with multiple active carts
    duplicate_users = Cart.objects.filter(status='active').values('user')\
        .annotate(cart_count=Count('id'))\
        .filter(cart_count__gt=1)\
        .values_list('user', flat=True)
    
    # For each user with multiple carts, keep the most recent one
    for user_id in duplicate_users:
        # Get all active carts for this user, ordered by creation date (newest first)
        user_carts = Cart.objects.filter(user_id=user_id, status='active')\
            .order_by('-created_at')
        
        if user_carts.count() > 1:
            # Keep the first (newest) cart, mark others as abandoned
            latest_cart = user_carts.first()
            user_carts.exclude(pk=latest_cart.pk).update(status='abandoned')

class Migration(migrations.Migration):
    dependencies = [
        ('store', '0008_merge_20250530_1618'),
    ]

    operations = [
        migrations.RunPython(clean_duplicate_carts, migrations.RunPython.noop),
    ]
