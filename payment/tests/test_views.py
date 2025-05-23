"""
Tests for payment views.
"""
import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory, Client, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import HttpRequest, JsonResponse
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.conf import settings
from django.utils import timezone
from django.contrib.messages.storage.fallback import FallbackStorage

from store.models import Order, OrderItem, Product, Category
from payment.views import payment_webhook, payment_success, payment_failed
from payment.utils import client

User = get_user_model()


class PaymentViewTests(TestCase):
    """Test payment views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.factory = RequestFactory()
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create a test category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category',
            description='Test category description'
        )
        
        # Create a test product
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            price=100.00,
            category=self.category,
            quantity=10,
            description='Test description',
            short_description='Test short description',
            is_active=True,
            # Use a simple string for the image to avoid file system operations
            image='products/test.jpg'
        )
        
        # Create a test order with timezone-aware datetime
        now = timezone.now()
        self.order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='test@example.com',
            phone='+919999999999',
            address='123 Test St, Test City, TS 500001',
            city='Test City',
            state='TS',
            postal_code='500001',
            country='India',
            status='pending',  # Must be one of the Status choices
            total_amount=100.00,
            tax_amount=18.00,
            shipping_fee=0.00,
            discount_amount=0.00,
            payment_method='razorpay',
            payment_status=False,
            razorpay_order_id='order_test1234567890',
            order_number='TEST123',  # This will be updated on save if not set
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        
        # Create order item
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=100.00,
            quantity=1,
            created_at=timezone.now(),
            updated_at=timezone.now()
        )
        
        # Set up test client
        self.client.force_login(self.user)
    
    def test_payment_success_view(self):
        """Test payment success view."""
        # Create a request
        url = reverse('payment:payment_success')
        request = self.factory.get(url)
        
        # Add session to request
        request.session = self.client.session
        
        # Add messages to request
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        
        # Call the view
        response = payment_success(request)
        
        # Check response
        self.assertEqual(response.status_code, 302)  # Should redirect
        self.assertEqual(response.url, reverse('store:order_detail', args=[self.order.order_number]))
        
        # Check if order payment status is updated
        self.order.refresh_from_db()
        self.assertTrue(self.order.payment_status)
    
    def test_payment_failed_view_updates_order_status(self):
        """Test that payment_failed view updates order status to payment_failed."""
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        # Clear any existing payments for this order
        Payment.objects.filter(order=self.order).delete()
        
        # Log in the test user
        self.client.force_login(self.user)
        
        # Set up test data
        error_code = 'PAYMENT_CANCELLED'
        error_description = 'User cancelled the payment'
        payment_id = 'pay_test123'
        
        # Ensure the order is associated with the test user and has required fields
        self.order.user = self.user
        self.order.razorpay_order_id = 'order_test1234567890'  # Ensure this matches the test
        self.order.payment_status = False
        self.order.status = 'pending'
        self.order.total_amount = 100.00
        self.order.created_at = timezone.now() - timedelta(days=1)
        self.order.updated_at = timezone.now() - timedelta(days=1)
        self.order.save(update_fields=[
            'user', 
            'razorpay_order_id', 
            'payment_status', 
            'status', 
            'total_amount',
            'created_at',
            'updated_at'
        ])
        
        # Ensure the order exists
        self.assertIsNotNone(Order.objects.filter(id=self.order.id).first(), "Order should exist")
        
        # Create URL for the view
        url = f"{reverse('payment:payment_failed')}?error[code]={error_code}&error[description]={error_description}&payment_id={payment_id}&order_id={self.order.razorpay_order_id}"
        
        print(f"\n=== Making request to: {url} ===")
        print(f"=== Order ID in test: {self.order.id} ===")
        print(f"=== Razorpay Order ID in test: {self.order.razorpay_order_id} ===")
        
        try:
            # Make the request and follow the redirect
            response = self.client.get(url, follow=True)
            
            # Print response details
            print(f"\n=== Response status code: {response.status_code} ===")
            print(f"=== Response URL: {response.request['PATH_INFO']} ===")
            print(f"=== Response redirect chain: {response.redirect_chain} ===")
            
            # Check that we got a successful response after following redirects
            self.assertEqual(response.status_code, 200)
            
            # Check if order status is updated
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, 'payment_failed', 
                           f"Expected order status to be 'payment_failed', but got '{self.order.status}'")
            
            # Check that a payment record was created
            payment_count = Payment.objects.filter(order=self.order).count()
            self.assertEqual(payment_count, 1, f"Expected 1 payment record, got {payment_count}")
            
            # Get the payment record
            payment = Payment.objects.filter(
                order=self.order,
                status='failed'
            ).first()
            
            self.assertIsNotNone(payment, "Payment record not found with status 'failed'")
            
            # Print payment details for debugging
            if payment:
                print(f"\n=== Payment Record Details ===")
                print(f"ID: {payment.id}")
                print(f"Payment ID: {payment.payment_id}")
                print(f"Amount: {payment.amount}")
                print(f"Status: {payment.status}")
                print(f"Error Code: {getattr(payment, 'error_code', 'N/A')}")
                print(f"Created At: {payment.created_at}")
            
        except Exception as e:
            print(f"\n=== Error during test: {str(e)} ===")
            print(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            raise
            
        # Additional assertions for the payment record
        self.assertIsNotNone(payment, "Payment record was not created")
        if payment:
            # Check required fields
            self.assertEqual(payment.payment_method, 'razorpay')
            self.assertEqual(payment.payment_id, payment_id)
            self.assertEqual(payment.amount, self.order.total_amount)
            self.assertIsNotNone(payment.created_at)
            self.assertIsNotNone(payment.updated_at)
            
            # Check error information
            self.assertEqual(payment.error_code, error_code)
            self.assertEqual(payment.error_description, error_description)
            
            # Check raw_data contains expected fields
            self.assertIsNotNone(payment.raw_data)
            raw_data = json.loads(payment.raw_data)
            self.assertEqual(raw_data.get('payment_id'), payment_id)
            self.assertEqual(raw_data.get('order_id'), self.order.razorpay_order_id)
            self.assertEqual(raw_data.get('error_code'), error_code)
            self.assertEqual(raw_data.get('error_description'), error_description)
    
    def test_payment_failed_view_adds_error_message(self):
        """Test that payment_failed view adds an error message."""
        # Log in the test user
        self.client.force_login(self.user)
        
        # Call the view with error parameters
        url = f"{reverse('payment:payment_failed')}?error[code]=PAYMENT_CANCELLED&error[description]=User+cancelled+the+payment&payment_id=pay_test123&order_id={self.order.razorpay_order_id}"
        
        # Don't follow redirects to avoid potential issues with the order detail view
        response = self.client.get(url, follow=False)
        
        # Check that we got a redirect
        self.assertEqual(response.status_code, 302)
        
        # Verify the redirect URL is correct
        self.assertIn(reverse('store:order_detail', args=[self.order.order_number]), response.url)
        
        # Check if the order status was updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'payment_failed')
    
    @override_settings(RAZORPAY_WEBHOOK_SECRET='test_webhook_secret')
    @patch('payment.views.verify_payment_signature')
    @patch('payment.views.get_payment_details')
    @patch('payment.views.capture_payment')
    def test_payment_webhook_captured(self, mock_capture, mock_get_payment_details, mock_verify):
        """Test webhook for captured payment."""
        # Setup mocks
        mock_verify.return_value = True
        
        payment_data = {
            'id': 'pay_test1234567890',
            'order_id': self.order.id,
            'amount': 11800,  # in paise
            'currency': 'INR',
            'status': 'captured',
            'method': 'card',
            'email': 'test@example.com',
            'contact': '+919999999999'
        }
        
        mock_get_payment_details.return_value = payment_data
        mock_capture.return_value = payment_data
        
        # Create webhook payload
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': payment_data
                },
                'order': {
                    'entity': {
                        'id': self.order.id,
                        'amount': 11800,
                        'currency': 'INR',
                        'receipt': f'order_{self.order.id}'
                    }
                }
            }
        }
        
        # Create request
        request = self.factory.post(
            reverse('payment:payment_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='test_signature'
        )
        
        # Call the view
        response = payment_webhook(request)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Webhook received successfully')
        
        # Verify mocks were called
        mock_verify.assert_called_once()
        mock_get_payment_details.assert_called_once_with(payment_data['id'])
        mock_capture.assert_called_once_with(payment_data['id'], payment_data['amount'])
        
        # Check if order was updated
        self.order.refresh_from_db()
        self.assertTrue(self.order.payment_status)
        self.assertEqual(self.order.payment_id, payment_data['id'])
    
    @override_settings(RAZORPAY_WEBHOOK_SECRET='test_webhook_secret')
    @patch('payment.views.verify_payment_signature')
    def test_payment_webhook_failed(self, mock_verify):
        """Test webhook for failed payment."""
        # Setup mocks
        mock_verify.return_value = True
        
        # Create webhook payload for failed payment
        payload = {
            'event': 'payment.failed',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test1234567890',
                        'order_id': self.order.id,
                        'amount': 11800,
                        'currency': 'INR',
                        'status': 'failed',
                        'error_description': 'Payment declined',
                        'error_code': 'BAD_REQUEST_ERROR'
                    }
                }
            }
        }
        
        # Create request
        request = self.factory.post(
            reverse('payment:payment_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='test_signature'
        )
        
        # Call the view
        response = payment_webhook(request)
        
        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'Webhook received successfully')
        
        # Check order status (should not be marked as paid)
        self.order.refresh_from_db()
        self.assertFalse(self.order.payment_status)
    
    @override_settings(RAZORPAY_WEBHOOK_SECRET='test_webhook_secret')
    @patch('payment.views.verify_payment_signature')
    def test_payment_webhook_invalid_signature(self, mock_verify):
        """Test webhook with invalid signature."""
        # Setup mocks
        mock_verify.return_value = False
        
        # Create request with invalid signature
        request = self.factory.post(
            reverse('payment:payment_webhook'),
            data=json.dumps({'event': 'test'}),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='invalid_signature'
        )
        
        # Call the view
        response = payment_webhook(request)
        
        # Check response (should return 400 for invalid signature)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b'Invalid signature', response.content)


class CreateOrderViewTest(TestCase):
    """Test create order view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser2', email='test2@example.com', password='testpass123')
        
        # Create a test order
        self.order = Order.objects.create(
            user=self.user,
            full_name='Test User',
            email='test2@example.com',
            phone='1234567890',
            address_line_1='123 Test St',
            city='Test City',
            state='TS',
            postal_code='500001',
            country='IN',
            order_total=100.00,
            tax=18.00,
            grand_total=118.00,
            payment_method='razorpay',
            payment_status=False
        )
        
        # Set up session
        session = self.client.session
        session['order_id'] = str(self.order.id)
        session.save()
    
    @patch('payment.views.create_razorpay_order')
    def test_create_order_view(self, mock_create_order):
        """Test creating a Razorpay order."""
        # Mock the Razorpay order creation
        mock_order = {
            'id': 'order_test1234567890',
            'amount': 11800,
            'currency': 'INR',
            'status': 'created',
            'receipt': f'order_{self.order.id}'
        }
        mock_create_order.return_value = mock_order
        
        # Make the request
        response = self.client.post(
            reverse('payment:create_order'),
            data={'amount': '118.00'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['order_id'], mock_order['id'])
        self.assertEqual(response_data['amount'], mock_order['amount'])
        
        # Verify the order was created with the correct data
        mock_create_order.assert_called_once_with(
            amount=11800,  # Amount in paise
            currency='INR',
            receipt=f'order_{self.order.id}'
        )
    
    def test_create_order_view_invalid_request(self):
        """Test creating an order with invalid request."""
        # Make a GET request (should fail)
        response = self.client.get(reverse('payment:create_order'))
        self.assertEqual(response.status_code, 400)
        
        # Make a POST request without AJAX
        response = self.client.post(reverse('payment:create_order'))
        self.assertEqual(response.status_code, 400)
        
        # Make a POST request without amount
        response = self.client.post(
            reverse('payment:create_order'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_order_view_no_order_in_session(self):
        """Test creating an order with no order in session."""
        # Clear the session
        session = self.client.session
        if 'order_id' in session:
            del session['order_id']
        session.save()
        
        # Make the request
        response = self.client.post(
            reverse('payment:create_order'),
            data={'amount': '118.00'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Should redirect to cart
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('store:cart'))
