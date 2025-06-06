from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

@register.filter(name='order_status_bg')
def order_status_bg(status):
    """Return appropriate background class based on order status"""
    status_bg_map = {
        'pending': 'warning',
        'confirmed': 'info',
        'processing': 'primary',
        'ready_for_shipment': 'info',
        'in_transit': 'info',
        'out_for_delivery': 'primary',
        'delivered': 'success',
        'cancelled': 'danger',
        'return_requested': 'warning',
        'returned': 'secondary',
        'refunded': 'secondary',
    }
    return status_bg_map.get(status, 'secondary')
