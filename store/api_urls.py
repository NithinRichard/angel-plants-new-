"""
URL patterns for the store API endpoints.
"""
from django.urls import path
from .api.cart_views import (
    api_add_to_cart, 
    api_remove_from_cart, 
    api_get_cart
)

app_name = 'store_api'

urlpatterns = [
    # Cart endpoints
    path('cart/', api_get_cart, name='api_cart'),
    path('cart/add/', api_add_to_cart, name='api_add_to_cart'),
    path('cart/remove/<int:product_id>/', api_remove_from_cart, name='api_remove_from_cart'),
    path('cart/remove/', api_remove_from_cart, name='api_remove_from_cart_post'),
    

]

api_urlpatterns = urlpatterns


