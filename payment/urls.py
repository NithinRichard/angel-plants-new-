from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # Create Razorpay order
    path('create-order/', views.create_order, name='create_order'),
    
    # Payment success callback
    path('success/', views.payment_success, name='payment_success'),
    
    # Payment failed callback
    path('failed/', views.payment_failed, name='payment_failed'),
    
    # Webhook endpoint for Razorpay
    path('webhook/', views.payment_webhook, name='payment_webhook'),
]
