from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_order_confirmation_email(order, request=None):
    """
    Send an order confirmation email to the customer
    """
    subject = f"Order Confirmation - #{order.id}"
    
    # Prepare context for the email template
    context = {
        'order': order,
        'items': order.items.all(),
        'total': order.get_total_cost(),
    }
    
    # Render HTML email
    html_content = render_to_string('emails/order_confirmation.html', context)
    text_content = strip_tags(html_content)  # Strip the HTML for the plain text version
    
    # Create the email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
        reply_to=[settings.CONTACT_EMAIL],
    )
    
    # Attach the HTML version of the email
    email.attach_alternative(html_content, "text/html")
    
    try:
        # Send the email
        email.send(fail_silently=False)
        return True
    except Exception as e:
        if request and hasattr(request, 'session'):
            messages.error(request, f"Failed to send confirmation email: {str(e)}")
        return False


def send_contact_form_email(form_data, request=None):
    """
    Send an email when someone submits the contact form
    """
    subject = f"New Contact Form Submission: {form_data.get('subject', 'No Subject')}"
    
    # Prepare context for the email template
    context = {
        'name': form_data.get('name'),
        'email': form_data.get('email'),
        'subject': form_data.get('subject'),
        'message': form_data.get('message'),
    }
    
    # Render HTML email
    html_content = render_to_string('emails/contact_form.html', context)
    text_content = strip_tags(html_content)  # Strip the HTML for the plain text version
    
    # Create the email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_EMAIL],
        reply_to=[form_data.get('email')],
    )
    
    # Attach the HTML version of the email
    email.attach_alternative(html_content, "text/html")
    
    try:
        # Send the email
        email.send(fail_silently=False)
        return True
    except Exception as e:
        if request and hasattr(request, 'session'):
            messages.error(request, f"Failed to send your message: {str(e)}")
        return False


def calculate_cart_total(cart):
    """
    Calculate the total price of items in the cart
    """
    total = 0
    for item in cart:
        if 'price' in item and 'quantity' in item:
            total += item['price'] * item['quantity']
    return total


def get_client_ip(request):
    """
    Get the client's IP address from the request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
