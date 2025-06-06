from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Order

class UpdateOrderStatusForm(forms.ModelForm):
    """Form for updating order status and tracking information"""
    tracking_number = forms.CharField(
        label=_('Tracking Number'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'vTextField'})
    )
    tracking_url = forms.URLField(
        label=_('Tracking URL'),
        required=False,
        widget=forms.URLInput(attrs={'class': 'vURLField'})
    )
    shipping_provider = forms.CharField(
        label=_('Shipping Provider'),
        required=False,
        widget=forms.TextInput(attrs={'class': 'vTextField'})
    )
    delivery_notes = forms.CharField(
        label=_('Delivery Notes'),
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'vLargeTextField'})
    )

    class Meta:
        model = Order
        fields = [
            'status', 
            'tracking_number', 
            'tracking_url', 
            'shipping_provider',
            'delivery_instructions'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'vSelect2Field'}),
            'delivery_instructions': forms.Textarea(attrs={'rows': 3, 'class': 'vLargeTextField'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show statuses that make sense for the current status
        current_status = self.instance.status if self.instance else None
        status_choices = []
        
        if current_status == Order.Status.PENDING:
            status_choices = [
                (Order.Status.CONFIRMED, _('Confirm Order')),
                (Order.Status.CANCELLED, _('Cancel Order')),
            ]
        elif current_status == Order.Status.CONFIRMED:
            status_choices = [
                (Order.Status.PROCESSING, _('Start Processing')),
                (Order.Status.CANCELLED, _('Cancel Order')),
            ]
        elif current_status == Order.Status.PROCESSING:
            status_choices = [
                (Order.Status.READY_FOR_SHIPMENT, _('Mark as Ready for Shipment')),
                (Order.Status.CANCELLED, _('Cancel Order')),
            ]
        elif current_status == Order.Status.READY_FOR_SHIPMENT:
            status_choices = [
                (Order.Status.IN_TRANSIT, _('Ship Order')),
                (Order.Status.CANCELLED, _('Cancel Order')),
            ]
        elif current_status == Order.Status.IN_TRANSIT:
            status_choices = [
                (Order.Status.OUT_FOR_DELIVERY, _('Out for Delivery')),
                (Order.Status.CANCELLED, _('Cancel Order')),
            ]
        elif current_status == Order.Status.OUT_FOR_DELIVERY:
            status_choices = [
                (Order.Status.DELIVERED, _('Mark as Delivered')),
            ]
        
        # Add the current status to the choices if it's not already there
        if current_status and not any(choice[0] == current_status for choice in status_choices):
            status_choices.insert(0, (current_status, f"Keep as {self.instance.get_status_display()}"))
        
        self.fields['status'].choices = status_choices
    
    def save(self, commit=True):
        order = super().save(commit=False)
        if commit:
            order.save()
        return order
