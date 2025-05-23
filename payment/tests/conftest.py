"""
Pytest configuration and fixtures for payment app tests.
"""
import pytest
from django.contrib.auth import get_user_model
from store.models import Order, Product, Category, OrderItem

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(client, test_user):
    """Return a client with an authenticated user."""
    client.force_login(test_user)
    return client


@pytest.fixture
def test_category(db):
    """Create a test category."""
    return Category.objects.create(
        name='Test Category',
        slug='test-category'
    )


@pytest.fixture
def test_product(test_category, db):
    """Create a test product."""
    return Product.objects.create(
        name='Test Product',
        slug='test-product',
        price=100.00,
        category=test_category,
        stock=10
    )


@pytest.fixture
def test_order(test_user, db):
    """Create a test order."""
    return Order.objects.create(
        user=test_user,
        full_name='Test User',
        email='test@example.com',
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


@pytest.fixture
def test_order_item(test_order, test_product, db):
    """Create a test order item."""
    return OrderItem.objects.create(
        order=test_order,
        product=test_product,
        quantity=1,
        price=100.00
    )


@pytest.fixture
def razorpay_order_data(test_order):
    """Return sample Razorpay order data."""
    return {
        'id': 'order_test1234567890',
        'amount': 11800,  # in paise
        'currency': 'INR',
        'status': 'created',
        'receipt': f'order_{test_order.id}'
    }


@pytest.fixture
def razorpay_payment_data(test_order):
    """Return sample Razorpay payment data."""
    return {
        'id': 'pay_test1234567890',
        'order_id': test_order.id,
        'amount': 11800,  # in paise
        'currency': 'INR',
        'status': 'captured',
        'method': 'card',
        'email': 'test@example.com',
        'contact': '+919999999999'
    }


@pytest.fixture
def webhook_payload(test_order, razorpay_payment_data):
    """Return sample webhook payload."""
    return {
        'event': 'payment.captured',
        'payload': {
            'payment': {
                'entity': razorpay_payment_data
            },
            'order': {
                'entity': {
                    'id': test_order.id,
                    'amount': 11800,
                    'currency': 'INR',
                    'receipt': f'order_{test_order.id}'
                }
            }
        }
    }
