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

from ..models import Cart, CartItem, Product, Coupon
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
        return JsonResponse({
            'success': True,
            'cart': cart_data
        })
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)}, 
            status=500
        )


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_apply_coupon(request):
    """
    API endpoint to apply a coupon to the cart.
    
    Expected POST data:
    {
        "code": "DISCOUNT10"
    }
    """
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        
        if not code:
            return JsonResponse(
                {'success': False, 'message': 'Coupon code is required'}, 
                status=400
            )
        
        # Get the user's active cart
        cart = get_object_or_404(
            Cart.objects.select_related('coupon'), 
            user=request.user, 
            status='active'
        )
        
        # Check if coupon is valid
        try:
            coupon = Coupon.objects.get(
                code=code,
                is_active=True,
            )
            
            # Check if coupon is still valid
            if not coupon.is_valid():
                return JsonResponse(
                    {'success': False, 'message': 'This coupon has expired'}, 
                    status=400
                )
            
            # Check usage limits
            if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
                return JsonResponse(
                    {'success': False, 'message': 'This coupon has reached its usage limit'}, 
                    status=400
                )
            
            # Apply coupon to cart
            cart.coupon = coupon
            cart.save()
            
            # Get updated cart data
            cart_data = get_cart_items(request)
            
            return JsonResponse({
                'success': True,
                'message': 'Coupon applied successfully',
                'cart': cart_data,
                'discount': {
                    'code': coupon.code,
                    'discount_amount': str(coupon.discount_amount),
                    'discount_type': coupon.discount_type,
                    'description': coupon.description
                }
            })
            
        except Coupon.DoesNotExist:
            return JsonResponse(
                {'success': False, 'message': 'Invalid coupon code'}, 
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


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_remove_coupon(request):
    """
    API endpoint to remove a coupon from the cart.
    """
    try:
        # Get the user's active cart
        cart = get_object_or_404(
            Cart.objects.select_related('coupon'), 
            user=request.user, 
            status='active'
        )
        
        if not cart.coupon:
            return JsonResponse(
                {'success': False, 'message': 'No coupon applied to this cart'}, 
                status=400
            )
        
        # Remove coupon from cart
        coupon_code = cart.coupon.code
        cart.coupon = None
        cart.save()
        
        # Get updated cart data
        cart_data = get_cart_items(request)
        
        return JsonResponse({
            'success': True,
            'message': f'Coupon {coupon_code} removed successfully',
            'cart': cart_data
        })
        
    except Exception as e:
        return JsonResponse(
            {'success': False, 'message': str(e)}, 
            status=500
        )
