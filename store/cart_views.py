from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse
from decimal import Decimal
from .models import Product, Cart, CartItem

@login_required
def add_to_cart(request, product_id):
    """
    Add a product to the cart or update quantity if already in cart.
    """
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Get quantity from POST data, default to 1 if not provided
        quantity = int(request.POST.get('quantity', 1))
        
        # Ensure quantity is at least 1
        quantity = max(1, quantity)
        
        # Get or create cart for the current user
        try:
            # First try to get an existing cart
            cart = Cart.objects.get(user=request.user, status='active')
        except Cart.DoesNotExist:
            # If no cart exists, create a new one
            try:
                cart = Cart.objects.create(user=request.user, status='active')
            except Exception as e:
                # If there's still an error (e.g., race condition), try to get the cart again
                cart = Cart.objects.get(user=request.user, status='active')
        
        # Get or create cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 0, 'price': product.price}
        )
        
        # Update quantity by the specified amount
        cart_item.increase_quantity(quantity)
        
        # Prepare response data
        response_data = {
            'status': 'success',
            'message': f"{product.name} added to cart",
            'item_count': cart.item_count,
            'total_quantity': cart.total_quantity,
            'cart_total': float(cart.total),
            'shipping_cost': 99.00,  # Fixed shipping cost for India
            'tax': 0.00,  # Will be calculated in the frontend
            'total_with_shipping': float(cart.total) + 99.00,  # Total with shipping
            'cart_item': {
                'id': cart_item.id,
                'product_id': product.id,
                'name': product.name,
                'quantity': cart_item.quantity,
                'price': float(product.price),
                'total_price': float(cart_item.quantity * product.price)
            }
        }
        
        # Set success message
        messages.success(request, f"{product.name} has been added to your cart.")
        
        # If it's an AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)
            
        # For regular form submission, redirect to cart or previous page
        redirect_url = request.META.get('HTTP_REFERER', reverse('store:cart'))
        return redirect(redirect_url)
        
    except Product.DoesNotExist:
        error_msg = 'Product not found.'
    except Exception as e:
        error_msg = f'An error occurred: {str(e)}'
        print(f"Error in add_to_cart: {error_msg}")
        import traceback
        traceback.print_exc()
    
    # Handle errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
    
    messages.error(request, error_msg)
    return redirect('store:home')

@login_required
def update_cart(request):
    """
    Update cart item quantities.
    Expected POST data: {'product_id': quantity, 'update_quantity': '1'}
    """
    if request.method == 'POST':
        try:
            # Get the user's cart
            cart = Cart.objects.get(user=request.user, status='active')
            product_id = request.POST.get('product_id')
            quantity = request.POST.get('quantity')
            
            if not (product_id and product_id.isdigit() and quantity):
                raise ValueError('Invalid product ID or quantity.')
                
            cart_item = CartItem.objects.get(
                cart=cart,
                product_id=product_id
            )
            
            # Update quantity
            cart_item.quantity = max(1, int(quantity))  # Ensure quantity is at least 1
            cart_item.save()
            
            # Refresh the cart to get updated totals
            cart.refresh_from_db()
            
            # Calculate totals
            cart_total = float(cart.total)
            shipping_cost = 99.00  # Fixed shipping cost for India
            tax = cart_total * 0.18  # 18% GST
            total_with_shipping = cart_total + tax + shipping_cost
            
            # Prepare success response with all required data
            response_data = {
                'status': 'success',
                'message': 'Cart updated',
                'item_count': cart.item_count,
                'total_quantity': cart.total_quantity,
                'cart_total': cart_total,
                'shipping_cost': shipping_cost,
                'tax': tax,
                'total_with_shipping': total_with_shipping,
                'updated_item': {
                    'id': cart_item.id,
                    'product_id': cart_item.product.id,
                    'name': cart_item.product.name,
                    'quantity': cart_item.quantity,
                    'price': float(cart_item.price),
                    'total_price': float(cart_item.total_price)
                }
            }
            
            messages.success(request, 'Your cart has been updated.')
            
            # If it's not an AJAX request, redirect to cart
            if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                return redirect('store:cart')
                
            return JsonResponse(response_data)
            
        except Cart.DoesNotExist:
            error_msg = 'No active cart found.'
            status_code = 404
        except CartItem.DoesNotExist:
            error_msg = 'Item not found in cart.'
            status_code = 404
        except ValueError as e:
            error_msg = str(e) or 'Invalid input.'
            status_code = 400
        except Exception as e:
            error_msg = f'An error occurred: {str(e)}'
            status_code = 500
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data)
                
            messages.success(request, 'Your cart has been updated.')
            return redirect('store:cart')
            
        except Cart.DoesNotExist:
            error_msg = 'No active cart found.'
        except Exception as e:
            error_msg = f'An error occurred: {str(e)}'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
            
        messages.error(request, error_msg)
        return redirect('store:cart')
    
    return redirect('store:cart')

@login_required
def remove_from_cart(request, product_id):
    """
    Remove a product from the cart or decrease its quantity.
    """
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Get the user's cart
        cart = get_object_or_404(Cart, user=request.user, status='active')
        
        # Get the cart item
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            
            # Remove the item from the cart
            cart_item.delete()
            
            # Prepare success response with all required data
            response_data = {
                'status': 'success',
                'message': f"{product.name} removed from cart",
                'item_count': cart.item_count,
                'total_quantity': cart.total_quantity,
                'cart_total': float(cart.total),
                'shipping_cost': 99.00 if cart.item_count > 0 else 0.00,  # Free shipping if cart is empty
                'tax': float(cart.total) * 0.18,  # 18% GST
                'total_with_shipping': (float(cart.total) * 1.18 + (99.00 if cart.item_count > 0 else 0.00)) if cart.item_count > 0 else 0.00,
                'removed_item': {
                    'id': product.id,
                    'product_id': product.id,
                    'name': product.name,
                    'quantity': 0,
                    'price': float(product.price),
                    'total_price': 0.00
                }
            }
            
            # Set success message
            messages.success(request, f"{product.name} has been removed from your cart.")
            
        except CartItem.DoesNotExist:
            # Item not in cart
            response_data = {
                'status': 'error',
                'message': 'Item not found in cart',
            }
            messages.error(request, 'Item not found in your cart.')
        
        # If it's an AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)
            
        # For regular form submission, redirect to cart or previous page
        redirect_url = request.META.get('HTTP_REFERER', reverse('store:cart'))
        return redirect(redirect_url)
        
    except Product.DoesNotExist:
        error_msg = 'Product not found.'
    except Cart.DoesNotExist:
        error_msg = 'No active cart found.'
    except Exception as e:
        error_msg = f'An error occurred: {str(e)}'
    
    # Handle errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
    
    messages.error(request, error_msg)
    return redirect('store:cart')
