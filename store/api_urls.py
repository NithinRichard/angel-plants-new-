"""
URL patterns for the store API endpoints.
"""
from django.urls import path
from .api.cart_views import (
    api_add_to_cart, 
    api_remove_from_cart, 
    api_get_cart,
    api_apply_coupon,
    api_remove_coupon
)

app_name = 'store_api'

urlpatterns = [
    # Cart endpoints
    path('cart/', api_get_cart, name='api_cart'),
    path('cart/add/', api_add_to_cart, name='api_add_to_cart'),
    path('cart/remove/<int:product_id>/', api_remove_from_cart, name='api_remove_from_cart'),
    path('cart/remove/', api_remove_from_cart, name='api_remove_from_cart_post'),
    
    # Coupon endpoints
    path('cart/coupon/apply/', api_apply_coupon, name='api_apply_coupon'),
    path('cart/coupon/remove/', api_remove_coupon, name='api_remove_coupon'),
]

api_urlpatterns = urlpatterns
