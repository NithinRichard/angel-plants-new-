import logging
import smtplib
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

def test_email_connection():
    """Test SMTP connection and credentials"""
    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=10) as server:
            server.ehlo()
            if settings.EMAIL_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            return True, "SMTP connection successful"
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error: {str(e)}")
        return False, f"SMTP Authentication failed: {str(e)}"
    except Exception as e:
        logger.error(f"SMTP Connection Error: {str(e)}")
        return False, f"SMTP Connection failed: {str(e)}"

def send_order_confirmation_email(order):
    """
    Send order confirmation email to the customer with enhanced error handling
    
    Args:
        order: Order instance
    
    Returns:
        tuple: (success: bool, message: str)
    """
    logger.info(f"Starting email send process for order: {getattr(order, 'id', 'unknown')}")
    
    if not order:
        error_msg = "No order provided"
        logger.error(error_msg)
        return False, error_msg
        
    # Get email from order or user if available
    email = getattr(order, 'email', None)
    if not email and hasattr(order, 'user') and order.user and hasattr(order.user, 'email'):
        email = order.user.email
        logger.info(f"Using user's email from account: {email}")
    
    if not email or not email.strip():
        error_msg = f"No valid email address found for order {getattr(order, 'id', 'unknown')}. Email: {email}"
        logger.error(error_msg)
        return False, error_msg

    try:
        logger.info("Testing SMTP connection...")
        smtp_success, smtp_message = test_email_connection()
        logger.info(f"SMTP Connection Test: {'Success' if smtp_success else 'Failed'} - {smtp_message}")
        if not smtp_success:
            return False, f"SMTP Connection Error: {smtp_message}"
            
        logger.info(f"Preparing email for order {getattr(order, 'id', 'unknown')}")
        logger.info(f"Recipient: {order.email}")

        # Prepare context for the email template
        try:
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
                'shipping_cost': 99.00,  # Fixed shipping cost
                'total': order.get_total_cost() + 99.00  # Including shipping
            }
            
            # Render HTML content
            html_content = render_to_string('emails/order_confirmation.html', context)
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Create email subject with order number
            order_identifier = getattr(order, 'order_number', None) or f"#{getattr(order, 'id', 'N/A')}"
            subject = f"Order Confirmation - {order_identifier}"
            
            # Get email settings
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [order.email]
            
            logger.info(f"Email settings - From: {from_email}, To: {to_email}, Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}")
            logger.info(f"Using TLS: {settings.EMAIL_USE_TLS}, Username: {settings.EMAIL_HOST_USER}")
            logger.info(f"Subject: {subject}")
            
            logger.info(f"Preparing to send order confirmation email to {to_email} for order {order_identifier}")
            
            # Create email message with explicit connection
            logger.info("Creating SMTP connection...")
            try:
                connection = get_connection(
                    host=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    username=settings.EMAIL_HOST_USER,
                    password=settings.EMAIL_HOST_PASSWORD,
                    use_tls=settings.EMAIL_USE_TLS,
                    timeout=10
                )
                logger.info("SMTP connection created successfully")
                
                # Create and send email
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=to_email,
                    connection=connection
                )
                msg.attach_alternative(html_content, "text/html")
                
                # Send email with timeout
                logger.info("Sending email...")
                try:
                    msg.send(fail_silently=False)
                    logger.info("Email sent successfully")
                    
                    # Close the connection
                    connection.close()
                    
                    logger.info(f"Successfully sent order confirmation email for order {order_identifier} to {order.email}")
                    return True, "Email sent successfully"
                    
                except Exception as e:
                    logger.error(f"Failed to send email: {str(e)}", exc_info=True)
                    return False, f"Failed to send email: {str(e)}"
                finally:
                    try:
                        connection.close()
                    except Exception as e:
                        logger.warning(f"Error closing connection: {str(e)}")
            
            except Exception as e:
                logger.error(f"Failed to create SMTP connection: {str(e)}", exc_info=True)
                return False, f"Failed to create SMTP connection: {str(e)}"
            
        except Exception as e:
            error_msg = f"Error preparing email for order {getattr(order, 'id', 'unknown')}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
            
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP Authentication failed for order {getattr(order, 'id', 'unknown')}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
        
    except smtplib.SMTPException as e:
        error_msg = f"SMTP Error sending email for order {getattr(order, 'id', 'unknown')}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"Unexpected error sending email for order {getattr(order, 'id', 'unknown')}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
