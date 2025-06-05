import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def send_order_confirmation_email(order):
    """
    Send order confirmation email to the customer
    
    Args:
        order: Order instance
    """
    try:
        # Prepare context for the email template
        context = {
            'order': order,
            'order_items': order.items.all(),
            'shipping_address': {
                'name': f"{order.first_name} {order.last_name}",
                'email': order.email,
                'phone': order.phone or 'N/A',
                'address': f"{order.address}",
                'address2': f"{order.address2}" if order.address2 else '',
                'city': order.city,
                'state': order.state,
                'postal_code': order.postal_code,
                'country': order.country,
            },
            'subtotal': order.get_total_cost(),
            'shipping_cost': 99.00,  # Assuming fixed shipping cost
            'total': order.get_total_cost() + 99.00  # Including shipping
        }
        
        # Render HTML content
        html_content = render_to_string('emails/order_confirmation.html', context)
        
        # Create plain text version
        text_content = strip_tags(html_content)
        
        # Create email
        subject = f"Order Confirmation - #{order.order_number or order.id}"
        from_email = None  # Uses DEFAULT_FROM_EMAIL from settings
        to_email = [order.email]
        
        # Create email message
        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        msg.send(fail_silently=False)
        logger.info(f"Order confirmation email sent for order #{order.id} to {order.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send order confirmation email for order #{order.id}: {str(e)}", 
                   exc_info=True)
        return False
