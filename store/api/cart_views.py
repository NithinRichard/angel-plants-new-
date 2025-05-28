"""
API views for cart operations.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal
import json

from ..models import Cart, CartItem, Product
from ..cart_utils import add_to_cart, remove_from_cart, get_cart_items


@csrf_exempt
@require_http_methods(["POST"])
def api_add_to_cart(request):
    """
    API endpoint to add a product to the cart.
    
    Expected POST data:
    {
        "product_id": 1,
        "quantity": 1,
        "update_quantity": false
    }
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        update_quantity = bool(data.get('update_quantity', False))
        
        if not product_id:
            return JsonResponse(
                {'success': False, 'message': 'Product ID is required'}, 
                status=400
            )
        
        success, message, cart_item = add_to_cart(
            request, 
            product_id, 
            quantity, 
            update_quantity
        )
        
        if success:
            cart_data = get_cart_items(request)
            return JsonResponse({
                'success': True,
                'message': message,
                'cart': cart_data
            })
        else:
            return JsonResponse(
                {'success': False, 'message': message}, 
                status=400
            )
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON data'}, 
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)}, 
            status=500
        )


@csrf_exempt
@require_http_methods(["POST"])
def api_remove_from_cart(request, product_id=None):
    """
    API endpoint to remove a product from the cart.
    
    Can be called with product_id in URL or in POST data.
    """
    try:
        # Try to get product_id from POST data if not in URL
        if not product_id:
            data = json.loads(request.body)
            product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse(
                {'success': False, 'message': 'Product ID is required'}, 
                status=400
            )
        
        success, message = remove_from_cart(request, product_id)
        
        if success:
            cart_data = get_cart_items(request)
            return JsonResponse({
                'success': True,
                'message': message,
                'cart': cart_data
            })
        else:
            return JsonResponse(
                {'success': False, 'message': message}, 
                status=404
            )
            
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'message': 'Invalid JSON data'}, 
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)}, 
            status=500
        )


@require_http_methods(["GET"])
def api_get_cart(request):
    """
    API endpoint to get the current cart contents.
    """
    try:
        cart_data = get_cart_items(request)
        return JsonResponse({'success': True, 'cart': cart_data})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
