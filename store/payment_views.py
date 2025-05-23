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

from .models import Order, Payment, OrderItem, Cart, CartItem
from .payment_utils import create_razorpay_order, verify_payment_signature

# Initialize Razorpay client
import razorpay
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class PaymentView(LoginRequiredMixin, DetailView):
    """View to handle payment page"""
    model = Order
    template_name = 'store/payment/payment_form.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user, status__in=['pending', 'processing'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['razorpay_key'] = settings.RAZORPAY_KEY_ID
        return context


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
    if request.method == 'POST':
        try:
            # Get webhook payload
            payload = json.loads(request.body)
            
            # Verify the webhook signature (optional but recommended)
            received_signature = request.headers.get('X-Razorpay-Signature', '')
            
            # Verify the signature
            # Note: In production, verify the webhook signature
            # client.utility.verify_webhook_signature(payload, signature, settings.RAZORPAY_WEBHOOK_SECRET)
            
            # Handle different webhook events
            event = payload.get('event')
            
            if event == 'payment.captured':
                # Handle successful payment
                payment_data = payload.get('payload', {}).get('payment', {})
                order_id = payment_data.get('notes', {}).get('order_id')
                
                if order_id:
                    order = get_object_or_404(Order, id=order_id)
                    order.status = 'completed'
                    order.save()
                    
                    # Create payment record
                    Payment.objects.create(
                        order=order,
                        payment_id=payment_data.get('id'),
                        amount=Decimal(payment_data.get('amount', 0)) / 100,  # Convert back to rupees
                        payment_method=payment_data.get('method'),
                        status=payment_data.get('status'),
                        raw_data=json.dumps(payment_data)
                    )
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


class PaymentSuccessView(LoginRequiredMixin, View):
    """Handle successful payment"""
    
    def get(self, request, *args, **kwargs):
        order_id = request.GET.get('order_id')
        payment_id = request.GET.get('payment_id')
        signature = request.GET.get('signature')
        
        if not all([order_id, payment_id, signature]):
            return HttpResponseBadRequest("Missing required parameters")
        
        try:
            # Get the order
            order = get_object_or_404(Order, razorpay_order_id=order_id, user=request.user)
            
            # Verify the payment signature
            if not verify_payment_signature(order_id, payment_id, signature):
                return HttpResponseBadRequest("Invalid payment signature")
            
            # Update order status
            with transaction.atomic():
                order.status = 'processing'  # or 'completed' based on your workflow
                order.payment_status = True
                order.payment_id = payment_id
                order.payment_signature = signature
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
                        'signature': signature
                    })
                )
                
                # Clear the cart after successful payment
                try:
                    cart = Cart.objects.get(user=request.user)
                    cart.items.all().delete()
                except Cart.DoesNotExist:
                    pass
                
            # Render success template with order and payment details
            return render(request, 'store/payment/payment_success.html', {
                'order': order,
                'payment': {
                    'payment_id': payment_id,
                    'amount': order.total_amount,
                    'status': 'captured'
                }
            })
            
        except Exception as e:
            # Log the error
            print(f"Error processing payment success: {str(e)}")
            messages.error(request, "There was an error processing your payment. Please contact support.")
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
