import json
from decimal import Decimal
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import Http404

from .models import Order, Payment, OrderItem, Cart, CartItem
from .payment_utils import create_razorpay_order, verify_payment_signature

# Initialize Razorpay client
import razorpay
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class PaymentView(LoginRequiredMixin, View):
    """View to handle payment page and form submission"""
    template_name = 'store/payment/payment_form.html'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user, status__in=['pending', 'processing'])
    
    def get_object(self):
        order_id = self.kwargs.get('order_id')
        if not order_id:
            raise Http404("Order ID is required")
        try:
            return get_object_or_404(self.get_queryset(), id=order_id)
        except (ValueError, TypeError):
            raise Http404("Invalid order ID format")
    
    def get(self, request, *args, **kwargs):
        try:
            order = self.get_object()
            context = {
                'order': order,
                'razorpay_key': settings.RAZORPAY_KEY_ID
            }
            return render(request, self.template_name, context)
        except Http404 as e:
            messages.error(request, str(e))
            return redirect('store:checkout')
        except Exception as e:
            logger.error(f"Error in payment view GET: {str(e)}", exc_info=True)
            messages.error(request, "An error occurred while loading the payment page.")
            return redirect('store:checkout')
    
    def post(self, request, *args, **kwargs):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            order = self.get_object()
            payment_method = request.POST.get('payment_method', 'razorpay')
            
            if not payment_method in ['razorpay', 'cash_on_delivery']:
                raise ValueError("Invalid payment method")
            
            # Update order with payment method
            order.payment_method = payment_method
            order.save(update_fields=['payment_method', 'updated_at'])
            
            if payment_method == 'cash_on_delivery':
                # Process cash on delivery
                order.status = 'processing'
                order.payment_status = 'pending'
                order.save(update_fields=['status', 'payment_status', 'updated_at'])
                
                # Clear the cart
                cart = Cart.objects.filter(user=request.user, status='active').first()
                if cart:
                    cart.status = 'completed'
                    cart.save()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('store:checkout_success', kwargs={'order_number': order.order_number})
                    })
                return redirect('store:checkout_success', order_number=order.order_number)
            
            elif payment_method == 'razorpay':
                # Process Razorpay payment
                amount = int(order.total_amount * 100)  # Convert to paise
                razorpay_order = create_razorpay_order(amount, order.id)
                
                if not razorpay_order:
                    raise Exception('Failed to create Razorpay order')
                
                # Save Razorpay order ID
                order.razorpay_order_id = razorpay_order['id']
                order.save(update_fields=['razorpay_order_id', 'updated_at'])
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'razorpay': {
                            'key_id': settings.RAZORPAY_KEY_ID,
                            'amount': amount,
                            'currency': 'INR',
                            'name': 'Angel\'s Plants',
                            'description': f'Order #{order.order_number}',
                            'order_id': razorpay_order['id']
                        },
                        'order_id': order.id
                    })
                
                # Non-AJAX fallback
                context = {
                    'order': order,
                    'razorpay_key': settings.RAZORPAY_KEY_ID,
                    'razorpay_order_id': razorpay_order['id'],
                    'amount': amount,
                    'currency': 'INR',
                    'name': request.user.get_full_name() or request.user.username,
                    'email': request.user.email,
                    'contact': getattr(request.user.profile, 'phone', '')
                }
                return render(request, self.template_name, context)
                
        except Http404 as e:
            error_message = str(e)
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=404)
            messages.error(request, error_message)
            return redirect('store:checkout')
        except ValueError as e:
            error_message = str(e)
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=400)
            messages.error(request, error_message)
            return redirect('store:checkout')
        except Exception as e:
            logger.error(f"Payment processing failed: {str(e)}", exc_info=True)
            error_message = "An error occurred while processing your payment. Please try again."
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': error_message
                }, status=500)
            messages.error(request, error_message)
            return redirect('store:checkout')


class CreateRazorpayOrderView(LoginRequiredMixin, View):
    """Create a Razorpay order"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Get the order from the database
            order_id = request.POST.get('order_id')
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            # Create a Razorpay order
            razorpay_order = create_razorpay_order(
                amount=order.total_amount,
                receipt=f'order_{order.id}'
            )
            
            if not razorpay_order:
                return JsonResponse({'error': 'Failed to create order'}, status=500)
            
            # Save the Razorpay order ID to your order
            order.razorpay_order_id = razorpay_order['id']
            order.save()
            
            return JsonResponse({
                'id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'key': settings.RAZORPAY_KEY_ID,
                'order_id': order.id
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
def payment_webhook(request):
    """Handle Razorpay webhook"""
    if request.method != 'POST':
        return HttpResponseBadRequest("Invalid request method")
    
    try:
        # Get webhook payload
        payload = request.body.decode('utf-8')
        received_signature = request.headers.get('X-Razorpay-Signature', '')
        
        # Verify the webhook signature
        try:
            razorpay_client.utility.verify_webhook_signature(
                payload,
                received_signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return HttpResponseBadRequest("Invalid signature")
        
        # Parse the payload
        try:
            payload_data = json.loads(payload)
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")
        
        # Handle different webhook events
        event = payload_data.get('event')
        
        if event == 'payment.captured':
            # Handle successful payment
            payment_data = payload_data.get('payload', {}).get('payment', {}) if 'payload' in payload_data else {}
            payment_id = payment_data.get('id')
            order_id = payment_data.get('notes', {}).get('order_id')
            
            if not order_id:
                logger.error(f"No order_id found in payment data: {payment_data}")
                return HttpResponseBadRequest("No order_id in payment data")
            
            try:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=order_id)
                    if order.payment_status != 'completed':  # Prevent duplicate processing
                        order.status = 'processing'  # or 'completed' based on your workflow
                        order.payment_status = True
                        order.payment_id = payment_id
                        order.save()
                        
                        # Create payment record
                        Payment.objects.create(
                            order=order,
                            payment_id=payment_data.get('id'),
                            amount=Decimal(payment_data.get('amount', 0)) / 100,  # Convert back to rupees
                            payment_method=payment_data.get('method', 'card'),
                            status=payment_data.get('status', 'captured'),
                            raw_data=json.dumps(payment_data)
                        )
            except Order.DoesNotExist:
                logger.error(f"Order not found: {order_id}")
                return HttpResponseBadRequest("Order not found")
            except Exception as e:
                logger.error(f"Error processing payment: {str(e)}")
                return HttpResponseBadRequest(f"Error processing payment: {str(e)}")
            
            return JsonResponse({'status': 'success'})
        
        return JsonResponse({'status': 'ignored', 'event': event})
        
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        return HttpResponseBadRequest("Error processing webhook")


class PaymentSuccessView(LoginRequiredMixin, View):
    """Handle successful payment"""
    
    def get(self, request, *args, **kwargs):
        order_id = request.GET.get('order_id')
        payment_id = request.GET.get('payment_id')
        signature = request.GET.get('signature')
        
        if not all([order_id, payment_id, signature]):
            messages.error(request, "Missing required payment parameters.")
            return redirect('store:checkout')
        
        try:
            # Get the order with select_for_update to prevent race conditions
            with transaction.atomic():
                order = Order.objects.select_for_update().get(
                    razorpay_order_id=order_id, 
                    user=request.user,
                    status__in=['pending', 'processing']
                )
                
                # Verify the payment signature
                if not verify_payment_signature(order_id, payment_id, signature):
                    messages.error(request, "Invalid payment signature. Please contact support.")
                    return redirect('store:payment_failed', order_id=order.id)
                
                # Only update if not already processed
                if order.payment_status != 'completed':
                    # Update order status
                    order.status = 'processing'  # or 'completed' based on your workflow
                    order.payment_status = True
                    order.payment_id = payment_id
                    order.payment_signature = signature
                    order.payment_date = timezone.now()
                    order.save()
                    
                    # Create payment record
                    Payment.objects.create(
                        order=order,
                        payment_id=payment_id,
                        amount=order.total_amount,
                        payment_method='razorpay',
                        status='captured',
                        raw_data=json.dumps({
                            'order_id': order_id,
                            'payment_id': payment_id,
                            'signature': signature,
                            'timestamp': timezone.now().isoformat()
                        })
                    )
                    
                    # Clear the cart after successful payment
                    Cart.objects.filter(user=request.user).delete()
                    
                    # Send order confirmation email (you can implement this)
                    try:
                        # send_order_confirmation_email(order)
                        pass
                    except Exception as e:
                        logger.error(f"Failed to send order confirmation email: {str(e)}")
                
                # Render success template with order and payment details
                return render(request, 'store/payment/payment_success.html', {
                    'order': order,
                    'payment': {
                        'payment_id': payment_id,
                        'amount': order.total_amount,
                        'status': 'captured',
                        'date': order.payment_date
                    }
                })
                
        except Order.DoesNotExist:
            logger.error(f"Order not found or already processed: {order_id}")
            messages.error(request, "Order not found or already processed.")
            return redirect('store:home')
            
        except Exception as e:
            logger.error(f"Error processing payment success: {str(e)}", exc_info=True)
            messages.error(request, "There was an error processing your payment. Our team has been notified.")
            return redirect('store:payment_failed', order_id=order_id if 'order_id' in locals() else None)


class PaymentFailedView(LoginRequiredMixin, View):
    """Handle failed payment"""
    
    def get(self, request, *args, **kwargs):
        order_id = request.GET.get('order_id')
        error_code = request.GET.get('error_code')
        error_description = request.GET.get('error_description', 'Payment was not completed successfully.')
        
        # Get the order if order_id is provided
        order = None
        if order_id:
            try:
                order = Order.objects.get(id=order_id, user=request.user)
            except Order.DoesNotExist:
                pass
        
        context = {
            'order': order,
            'error_code': error_code,
            'error_message': error_description
        }
        
        return render(request, 'store/payment/payment_failed.html', context)
