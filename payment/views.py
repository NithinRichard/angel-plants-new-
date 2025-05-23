import json
import logging
import uuid
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404, reverse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.cache import never_cache
from store.models import Order, Payment, OrderItem
from .utils import create_razorpay_order, verify_payment_signature, get_payment_details, capture_payment
import time
import razorpay

logger = logging.getLogger(__name__)

def generate_unique_receipt():
    """Generate a unique receipt ID for Razorpay"""
    return f"order_rcpt_{uuid.uuid4().hex[:16]}"

@login_required
@require_http_methods(["POST"])
def create_order(request):
    """
    Create a Razorpay order for the current user's cart
    """
    logger.info("=== Starting create_order view ===")
    logger.info(f"User: {request.user.id}, Email: {request.user.email}")
    
    # Log request details
    logger.debug(f"Request method: {request.method}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"Request body: {request.body}")
    
    # Check if it's an AJAX request
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    logger.debug(f"Is AJAX request: {is_ajax}")
    
    if not is_ajax:
        logger.warning("Non-AJAX request received")
        return JsonResponse({
            'status': 'error',
            'code': 'invalid_request',
            'message': 'Invalid request. This endpoint only accepts AJAX requests.'
        }, status=400)
    
    try:
        with transaction.atomic():
            # Get the user's latest unpaid order
            logger.debug(f"Fetching active order for user {request.user.id}")
            
            try:
                order = Order.objects.select_for_update().select_related('user').prefetch_related('items').filter(
                    user=request.user, 
                    payment_status=False
                ).order_by('-created_at').first()
                
                logger.debug(f"Order query executed. Found order: {order is not None}")
                
                if not order:
                    logger.warning(f"No active order found for user {request.user.id}")
                    return JsonResponse({
                        'status': 'error',
                        'code': 'no_order',
                        'message': 'No active order found. Your cart might be empty.'
                    }, status=400)
                    
                logger.debug(f"Order details - ID: {order.id}, Total: {getattr(order, 'total_amount', 'N/A')}, "
                            f"Items: {order.items.count() if hasattr(order, 'items') else 'N/A'}")
                
            except Exception as query_error:
                logger.error(f"Error fetching order: {str(query_error)}", exc_info=True)
                return JsonResponse({
                    'status': 'error',
                    'code': 'order_fetch_error',
                    'message': 'Error fetching your order. Please try again.'
                }, status=500)
                
            logger.debug(f"Found order {order.id} with {order.items.count()} items")
            
            if order.items.count() == 0:
                logger.warning(f"Order {order.id} has no items")
                return JsonResponse({
                    'status': 'error',
                    'code': 'empty_cart',
                    'message': 'Your cart is empty. Please add items before proceeding to checkout.'
                }, status=400)
            
            # Log order details for debugging
            logger.debug(f"Order details - ID: {order.id}, Total: {order.total_amount}, Items: {order.items.count()}")
            
            # Validate order amount
            if not hasattr(order, 'total_amount') or order.total_amount is None:
                logger.error(f"Order {order.id} has no total_amount")
                return JsonResponse({
                    'status': 'error',
                    'code': 'invalid_order',
                    'message': 'Order total could not be calculated. Please try again.'
                }, status=400)
                
            if order.total_amount <= 0:
                logger.error(f"Invalid order amount {order.total_amount} for order {order.id}")
                return JsonResponse({
                    'status': 'error',
                    'code': 'invalid_amount',
                    'message': 'Invalid order amount. Please check your cart and try again.'
                }, status=400)
            
            # Convert amount to paise (Razorpay's requirement) and round to nearest integer
            try:
                amount = int(round(float(order.total_amount) * 100))
                logger.debug(f"Converted amount: {order.total_amount} to {amount} paise")
            except (TypeError, ValueError) as e:
                logger.error(f"Error converting amount {order.total_amount} to paise: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'code': 'amount_conversion_error',
                    'message': 'Error processing order amount. Please try again.'
                }, status=500)
            
            # Create Razorpay order with detailed logging
            try:
                logger.debug(f"Creating Razorpay order for amount: {amount}")
                logger.debug(f"Order details - ID: {order.id}, Total: {amount}, Items: {order.items.count()}")
                
                # Prepare order data
                order_data = {
                    'amount': amount,
                    'currency': 'INR',
                    'receipt': f"order_{order.id}",
                    'notes': {
                        'order_id': str(order.id),
                        'user_id': str(request.user.id),
                        'description': f"Order #{order.order_number}"
                    }
                }
                
                logger.debug(f"Sending order data to Razorpay: {order_data}")
                
                # Create the Razorpay order with auto-capture
                razorpay_order = create_razorpay_order(
                    amount=order_data['amount'],
                    currency=order_data['currency'],
                    receipt=order_data['receipt'],
                    notes=order_data['notes']
                )
                
                # Enable auto-capture for the order
                try:
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    payment_id = razorpay_order.get('id')
                    if payment_id:
                        client.payment.capture(payment_id, amount)
                        logger.info(f"Enabled auto-capture for payment {payment_id}")
                except Exception as capture_error:
                    logger.warning(f"Could not enable auto-capture: {str(capture_error)}")
                
                if not razorpay_order or 'id' not in razorpay_order:
                    error_msg = f"Invalid response from Razorpay: {razorpay_order}"
                    logger.error(error_msg)
                    return JsonResponse({
                        'status': 'error',
                        'code': 'razorpay_error',
                        'message': 'Invalid response from payment processor. Please try again.'
                    }, status=500)
                    
                logger.info(f"Successfully created Razorpay order: {razorpay_order['id']}")
                
                # Update order with Razorpay order ID
                order.razorpay_order_id = razorpay_order['id']
                order.save(update_fields=['razorpay_order_id', 'updated_at'])
                
                # Get user details for prefill
                user_name = request.user.get_full_name() or request.user.username
                user_email = request.user.email
                user_phone = getattr(order.shipping_address, 'phone', '') if hasattr(order, 'shipping_address') else ''
                
                # Prepare response data
                response_data = {
                    'status': 'success',
                    'order_id': razorpay_order['id'],
                    'amount': amount,
                    'currency': 'INR',
                    'key': settings.RAZORPAY_KEY_ID,
                    'name': 'Your Store Name',
                    'description': f'Order #{order.order_number}',
                    'prefill': {
                        'name': user_name,
                        'email': user_email,
                        'contact': user_phone
                    },
                    'theme': {
                        'color': '#F37254'
                    },
                    'order_number': order.order_number
                }
                
                logger.debug(f"Sending response data: {response_data}")
                
                return JsonResponse(response_data)
                
            except Exception as e:
                error_msg = f"Error creating Razorpay order: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # Check for specific Razorpay errors
                if hasattr(e, 'error') and isinstance(e.error, dict):
                    error_code = e.error.get('code', 'unknown_error')
                    error_description = e.error.get('description', 'Unknown error occurred')
                    logger.error(f"Razorpay error - Code: {error_code}, Description: {error_description}")
                    
                    # Provide more specific error messages for common issues
                    if 'invalid' in str(error_code).lower() or 'invalid' in str(error_description).lower():
                        error_message = "Invalid payment details. Please check your information and try again."
                    elif 'insufficient' in str(error_description).lower():
                        error_message = "Insufficient balance. Please use a different payment method."
                    else:
                        error_message = f"Payment error: {error_description}"
                else:
                    error_message = "An unexpected error occurred while processing your payment. Please try again."
                
                return JsonResponse({
                    'status': 'error',
                    'code': 'payment_error',
                    'message': error_message
                }, status=500)
            
    except Exception as e:
        logger.critical(f"Unexpected error in create_order: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'code': 'server_error',
            'message': 'An unexpected error occurred. Our team has been notified. Please try again later.'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook(request):
    """
    Handle Razorpay webhook events for payment processing
    """
    try:
        # Get the webhook payload
        payload = json.loads(request.body.decode('utf-8'))
        logger.info(f"Received webhook payload: {json.dumps(payload, indent=2)}")
        
        # Verify the webhook signature
        webhook_signature = request.headers.get('X-Razorpay-Signature')
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        
        if not webhook_secret:
            logger.error("RAZORPAY_WEBHOOK_SECRET is not configured")
            return HttpResponseServerError("Server configuration error")
            
        if not verify_payment_signature(payload, webhook_signature, webhook_secret):
            logger.warning(f"Invalid webhook signature. Received: {webhook_signature}")
            return HttpResponseBadRequest("Invalid signature")
        
        # Handle different webhook events
        event = payload.get('event')
        
        if event == 'payment.captured':
            return handle_payment_captured(payload)
        elif event == 'payment.failed':
            return handle_payment_failed(payload)
        elif event == 'order.paid':
            return handle_order_paid(payload)
        else:
            logger.info(f"Unhandled webhook event: {event}")
            return JsonResponse({'status': 'ignored', 'event': event}, status=200)
            
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload in webhook: {str(e)}")
        return HttpResponseBadRequest("Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error in payment webhook: {str(e)}", exc_info=True)
        return HttpResponseServerError("Internal server error")

def handle_payment_captured(payload):
    """Handle payment.captured webhook event"""
    try:
        payment_data = payload.get('payload', {}).get('payment', {})
        payment_id = payment_data.get('entity', {}).get('id')
        order_id = payment_data.get('entity', {}).get('order_id')
        
        if not payment_id or not order_id:
            logger.error(f"Missing payment_id or order_id in webhook payload: {payload}")
            return HttpResponseBadRequest("Missing required fields")
        
        logger.info(f"Processing payment.captured for payment_id: {payment_id}, order_id: {order_id}")
        
        with transaction.atomic():
            # Get the order with select_for_update to prevent race conditions
            try:
                order = Order.objects.select_for_update().get(
                    razorpay_order_id=order_id,
                    payment_status=False  # Only process if not already paid
                )
            except Order.DoesNotExist:
                logger.warning(f"Order not found or already paid: {order_id}")
                return JsonResponse({'status': 'ignored', 'reason': 'order_not_found_or_paid'}, status=200)
            
            # Verify payment with Razorpay
            try:
                payment = get_payment_details(payment_id)
                if payment.get('status') != 'captured':
                    logger.warning(f"Payment {payment_id} status is not captured: {payment.get('status')}")
                    return JsonResponse({'status': 'ignored', 'reason': 'payment_not_captured'}, status=200)
            except Exception as e:
                logger.error(f"Error verifying payment {payment_id}: {str(e)}")
                return HttpResponseServerError("Error verifying payment")
            
            # Update order status
            order.payment_status = True
            order.status = 'processing'
            order.payment_date = timezone.now()
            order.save(update_fields=['payment_status', 'status', 'payment_date', 'updated_at'])
            
            # Create or update payment record
            payment_amount = payment_data.get('entity', {}).get('amount', 0) / 100  # Convert from paise to rupees
            Payment.objects.update_or_create(
                transaction_id=payment_id,
                defaults={
                    'order': order,
                    'amount': payment_amount,
                    'payment_method': 'razorpay',
                    'status': 'completed',
                    'raw_data': json.dumps(payment_data),
                    'created_at': timezone.now()
                }
            )
            
            logger.info(f"Successfully processed payment {payment_id} for order {order.id}")
            
            # TODO: Send order confirmation email
            # send_order_confirmation_email(order)
            
            return JsonResponse({'status': 'success'})
            
    except Exception as e:
        logger.error(f"Error in handle_payment_captured: {str(e)}", exc_info=True)
        return HttpResponseServerError("Internal server error")

def handle_payment_failed(payload):
    """Handle payment.failed webhook event"""
    try:
        payment_data = payload.get('payload', {}).get('payment', {}).get('entity', {})
        payment_id = payment_data.get('id')
        order_id = payment_data.get('order_id')
        error_code = payment_data.get('error_code')
        error_description = payment_data.get('error_description')
        
        logger.warning(f"Payment failed - ID: {payment_id}, Order: {order_id}, "
                     f"Error: {error_code} - {error_description}")
        
        if order_id:
            try:
                order = Order.objects.get(razorpay_order_id=order_id)
                order.status = 'payment_failed'
                order.save(update_fields=['status', 'updated_at'])
                
                # Log the failed payment attempt
                Payment.objects.create(
                    order=order,
                    transaction_id=payment_id,
                    amount=payment_data.get('amount', 0) / 100,
                    payment_method='razorpay',
                    status='failed',
                    error_code=error_code,
                    error_description=error_description,
                    raw_data=json.dumps(payment_data)
                )
                
                # TODO: Send payment failure notification to admin
                
            except Order.DoesNotExist:
                logger.warning(f"Order not found for failed payment: {order_id}")
        
        return JsonResponse({'status': 'processed'})
        
    except Exception as e:
        logger.error(f"Error in handle_payment_failed: {str(e)}", exc_info=True)
        return HttpResponseServerError("Internal server error")

def handle_order_paid(payload):
    """Handle order.paid webhook event"""
    try:
        order_data = payload.get('payload', {}).get('order', {}).get('entity', {})
        order_id = order_data.get('id')
        payment_id = order_data.get('payment_id')
        
        if not order_id or not payment_id:
            logger.error(f"Missing order_id or payment_id in order.paid webhook: {payload}")
            return HttpResponseBadRequest("Missing required fields")
            
        logger.info(f"Processing order.paid for order_id: {order_id}, payment_id: {payment_id}")
        
        # In most cases, payment.captured will handle this, but we'll log it
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(
                    razorpay_order_id=order_id,
                    payment_status=False
                )
                logger.info(f"Order {order.id} marked as paid via order.paid webhook")
                
                # If for some reason payment wasn't captured yet, capture it
                if not order.payment_status:
                    payment = get_payment_details(payment_id)
                    if payment.get('status') == 'captured':
                        order.payment_status = True
                        order.status = 'processing'
                        order.payment_date = timezone.now()
                        order.save(update_fields=['payment_status', 'status', 'payment_date', 'updated_at'])
                        
                        Payment.objects.update_or_create(
                            transaction_id=payment_id,
                            defaults={
                                'order': order,
                                'amount': payment.get('amount', 0) / 100,
                                'payment_method': 'razorpay',
                                'status': 'completed',
                                'raw_data': json.dumps(payment)
                            }
                        )
        except Order.DoesNotExist:
            logger.warning(f"Order {order_id} not found or already paid")
        
        return JsonResponse({'status': 'processed'})
        
    except Exception as e:
        logger.error(f"Error in handle_order_paid: {str(e)}", exc_info=True)
        return HttpResponseServerError("Internal server error")

@login_required
@require_GET
def payment_success(request):
    """
    Handle successful payment return from Razorpay
    """
    payment_id = request.GET.get('payment_id')
    order_id = request.GET.get('order_id')
    signature = request.GET.get('signature')
    
    if not all([payment_id, order_id, signature]):
        messages.error(request, "Invalid payment details. Please contact support if the amount was deducted.")
        return redirect('store:checkout')
    
    try:
        # Get the order with related data
        order = Order.objects.select_related('shipping_address').prefetch_related('items').get(
            razorpay_order_id=order_id,
            user=request.user
        )
        
        # If payment is already processed, redirect to success page
        if order.payment_status:
            return redirect('store:checkout_success', order_id=order.id)
        
        # Verify the payment with Razorpay
        try:
            payment = get_payment_details(payment_id)
            
            # Verify the payment signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            params = {
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': order_id,
                'razorpay_signature': signature
            }
            
            try:
                client.utility.verify_payment_signature(params)
                signature_valid = True
            except Exception as e:
                logger.warning(f"Invalid payment signature: {str(e)}")
                signature_valid = False
            
            if payment.get('status') == 'captured' and payment.get('order_id') == order_id and signature_valid:
                # Update order status
                with transaction.atomic():
                    order.payment_status = True
                    order.status = 'processing'
                    order.payment_date = timezone.now()
                    order.save(update_fields=['payment_status', 'status', 'payment_date', 'updated_at'])
                    
                    # Create payment record
                    Payment.objects.update_or_create(
                        transaction_id=payment_id,
                        defaults={
                            'order': order,
                            'amount': payment.get('amount', 0) / 100,  # Convert from paise to rupees
                            'payment_method': 'razorpay',
                            'status': 'completed',
                            'raw_data': json.dumps(payment),
                            'created_at': timezone.now()
                        }
                    )
                
                # Clear cart
                # Note: In a real app, you might want to keep the items for order history
                # and have a separate cart model
                
                # Redirect to success page
                messages.success(request, "Your payment was successful!")
                return redirect('store:checkout_success', order_id=order.id)
            else:
                # If payment is not captured, try to capture it
                if payment.get('status') == 'authorized':
                    try:
                        captured = capture_payment(payment_id, payment.get('amount'))
                        if captured and captured.get('status') == 'captured' and signature_valid:
                            with transaction.atomic():
                                order.payment_status = True
                                order.status = 'processing'
                                order.payment_date = timezone.now()
                                order.save(update_fields=['payment_status', 'status', 'payment_date', 'updated_at'])
                                
                                Payment.objects.update_or_create(
                                    transaction_id=payment_id,
                                    defaults={
                                        'order': order,
                                        'amount': captured.get('amount', 0) / 100,
                                        'payment_method': 'razorpay',
                                        'status': 'completed',
                                        'raw_data': json.dumps(captured),
                                        'created_at': timezone.now()
                                    }
                                )
                            
                            messages.success(request, "Your payment was successfully captured!")
                            return redirect('store:checkout_success', order_id=order.id)
                    except Exception as capture_error:
                        logger.error(f"Error capturing payment {payment_id}: {str(capture_error)}", exc_info=True)
                
                # If we get here, payment verification failed
                logger.warning(f"Payment verification failed - Payment: {payment}, Signature valid: {signature_valid}")
                messages.warning(
                    request,
                    "We're still processing your payment. "
                    "You'll receive a confirmation email once it's complete."
                )
                return redirect('store:order_detail', order_number=order.order_number)
                
        except Exception as e:
            logger.error(f"Error verifying payment {payment_id}: {str(e)}", exc_info=True)
            messages.warning(
                request,
                "We're verifying your payment. You'll receive a confirmation email shortly."
            )
            return redirect('store:order_detail', order_number=order.order_number)
        
    except Order.DoesNotExist:
        logger.error(f"Order not found for payment success - Order ID: {order_id}, User: {request.user.id}")
        messages.error(request, "Order not found. Please contact support if you need assistance.")
        return redirect('store:checkout')
    except Exception as e:
        logger.error(f"Error processing payment success - Order ID: {order_id}, Error: {str(e)}", exc_info=True)
        messages.error(
            request,
            "An error occurred while processing your payment. "
            "Please contact support if the amount was deducted."
        )
        return redirect('store:checkout')

@login_required
@require_GET
def payment_failed(request):
    """
    Handle failed payment return from Razorpay
    """
    # Log the start of the function
    logger.info("payment_failed view called with GET params: %s", dict(request.GET))
    
    error_code = request.GET.get('error[code]')
    error_description = request.GET.get('error[description]')
    payment_id = request.GET.get('payment_id')
    order_id = request.GET.get('order_id')
    
    logger.info("Extracted params - error_code: %s, payment_id: %s, order_id: %s", 
                error_code, payment_id, order_id)
    
    # Log the failure
    logger.warning(
        f"Payment failed - Code: {error_code}, "
        f"Description: {error_description}, "
        f"Payment ID: {payment_id}, "
        f"Order ID: {order_id}"
    )
    
    # Try to get the order for context
    order = None
    if order_id:
        try:
            order = Order.objects.filter(
                razorpay_order_id=order_id,
                user=request.user
            ).first()
            
            # Update order status if it exists and payment failed
            if order and not order.payment_status:
                order.status = 'payment_failed'
                order.save(update_fields=['status', 'updated_at'])
                
                # Log the failed payment attempt
                if payment_id:
                    logger.info("Creating payment record for order_id: %s, payment_id: %s", order_id, payment_id)
                    try:
                        # Create payment record with all required fields
                        error_source = request.GET.get('error[source]', 'unknown')
                        error_step = request.GET.get('error[step]', 'unknown')
                        error_reason = request.GET.get('error[reason]', 'unknown')
                        payment_data = {
                            'order': order,
                            'payment_id': payment_id if payment_id else f'failed_{order.order_number}_{int(time.time())}',
                            'payment_method': order.payment_method or 'razorpay',
                            'amount': order.total_amount or 0,
                            'status': 'failed',
                            'transaction_id': payment_id or f'txn_{order.order_number}_{int(time.time())}',
                            'error_code': error_code,
                            'error_description': error_description,
                            'error_source': error_source,
                            'error_step': error_step,
                            'error_reason': error_reason,
                            'raw_data': json.dumps({
                                'error': error_description,
                                'error_code': error_code,
                                'error_source': error_source,
                                'error_step': error_step,
                                'error_reason': error_reason,
                                'payment_id': payment_id,
                                'order_id': order_id,
                                'timestamp': timezone.now().isoformat()
                            })
                        }
                        # Create the payment record
                        payment = Payment.objects.create(**payment_data)
                        logger.info("Successfully created payment record with ID: %s", payment.id)
                    except Exception as e:
                        logger.error("Error creating payment record: %s", str(e), exc_info=True)
                        raise
        except Exception as e:
            logger.error(f"Error updating order status for failed payment: {str(e)}", exc_info=True)
    
    # Prepare error message based on error code
    user_message = "Your payment was not successful. "
    
    if error_code == 'PAYMENT_CANCELLED':
        user_message += "You cancelled the payment."
    elif error_code == 'BAD_REQUEST_ERROR':
        user_message += "There was an issue with the payment request. "
        user_message += "Please check your payment details and try again."
    elif error_code == 'AUTHENTICATION_FAILED':
        user_message += "Payment authentication failed. Please try again or use a different payment method."
    elif error_code == 'INSUFFICIENT_BALANCE':
        user_message += "Insufficient balance in your account. Please use a different payment method."
    else:
        user_message += "Please try again or contact support if the issue persists."
    
    messages.error(request, user_message)
    
    # If we have an order, redirect to order detail page, otherwise to checkout
    if order:
        return redirect('store:order_detail', order_number=order.order_number)
    return redirect('store:checkout')
