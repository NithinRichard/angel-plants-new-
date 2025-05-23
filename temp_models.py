from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


class Wishlist(models.Model):
    """
    Model to store user's wishlist items
    """
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name=_('user'),
        db_index=True,
        null=True,  # Allow null for anonymous users
        blank=True  # Allow blank in forms
    )
    product = models.ForeignKey(
        'store.Product',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        verbose_name=_('product'),
        db_index=True
    )
    quantity = models.PositiveIntegerField(
        _('quantity'),
        default=1,
        help_text=_('Number of items')
    )
    notes = models.TextField(
        _('notes'),
        blank=True,
        help_text=_('Any additional notes about this item')
    )
    is_public = models.BooleanField(
        _('is public'),
        default=False,
        help_text=_('Allow others to see this wishlist item')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True, db_index=True)
    
    class Meta:
        app_label = 'store'
        verbose_name = _('wishlist item')
        verbose_name_plural = _('wishlist items')
        ordering = ['-created_at']
        unique_together = ['user', 'product']
    
    def __str__(self):
        username = self.user.get_username() if self.user else 'Anonymous'
        product_name = getattr(self.product, 'name', 'Unknown Product')
        return f"{username}'s wishlist: {product_name} (x{self.quantity})"
