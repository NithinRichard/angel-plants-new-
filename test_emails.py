#!/usr/bin/env python
import os
import sys
import django
import django.conf

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')

try:
    django.setup()
    from django.conf import settings
    from django.core.mail import send_mail
    from store.models import Order, User
except Exception as e:
    print(f"Error setting up Django: {str(e)}")
    sys.exit(1)

def test_basic_email():
    """Test basic email sending functionality"""
    try:
        # Use admin email as fallback if TEST_EMAIL is not set
        test_email = getattr(settings, 'TEST_EMAIL', settings.ADMIN_EMAIL if hasattr(settings, 'ADMIN_EMAIL') else settings.DEFAULT_FROM_EMAIL)
        
        send_mail(
            'Test Email',
            'This is a test email from Angel Plants.',
            settings.DEFAULT_FROM_EMAIL,
            [test_email],
            fail_silently=False,
        )
        print(f"Basic email sent successfully to {test_email}!")
        return True
    except Exception as e:
        print(f"Basic email test failed: {str(e)}")
        print("Make sure your email settings in settings.py are correct and the email backend is properly configured.")
        return False

def test_smtp_connection():
    """Test SMTP connection"""
    try:
        from store.email_utils import test_email_connection
        success, message = test_email_connection()
        if success:
            print(f"SMTP Test: SUCCESS - {message}")
            return True
        else:
            print(f"SMTP Test: FAILED - {message}")
            return False
    except Exception as e:
        print(f"SMTP Test: ERROR - {str(e)}")
        return False

def test_order_confirmation_email():
    """Test sending order confirmation email"""
    try:
        from store.email_utils import send_order_confirmation_email
        from django.core.exceptions import ObjectDoesNotExist
        
        # Create a mock order object for testing
        class MockOrder:
            def __init__(self, email=None, id=999):
                self.id = id
                self.email = email or getattr(settings, 'TEST_EMAIL', 'test@example.com')
                self.order_number = f"TEST-{id}"
                self.total_amount = 99.99
                self.status = "Confirmed"
                self.payment_status = True
                self.created_at = "2023-01-01"
                self.get_total_cost = lambda: self.total_amount
                self.get_items = lambda: [{
                    'product': {'name': 'Test Product'},
                    'quantity': 1,
                    'price': 99.99
                }]
                
        # Create a test order with a test email
        test_email = getattr(settings, 'TEST_EMAIL', 'test@example.com')
        test_order = MockOrder(email=test_email)
        
        print(f"Using test order with email: {test_order.email}")
        
        # Test sending the email
        success, message = send_order_confirmation_email(test_order)
        
        if success:
            print(f"Order email test: SUCCESS - {message}")
            return True
        else:
            print(f"Order email test: FAILED - {message}")
            return False
            
    except Exception as e:
        print(f"Order email test: ERROR - {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing basic email send...")
    test_basic_email()
    
    print("\nTesting SMTP connection...")
    test_smtp_connection()
    
    print("\nTesting order confirmation email...")
    test_order_confirmation_email()
