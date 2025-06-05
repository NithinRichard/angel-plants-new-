#!/usr/bin/env python
import os
import sys
import logging
import smtplib
import django
from django.conf import settings
from django.core.mail import send_mail

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('email_test.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_django():
    """Set up Django environment"""
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()

def test_smtp_connection():
    """Test SMTP server connection"""
    try:
        logger.info("Testing SMTP connection...")
        email_host = getattr(settings, 'EMAIL_HOST', 'smtp.gmail.com')
        email_port = getattr(settings, 'EMAIL_PORT', 587)
        email_host_user = getattr(settings, 'EMAIL_HOST_USER', '')
        
        logger.info(f"Connecting to {email_host}:{email_port} as {email_host_user}")
        
        with smtplib.SMTP(email_host, email_port, timeout=10) as server:
            server.ehlo()
            if getattr(settings, 'EMAIL_USE_TLS', True):
                server.starttls()
                logger.info("TLS connection established")
            
            email_host_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            if email_host_user and email_host_password:
                server.login(email_host_user, email_host_password)
                logger.info("Successfully authenticated with SMTP server")
            
            return True, "SMTP connection successful"
            
    except Exception as e:
        error_msg = f"SMTP connection failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def test_send_email():
    """Test sending a simple email"""
    try:
        # Test SMTP connection first
        smtp_success, smtp_message = test_smtp_connection()
        if not smtp_success:
            logger.error(f"Cannot send email: {smtp_message}")
            return False
            
        # Use the default from email if no test email is set
        to_email = getattr(settings, 'TEST_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        logger.info(f"Sending test email to: {to_email}")
        logger.info(f"Using email backend: {settings.EMAIL_BACKEND}")
        
        # Send a test email
        result = send_mail(
            'Test Email from Angel Plants',
            'This is a test email from Angel Plants.',
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
        
        logger.info(f"Email send result: {result}")
        print(f"✅ Test email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logger.exception("Failed to send test email")
        print(f"❌ Failed to send test email: {str(e)}")
        return False

if __name__ == "__main__":
    print("Setting up Django...")
    setup_django()
    
    print("\n=== Starting Email Test ===")
    print(f"Django version: {django.get_version()}")
    print(f"Email backend: {settings.EMAIL_BACKEND}")
    print(f"Email host: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
    
    print("\nTesting email sending...")
    success = test_send_email()
    
    if success:
        print("\n✅ Email test completed successfully!")
    else:
        print("\n❌ Email test failed. Check the logs for details.")
    
    print("\nTest completed. Check email_test.log for detailed logs.")
