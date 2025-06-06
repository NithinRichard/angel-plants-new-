from django.urls import path
from django.views.decorators.http import require_http_methods
from . import views

app_name = 'payment'

urlpatterns = [
    # Root view - Lists all available endpoints
    path('', views.payment_home, name='payment_home'),
    
    # Create Razorpay order
    path('create-order/', views.create_order, name='create_order'),
    
    # Payment success callback
    path('success/', views.payment_success, name='payment_success'),
    
    # Payment failed callback
    path('failed/', views.payment_failed, name='payment_failed'),
    
    # Webhook endpoint for Razorpay
    path('webhook/', views.payment_webhook, name='payment_webhook'),
    
    # Payment verification endpoint (POST only)
    path('verify-payment/', require_http_methods(['POST'])(views.verify_payment), name='verify_payment'),
]
