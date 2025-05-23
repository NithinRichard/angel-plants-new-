import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import get_user_model
from store.models import Order, Payment, Product, Cart, CartItem

User = get_user_model()

class PaymentIntegrationTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create a test product
        self.product = Product.objects.create(
            name='Test Plant',
            slug='test-plant',
            price=Decimal('19.99'),
            stock=10,
            available=True
        )
        
        # Create a cart and add the product
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Create a test order
        self.order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='test@example.com',
            address='123 Test St',
            postal_code='12345',
            city='Test City',
            total_amount=Decimal('39.98'),
            status='pending'
        )
        
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_payment_page_loads(self):
        """Test that the payment page loads correctly"""
        response = self.client.get(reverse('store:payment', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/payment/payment_form.html')
        self.assertContains(response, 'Pay with Razorpay')
    
    def test_create_razorpay_order(self):
        """Test creating a Razorpay order"""
        response = self.client.post(
            reverse('store:create_razorpay_order'),
            {'order_id': self.order.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('id', data)
        self.assertIn('amount', data)
        self.assertEqual(data['currency'], 'INR')
    
    def test_payment_success_redirect(self):
        """Test successful payment redirect"""
        # In a real test, you would mock the Razorpay API
        # This is just testing the redirect flow
        response = self.client.get(
            reverse('store:payment_success') + f'?order_id=order_test123&payment_id=pay_test123&signature=test_signature',
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/payment/payment_success.html')
    
    def test_payment_failed_redirect(self):
        """Test failed payment redirect"""
        response = self.client.get(
            reverse('store:payment_failed') + '?order_id=123&error_code=PAYMENT_ERROR&error_description=Payment+failed',
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'store/payment/payment_failed.html')
        self.assertContains(response, 'Payment Failed')


class PaymentUtilsTest(TestCase):
    def test_create_razorpay_order(self):
        """Test creating a Razorpay order"""
        from store.payment_utils import create_razorpay_order
        
        # Test with valid amount
        order = create_razorpay_order(100, 'INR', 'test_receipt', {'notes': 'test'})
        self.assertIsNotNone(order)
        self.assertIn('id', order)
        self.assertEqual(order['amount'], 10000)  # 100 INR in paise
        
        # Test with invalid amount
        order = create_razorpay_order(0.5, 'INR')  # Less than minimum amount
        self.assertIsNone(order)
    
    def test_verify_payment_signature(self):
        """Test payment signature verification"""
        from store.payment_utils import verify_payment_signature
        
        # This is a mock test - in a real test, you would use actual test data from Razorpay
        # Here we're just testing the function signature and basic behavior
        result = verify_payment_signature('order_test123', 'pay_test123', 'test_signature')
        self.assertIsInstance(result, bool)


class PaymentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        
        self.order = Order.objects.create(
            user=self.user,
            first_name='Test',
            last_name='User',
            email='test2@example.com',
            address='123 Test St',
            postal_code='12345',
            city='Test City',
            total_amount=Decimal('99.99'),
            status='pending'
        )
    
    def test_create_payment(self):
        """Test creating a payment record"""
        payment = Payment.objects.create(
            order=self.order,
            payment_id='pay_test123',
            amount=Decimal('99.99'),
            payment_method='razorpay',
            status='captured',
            raw_data=json.dumps({'test': 'data'})
        )
        
        self.assertEqual(str(payment), f'Payment {payment.id} for Order {self.order.id}')
        self.assertEqual(payment.amount, Decimal('99.99'))
        self.assertEqual(payment.status, 'captured')
