#!/usr/bin/env python
import os
import sys
import django
from django.conf import settings
from django.core.mail import send_mail

def setup_django():
    """Set up Django environment"""
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()

def test_send_email():
    """Test sending a simple email"""
    try:
        # Use the default from email if no test email is set
        to_email = getattr(settings, 'TEST_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        print(f"Sending test email to: {to_email}")
        print(f"Using email backend: {settings.EMAIL_BACKEND}")
        print(f"Email host: {settings.EMAIL_HOST}")
        print(f"Email port: {settings.EMAIL_PORT}")
        
        # Send a test email
        result = send_mail(
            'Test Email from Angel Plants',
            'This is a test email from Angel Plants.\n\nIf you received this, email is working correctly!',
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
        
        print(f"Email send result: {result}")
        print("✅ Test email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test email: {str(e)}")
        return False

if __name__ == "__main__":
    print("Setting up Django...")
    setup_django()
    
    print("\n=== Starting Email Test ===")
    print(f"Django version: {django.get_version()}")
    
    print("\nTesting email sending...")
    success = test_send_email()
    
    if success:
        print("\n✅ Email test completed successfully!")
    else:
        print("\n❌ Email test failed. Check the output for details.")
