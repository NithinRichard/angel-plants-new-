from decimal import Decimal
import logging
import time
import traceback
import razorpay
from django.db import transaction
from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404, redirect, HttpResponseRedirect
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm

logger = logging.getLogger(__name__)
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, 
    DeleteView, View, FormView
)
from django.template import RequestContext
from django.template.loader import get_template
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from django.db.models.functions import Lower
from .filters import ProductFilter
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Sum, F, Count, Max, Min, Avg, Case, When, Value, IntegerField
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse, Http404, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity

from .filters import ProductFilter
from .forms import (
    ContactForm, ProductForm, ProductImageForm, ProductTagForm, 
    CheckoutForm, ReviewForm, AddressForm,
    ProductVariationForm, VariationForm, VariationOptionForm, OrderForm
)
from .models import (
    Category, Product, ProductImage, ProductVariation, Variation, VariationOption, 
    Review, Order, OrderItem, Cart, CartItem, Address, Wishlist, Payment,
    OrderActivity, BlogPost
)

# Get the User model
User = get_user_model()

class StaffOrderUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for staff to update order details.
    """
    model = Order
    template_name = 'store/staff/order_form.html'
    form_class = OrderForm
    slug_url_kwarg = 'order_number'
    slug_field = 'order_number'
    context_object_name = 'order'
    
    def test_func(self):
        """Ensure only staff members can access this view."""
        return self.request.user.is_staff
        
    def get_form_kwargs(self):
        """Pass the request to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
        
    def get_success_url(self):
        """Redirect to order detail page after successful update."""
        messages.success(self.request, 'Order has been updated successfully.')
        return reverse('store:staff_order_detail', kwargs={'order_number': self.object.order_number})

    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        context['order'] = order
        context['order_items'] = order.orderitem_set.all().select_related('product')
        return context


class StaffOrderDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    View for staff to see detailed information about a specific order.
    """
    model = Order
    template_name = 'store/staff/order_detail.html'
    context_object_name = 'order'
    slug_url_kwarg = 'order_number'
    slug_field = 'order_number'
    
    def test_func(self):
        """Ensure only staff members can access this view."""
        return self.request.user.is_staff
        
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        context['order_items'] = order.orderitem_set.all().select_related('product')
        context['order_activities'] = order.orderactivity_set.all().order_by('-created_at')
        return context

    def handle_no_permission(self):
        """Redirect to login page if user doesn't have permission."""
        messages.warning(self.request, 'You do not have permission to view this page.')
        return redirect('store:login')


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(lambda u: u.is_staff), name='dispatch')
@require_http_methods(["POST"])
def update_order_status(request, order_number):
    """
    Handle AJAX request to update order status.
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
    order = get_object_or_404(Order, order_number=order_number)
    new_status = request.POST.get('status')
    note = request.POST.get('note', '').strip()
    
    if not new_status or new_status not in dict(Order.STATUS_CHOICES).keys():
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    
    # Create activity log for status change
    activity_note = f'Status changed to {dict(Order.STATUS_CHOICES)[new_status]}'
    if note:
        activity_note += f': {note}'
    
    OrderActivity.objects.create(
        order=order,
        activity_type='status_change',
        note=activity_note,
        created_by=request.user
    )
    
    # Update order status
    order.status = new_status
    order.save()
    
    # If order is marked as shipped, update the shipped date
    if new_status == 'shipped' and not order.shipped_at:
        order.shipped_at = timezone.now()
        order.save()
    
    # If order is marked as delivered, update the delivered date
    if new_status == 'delivered' and not order.delivered_at:
        order.delivered_at = timezone.now()
        order.save()
    
    return JsonResponse({
        'success': True,
        'status_display': order.get_status_display(),
        'status_class': order.get_status_badge_class(),
        'updated_at': order.updated_at.strftime('%b %d, %Y %I:%M %p'),
        'activity_note': activity_note,
        'activity_date': timezone.now().strftime('%b %d, %Y %I:%M %p')
    })


class StaffOrderListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Order
    template_name = 'store/staff/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        """Return the list of orders with related data."""
        queryset = Order.objects.all().select_related('user', 'shipping_address', 'billing_address')
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status and status in dict(Order.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
        
        # Search by order number, customer name, or email
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(order_number__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Order by most recent first
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Add additional context data."""
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Order.STATUS_CHOICES
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context
    
    def test_func(self):
        return self.request.user.is_staff
    
    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect('store:home')
    
    def get_queryset(self):
        queryset = Order.objects.select_related('user').order_by('-created')
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status and status in dict(Order.Status.choices):
            queryset = queryset.filter(status=status)
        
        # Search by order number, email, or user
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(order_number__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query)
            )
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created__date__lte=date_to)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Order.Status.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


@require_http_methods(["POST"])
@login_required
@user_passes_test(lambda u: u.is_staff)
def update_order_status(request, order_number):
    """
    Update the status of an order with additional details.
    Only accessible by staff members via POST request.
    """
    order = get_object_or_404(Order, order_number=order_number)
    data = request.POST
    
    new_status = data.get('status')
    tracking_number = data.get('tracking_number', '').strip()
    tracking_url = data.get('tracking_url', '').strip()
    note = data.get('note', '').strip()
    notify_customer = data.get('notify_customer', 'false').lower() == 'true'
    
    # Validate status
    if not new_status or new_status not in dict(Order.Status.choices):
        return JsonResponse(
            {'success': False, 'message': 'Invalid order status'}, 
            status=400
        )
    
    # Update order fields
    order.status = new_status
    
    # Update tracking information if provided
    if tracking_number:
        order.tracking_number = tracking_number
    if tracking_url:
        order.tracking_url = tracking_url
    
    # Save the order
    order.save(update_fields=['status', 'tracking_number', 'tracking_url', 'updated_at'])
    
    # Create activity log
    activity_details = []
    if order.status != order.tracker.previous('status'):
        activity_details.append(f"Status changed to {order.get_status_display()}")
    if tracking_number and order.tracking_number != order.tracker.previous('tracking_number'):
        activity_details.append(f"Tracking number updated to {tracking_number}")
    if tracking_url and order.tracking_url != order.tracker.previous('tracking_url'):
        activity_details.append("Tracking URL updated")
    
    # Add the activity log
    activity = OrderActivity.objects.create(
        order=order,
        user=request.user,
        activity_type='status_change',
        details="; ".join(activity_details) if activity_details else "Order updated",
        note=note or None
    )
    
    # Send email notification if requested and applicable
    if notify_customer and order.user and new_status in ['processing', 'shipped', 'delivered']:
        try:
            send_order_status_email(order, request, activity)
            activity.notification_sent = True
            activity.save(update_fields=['notification_sent'])
        except Exception as e:
            # Log the error but don't fail the request
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send status update email for order {order.order_number}: {str(e)}")
    
    # Prepare response data
    response_data = {
        'success': True,
        'message': f'Order #{order.order_number} has been updated.',
        'order_number': order.order_number,
        'new_status': order.get_status_display(),
        'new_status_class': order.status,
        'tracking_info': {
            'number': order.tracking_number or '',
            'url': order.tracking_url or ''
        },
        'activity': {
            'id': activity.id,
            'timestamp': activity.timestamp.isoformat(),
            'details': activity.details,
            'user': str(activity.user) if activity.user else 'System'
        }
    }
    
    # If it's an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(response_data)
    
    # For regular form submission
    messages.success(request, f'Order #{order.order_number} has been updated.')
    return redirect('store:staff_order_detail', order_number=order.order_number)


def send_order_status_email(order, request):
    """
    Send email notification to customer about order status update.
    """
    subject = f'Order #{order.order_number} - {order.get_status_display()}'
    
    context = {
        'order': order,
        'status_display': order.get_status_display(),
        'site_name': settings.SITE_NAME,
        'site_domain': request.get_host(),
        'protocol': 'https' if request.is_secure() else 'http',
    }
    
    # Render HTML and plain text versions of the email
    html_message = render_to_string('emails/order_status_update.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email if order.user else order.email],
        html_message=html_message,
        fail_silently=True,
    )


class StaffDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Dashboard view for staff members with store statistics and recent activities.
    """
    template_name = 'store/staff_dashboard.html'
    login_url = 'accounts:login'
    
    def test_func(self):
        """Ensure only staff members can access this view."""
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Sales Statistics
        recent_orders = Order.objects.filter(created_at__gte=thirty_days_ago)
        total_sales = recent_orders.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        
        # Sales comparison with previous period
        sixty_days_ago = now - timedelta(days=60)
        previous_period_sales = Order.objects.filter(
            created_at__range=(sixty_days_ago, thirty_days_ago)
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        sales_change = Decimal('0')
        if previous_period_sales > 0:
            sales_change = ((total_sales - previous_period_sales) / previous_period_sales) * 100
        
        # Order counts
        order_count = recent_orders.count()
        previous_order_count = Order.objects.filter(
            created_at__range=(sixty_days_ago, thirty_days_ago)
        ).count()
        
        order_change = 0
        if previous_order_count > 0:
            order_change = ((order_count - previous_order_count) / previous_order_count) * 100
        
        # Recent Orders
        recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
        
        # Low Stock Products
        low_stock_products = Product.objects.filter(
            track_quantity=True,
            quantity__lte=10
        ).order_by('quantity')[:5]
        
        # Popular Products
        popular_products = Product.objects.annotate(
            order_count=Count('order_items')
        ).order_by('-order_count')[:5]
        
        # Sales by Day (Last 7 days)
        seven_days_ago = now - timedelta(days=7)
        daily_sales = Order.objects.filter(
            created_at__gte=seven_days_ago,
            status__in=['paid', 'delivered']
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total=Sum('total_amount')
        ).order_by('day')
        
        # Format data for charts
        sales_data = {
            'labels': [(now - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)],
            'datasets': [{
                'label': 'Sales',
                'data': [0] * 7,
                'borderColor': '#4e73df',
                'fill': True
            }]
        }
        
        for sale in daily_sales:
            day_index = (now.date() - sale['day'].date()).days
            if 0 <= day_index < 7:
                sales_data['datasets'][0]['data'][6 - day_index] = float(sale['total'] or 0)
        
        context.update({
            'total_sales': total_sales,
            'sales_change': float(sales_change),
            'order_count': order_count,
            'order_change': order_change,
            'recent_orders': recent_orders,
            'low_stock_products': low_stock_products,
            'popular_products': popular_products,
            'sales_data': sales_data,
            'now': now,
            'thirty_days_ago': thirty_days_ago,
        })
        
        return context


class AddressBookView(LoginRequiredMixin, TemplateView):
    """
    View to display and manage user's address book.
    """
    template_name = 'store/address_book.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's addresses, grouped by type
        addresses = user.addresses.all()
        
        context.update({
            'shipping_addresses': addresses.filter(address_type='shipping'),
            'billing_addresses': addresses.filter(address_type='billing'),
        })
        return context


class AddressCreateView(LoginRequiredMixin, CreateView):
    """
    View to create a new address.
    """
    model = Address
    template_name = 'store/address_form.html'
    fields = [
        'address_type', 'first_name', 'last_name', 'company',
        'address_line1', 'address_line2', 'city', 'state',
        'postal_code', 'country', 'phone', 'default'
    ]
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    
    def get_success_url(self):
        messages.success(self.request, 'Address added successfully.')
        return reverse_lazy('store:address_book')


class AddressUpdateView(LoginRequiredMixin, UpdateView):
    """
    View to update an existing address.
    """
    model = Address
    template_name = 'store/address_form.html'
    fields = [
        'address_type', 'first_name', 'last_name', 'company',
        'address_line1', 'address_line2', 'city', 'state',
        'postal_code', 'country', 'phone', 'default'
    ]
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        messages.success(self.request, 'Address updated successfully.')
        return reverse_lazy('store:address_book')


class AddressDeleteView(LoginRequiredMixin, DeleteView):
    """
    View to delete an address.
    """
    model = Address
    template_name = 'store/address_confirm_delete.html'
    
    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        messages.success(self.request, 'Address deleted successfully.')
        return reverse_lazy('store:address_book')


class SetDefaultAddressView(LoginRequiredMixin, View):
    """
    View to set an address as default for its type.
    """
    def post(self, request, *args, **kwargs):
        address = get_object_or_404(Address, pk=kwargs['pk'], user=request.user)
        
        # Set all addresses of this type to not default
        Address.objects.filter(
            user=request.user, 
            address_type=address.address_type
        ).update(default=False)
        
        # Set this address as default
        address.default = True
        address.save()
        
        messages.success(request, f'Default {address.get_address_type_display().lower()} updated.')
        return redirect('store:address_book')


class OrderDetailView(LoginRequiredMixin, DetailView):
    """
    View to display details of a specific order.
    """
    model = Order
    template_name = 'store/order_detail.html'
    context_object_name = 'order'
    slug_url_kwarg = 'order_number'
    slug_field = 'order_number'
    
    def get_queryset(self):
        # Only allow users to view their own orders
        return Order.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        
        # Add order items to context
        context['order_items'] = order.items.select_related('product').all()
        
        # Add shipping and billing info from order fields
        context['shipping_info'] = {
            'address': order.address,
            'city': order.city,
            'state': order.state,
            'postal_code': order.postal_code,
            'country': order.country
        }
            
        return context


class OrderHistoryView(LoginRequiredMixin, ListView):
    """
    View to display user's complete order history.
    """
    model = Order
    template_name = 'store/order_history.html'
    context_object_name = 'orders'
    paginate_by = 10
    login_url = 'accounts:login'
    redirect_field_name = 'next'
    
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class InvoiceView(LoginRequiredMixin, DetailView):
    model = Order
    template_name = 'store/invoice.html'
    context_object_name = 'order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        
        # Calculate totals
        subtotal = sum(item.quantity * item.price for item in order.items.all())
        tax = subtotal * Decimal('0.18')  # 18% GST
        shipping = Decimal('99.00')  # Fixed shipping cost
        total = subtotal + tax + shipping
        
        context.update({
            'subtotal': subtotal,
            'tax': tax.quantize(Decimal('0.01')),
            'shipping': shipping,
            'total': total.quantize(Decimal('0.01')),
            'company_info': {
                'name': 'Angel Plants',
                'address': '123 Plant Street, Garden City',
                'phone': '+91 1234567890',
                'email': 'info@angelplants.com',
                'gstin': '27AABCU1234C1Z5'
            }
        })
        return context
    
    def render_to_response(self, context, **response_kwargs):
        # Get the order from context
        order = context['order']
        
        # Calculate totals
        subtotal = sum(item.quantity * item.price for item in order.items.all())
        tax = subtotal * Decimal('0.18')  # 18% GST
        shipping = Decimal('99.00')  # Fixed shipping cost
        total = subtotal + tax + shipping
        
        # Create the PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_number}.pdf"'
        
        # Create the PDF object
        doc = SimpleDocTemplate(response, pagesize=A4)
        
        # Add styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=1))
        styles.add(ParagraphStyle(name='CenterAlign', parent=styles['Normal'], alignment=1, fontSize=14, spaceAfter=20))
        
        # Create story
        story = []
        
        # Add company info
        story.append(Paragraph("<strong>Angel Plants</strong>", styles['CenterAlign']))
        story.append(Paragraph("123 Plant Street, Garden City", styles['Normal']))
        story.append(Paragraph("Phone: +91 1234567890", styles['Normal']))
        story.append(Paragraph("Email: info@angelplants.com", styles['Normal']))
        story.append(Paragraph("GSTIN: 27AABCU1234C1Z5", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Add invoice header
        story.append(Paragraph("INVOICE", styles['CenterAlign']))
        story.append(Spacer(1, 20))
        
        # Add billing info
        billing_info = [
            ["Bill To:", f"{order.first_name} {order.last_name}"],
            ["", order.address],
            ["", f"{order.city}, {order.state} {order.postal_code}"],
            ["", order.country],
            ["Invoice Number:", order.order_number],
            ["Date:", order.created_at.strftime("%B %d, %Y")],
            ["Payment Status:", "Paid" if order.payment_status else "Unpaid"]
        ]
        
        billing_table = Table(billing_info, colWidths=[100, 400])
        billing_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(billing_table)
        story.append(Spacer(1, 20))
        
        # Add items table
        items_data = [['Item', 'Quantity', 'Price', 'Subtotal']]
        for item in order.items.all():
            items_data.append([
                item.product.name,
                str(item.quantity),
                f"₹{item.price}",
                f"₹{item.quantity * item.price}"
            ])
        
        items_table = Table(items_data)
        items_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Add totals
        totals_data = [
            ["Subtotal", f"₹{subtotal}"],
            ["Shipping", f"₹{shipping}"],
            ["GST (18%)", f"₹{tax}"],
            ["Total Amount", f"₹{total}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[300, 200])
        totals_table.setStyle(TableStyle([
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,-1), (-1,-1), colors.black)
        ]))
        story.append(totals_table)
        
        # Build the PDF
        doc.build(story)
        
        return response

class AccountView(LoginRequiredMixin, TemplateView):
    """
    View to display user account dashboard with order history and account details.
    """
    template_name = 'store/account.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user's orders, most recent first
        orders = Order.objects.filter(user=user).order_by('-created_at')
        
        context.update({
            'orders': orders,
            'user': user,
        })
        return context


from .forms import ProfileForm

from .forms import ProfileForm, UserForm
from .models import Profile

class AccountSettingsView(LoginRequiredMixin, TemplateView):
    """
    View for users to update their account settings and personal information.
    """
    template_name = 'store/account_settings.html'

    def get(self, request, *args, **kwargs):
        user_form = UserForm(instance=request.user)
        try:
            profile_form = ProfileForm(instance=request.user.profile)
        except Profile.DoesNotExist:
            profile_form = ProfileForm()
        return self.render_to_response(
            self.get_context_data(
                user_form=user_form,
                profile_form=profile_form
            )
        )

    def post(self, request, *args, **kwargs):
        user_form = UserForm(request.POST, instance=request.user)
        try:
            profile_form = ProfileForm(
                request.POST,
                request.FILES,
                instance=request.user.profile
            )
        except Profile.DoesNotExist:
            profile_form = ProfileForm(
                request.POST,
                request.FILES
            )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('store:account_settings')
        
        messages.error(request, 'Please correct the errors below.')
        return self.render_to_response(
            self.get_context_data(
                user_form=user_form,
                profile_form=profile_form
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'settings'
        return context


class RegisterView(CreateView):
    """
    View for new users to create an account.
    """
    model = User
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('store:account')
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return UserCreationForm

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Your account has been created successfully! Please log in.'
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create an Account'
        return context


class CheckoutCancelView(LoginRequiredMixin, TemplateView):
    """
    View to handle cancelled checkouts.
    """
    template_name = 'store/checkout_cancel.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = 'Your checkout was cancelled. Your cart has been saved for your convenience.'
        return context


class CheckoutSuccessView(LoginRequiredMixin, TemplateView):
    """
    View to display order confirmation after successful checkout.
    """
    template_name = 'store/checkout_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_number = self.kwargs.get('order_number')
        
        try:
            # Get the order for the current user with the given order number
            order = Order.objects.get(
                order_number=order_number,
                user=self.request.user
            )
            context['order'] = order
            
            # Mark the order as paid if it's in 'pending' status
            if order.status == Order.Status.PENDING:
                order.status = Order.Status.PAID
                order.paid = True
                order.save()
                
            # Clear the user's cart after successful checkout
            try:
                cart = Cart.objects.get(user=self.request.user, status='active')
                cart.status = 'completed'
                cart.save()
            except Cart.DoesNotExist:
                pass
                
        except Order.DoesNotExist:
            # If order not found, set order to None (template will show appropriate message)
            context['order'] = None
            
        return context

class HomeView(TemplateView):
    template_name = 'store/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Home - Angel\'s Plant Shop'
        
        # Only show featured products that are in stock or allow backorder
        context['featured_products'] = Product.objects.filter(
            is_featured=True, 
            is_active=True
        ).filter(
            Q(quantity__gt=0) | Q(allow_backorder=True)
        )[:8]
        
        # Only show bestsellers that are in stock or allow backorder
        context['bestsellers'] = Product.objects.filter(
            is_bestseller=True, 
            is_active=True
        ).filter(
            Q(quantity__gt=0) | Q(allow_backorder=True)
        )[:4]
        
        # Only show new arrivals that are in stock or allow backorder
        context['new_arrivals'] = Product.objects.filter(
            is_active=True
        ).filter(
            Q(quantity__gt=0) | Q(allow_backorder=True)
        ).order_by('-created_at')[:4]
        
        # Get categories with active products
        context['categories'] = Category.objects.filter(
            products__is_active=True,
            products__quantity__gt=0
        ).distinct()[:8]
        
        return context


class AboutView(TemplateView):
    template_name = 'store/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'About Us - Angel\'s Plant Shop'
        context['team_members'] = [
            {
                'name': 'John Doe',
                'position': 'Founder & CEO',
                'bio': 'Passionate about plants and sustainable living.',
                'image': 'https://randomuser.me/api/portraits/men/1.jpg'
            },
            {
                'name': 'Jane Smith',
                'position': 'Head Gardener',
                'bio': 'Expert in plant care with 10+ years of experience.',
                'image': 'https://randomuser.me/api/portraits/women/2.jpg'
            },
            {
                'name': 'Mike Johnson',
                'position': 'Customer Care',
                'bio': 'Loves helping customers find their perfect plants.',
                'image': 'https://randomuser.me/api/portraits/men/3.jpg'
            }
        ]
        return context


class ContactView(FormView):
    template_name = 'store/contact.html'
    form_class = ContactForm
    success_url = '/contact/thanks/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Contact Us - Angel\'s Plant Shop'
        context['contact_email'] = getattr(settings, 'CONTACT_EMAIL', 'contact@example.com')
        context['contact_phone'] = getattr(settings, 'CONTACT_PHONE', '+1 (555) 123-4567')
        context['business_address'] = getattr(settings, 'BUSINESS_ADDRESS', '123 Plant St, Greenery City, GC 12345')
        context['business_hours'] = getattr(settings, 'BUSINESS_HOURS', [
            'Monday - Friday: 9:00 AM - 6:00 PM',
            'Saturday: 10:00 AM - 4:00 PM',
            'Sunday: Closed'
        ])
        return context
        
    def form_valid(self, form):
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']
        
        try:
            print("\nDEBUG: Attempting to send email...")
            print(f"From: {settings.DEFAULT_FROM_EMAIL}")
            print(f"To: {settings.CONTACT_EMAIL}")
            
            # Simple text email for testing
            email_subject = f"Contact Form: {subject}"
            email_message = f"""
            New Contact Form Submission
            ---------------------------
            
            Name: {name}
            Email: {email}
            Subject: {subject}
            
            Message:
            {message}
            
            ---------------------------
            This email was sent from the contact form on Angel's Plant Shop.
            """
            
            # Print the email content for debugging
            print("\nDEBUG: Email Content:")
            print(f"Subject: {email_subject.strip()}")
            print(f"Message: {email_message.strip()}")
            
            # Using the simple send_mail function
            from django.core.mail import send_mail
            
            send_mail(
                subject=email_subject.strip(),
                message=email_message.strip(),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            
            print("DEBUG: Email sent successfully!")
            messages.success(self.request, 'Your message has been sent successfully!')
            return super().form_valid(form)
            
        except Exception as e:
            import traceback
            error_msg = f'Error sending message: {str(e)}. Please try again later.'
            print(f"\nERROR: {error_msg}")
            print("Traceback:")
            traceback.print_exc()
            messages.error(self.request, error_msg)
            return self.form_invalid(form)

@login_required
def add_to_wishlist(request, product_id):
    """
    Add a product to the user's wishlist.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to add items to your wishlist.')
        return redirect('store:login')
    
    product = get_object_or_404(Product, id=product_id, is_active=True)
    
    # Check if the product is already in the user's wishlist
    if Wishlist.objects.filter(user=request.user, product=product).exists():
        messages.info(request, 'This product is already in your wishlist.')
    else:
        try:
            # Create a new wishlist item
            Wishlist.objects.create(
                user=request.user,
                product=product,
                quantity=1
            )
            messages.success(request, 'Product added to your wishlist.')
        except Exception as e:
            messages.error(request, 'Failed to add product to wishlist. Please try again.')
            logger.error(f"Error adding to wishlist: {str(e)}")
    
    # Redirect back to the previous page or product detail
    redirect_url = request.META.get('HTTP_REFERER', 'store:product_detail')
    try:
        return redirect(redirect_url)
    except:
        return redirect('store:product_detail', slug=product.slug)


def api_toggle_wishlist(request, product_id):
    """
    API endpoint to toggle a product in the user's wishlist.
    Returns JSON response for AJAX requests.
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Please log in to modify your wishlist.',
            'login_required': True
        }, status=403)
    
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found or is no longer available.'
        }, status=404)
    
    # Check if the product is already in the user's wishlist
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    
    if wishlist_item:
        # Remove from wishlist
        wishlist_item.delete()
        added = False
        message = 'Product removed from your wishlist.'
    else:
        # Add to wishlist
        try:
            Wishlist.objects.create(
                user=request.user,
                product=product,
                quantity=1
            )
            added = True
            message = 'Product added to your wishlist.'
        except Exception as e:
            logger.error(f"Error adding to wishlist: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Failed to update wishlist. Please try again.'
            }, status=500)
    
    # Get updated wishlist count
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    
    return JsonResponse({
        'success': True,
        'added': added,
        'message': message,
        'wishlist_count': wishlist_count
    })


@login_required
def remove_from_wishlist(request, product_id):
    """
    Remove an item from the user's wishlist.
    """
    try:
        wishlist_item = Wishlist.objects.get(
            product_id=product_id,
            user=request.user
        )
        wishlist_item.delete()
        messages.success(request, 'Item removed from your wishlist.')
    except Wishlist.DoesNotExist:
        messages.error(request, 'Item not found in your wishlist.')
    except Exception as e:
        logger.error(f"Error removing from wishlist: {str(e)}")
        messages.error(request, 'Failed to remove item from wishlist. Please try again.')
    
    # Redirect back to the previous page or wishlist
    redirect_url = request.META.get('HTTP_REFERER', 'store:wishlist')
    try:
        return redirect(redirect_url)
    except:
        return redirect('store:wishlist')


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
            
            # Prepare success response
            response_data = {
                'status': 'success',
                'message': f"{product.name} removed from cart",
                'cart': {
                    'item_count': cart.item_count,
                    'total': str(cart.total),
                },
                'removed_item': {
                    'product_id': product.id,
                    'name': product.name,
                    'quantity': 0,
                    'price': str(product.price),
                    'subtotal': '0.00'
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
        redirect_url = request.META.get('HTTP_REFERER', reverse('cart'))
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
    return redirect(reverse('store:cart'))


@login_required
def add_to_cart(request, product_id, quantity=1):
    """
    Add a product to the cart or update quantity if already in cart.
    Handles both AJAX and regular form submissions.
    """
    if request.method != 'POST':
        return JsonResponse(
            {'status': 'error', 'message': 'Invalid request method'}, 
            status=405
        )
    
    try:
        # Get the product or return 404
        product = get_object_or_404(Product, id=product_id)
        
        # Check if product is active
        if not product.is_active:
            raise ValidationError('This product is no longer available.')
        
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError('Quantity must be at least 1')
        except (ValueError, TypeError):
            raise ValidationError('Invalid quantity')
            
        # Check stock if tracking is enabled
        if product.track_quantity and product.quantity < quantity:
            raise ValidationError(
                f'Only {product.quantity} items available in stock.'
            )
        
        # Get or create cart for the current user
        with transaction.atomic():
            cart, created = Cart.objects.select_for_update().get_or_create(
                user=request.user,
                status='active',
                defaults={'status': 'active'}
            )
            
            # Check if item already exists in cart
            try:
                cart_item = CartItem.objects.get(cart=cart, product=product)
                # Item exists, update quantity
                cart_item.increase_quantity(quantity)
                cart_item.save()
            except CartItem.DoesNotExist:
                # Item doesn't exist, create new with quantity
                cart_item = CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
            
            # Update cart totals
            cart.update_totals()
        
        # Prepare response data
        response_data = {
            'status': 'success',
            'message': f"{product.name} added to cart",
            'cart': {
                'item_count': cart.item_count,
                'total': str(cart.total.quantize(Decimal('0.00'))),
                'total_quantity': cart.total_quantity,
            },
            'added_item': {
                'product_id': product.id,
                'name': product.name,
                'quantity': cart_item.quantity,
                'price': str(cart_item.price.quantize(Decimal('0.00'))),
                'subtotal': str((cart_item.quantity * cart_item.price).quantize(Decimal('0.00')))
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
        
    except ValidationError as e:
        error_msg = str(e)
        status_code = 400
    except Product.DoesNotExist:
        error_msg = 'Product not found.'
        status_code = 404
    except Exception as e:
        error_msg = 'An error occurred while adding the item to your cart.'
        logger.exception("Error in add_to_cart")
        status_code = 500
    
    # Handle errors
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(
            {'status': 'error', 'message': error_msg}, 
            status=status_code
        )
    
    messages.error(request, error_msg)
    return redirect(request.META.get('HTTP_REFERER', reverse('store:home')))


@require_http_methods(["POST"])
@login_required
def update_cart(request, item_id=None):
    try:
        if request.body:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            action = data.get('action')
        else:
            # Handle form submission
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))
            action = request.POST.get('action')
            
        # If item_id is provided in the URL, use that instead of product_id
        if item_id is not None:
            cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
            product_id = cart_item.product.id
        
        if item_id is None:
            if not product_id or quantity < 1:
                return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
            
            product = get_object_or_404(Product, id=product_id, is_active=True)
            
            # Get or create cart for the current user
            cart, created = Cart.objects.get_or_create(
                user=request.user,
                defaults={'status': 'active'}
            )
            
            # Get or create cart item
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 0}
            )
        else:
            cart = cart_item.cart
        
        # Update quantity based on action
        if action == 'add':
            cart_item.quantity = F('quantity') + quantity
        elif action == 'set' or item_id is not None:
            cart_item.quantity = quantity
        elif action == 'remove':
            cart_item.quantity = 0
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)
        
        # Save the cart item
        cart_item.save()
        cart_item.refresh_from_db()
        
        # If quantity is 0 or less, delete the item
        if cart_item.quantity <= 0:
            cart_item.delete()
            item_quantity = 0
            item_subtotal = 0
        else:
            item_quantity = cart_item.quantity
            item_subtotal = float(cart_item.product.price) * item_quantity
        
        # Recalculate cart totals
        cart_items = CartItem.objects.filter(cart=cart).select_related('product')
        cart_total = sum(float(item.product.price) * item.quantity for item in cart_items)
        cart_count = sum(item.quantity for item in cart_items)
        
        # Update cart totals
        cart.total = cart_total
        cart.item_count = cart_count
        cart.save()
        
        # Get updated cart items for the response
        cart_items_data = [
            {
                'id': item.id,
                'product_id': item.product.id,
                'name': item.product.name,
                'price': str(item.product.price),
                'quantity': item.quantity,
                'subtotal': str(float(item.product.price) * item.quantity),
                'image': item.product.image.url if hasattr(item.product, 'image') and item.product.image else ''
            }
            for item in cart_items
        ]
        
        # Prepare response data
        response_data = {
            'success': True,
            'message': 'Cart updated successfully',
            'message_shown': False,  # Flag to indicate if message was shown server-side
            'item_count': cart_count,
            'total': cart_total,
            'item_total': item_subtotal if 'item_subtotal' in locals() else 0,
            'items': cart_items_data
        }
        
        # If this is an AJAX request, return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(response_data)
            
        # Otherwise, redirect back to the cart page with a success message
        messages.success(request, 'Cart updated successfully')
        return redirect('store:cart')
        
    except json.JSONDecodeError:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        messages.error(request, 'Invalid request')
        return redirect('store:cart')
    except Product.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)
        messages.error(request, 'Product not found')
        return redirect('store:cart')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
        messages.error(request, 'An error occurred while updating your cart')
        return redirect('store:cart')


def api_update_cart(request):
    """
    API endpoint to update cart items via AJAX.
    Expects JSON data with item_id and quantity.
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Authentication required',
            'login_required': True
        }, status=401)
    
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST method is allowed'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        if not item_id:
            raise ValueError('item_id is required')
            
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            item_removed = False
            message = 'Cart updated successfully.'
        else:
            cart_item.delete()
            item_removed = True
            message = 'Item removed from cart.'
        
        # Get updated cart data
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = CartItem.objects.filter(cart=cart).select_related('product')
        cart_total = sum(item.product.price * item.quantity for item in cart_items)
        
        return JsonResponse({
            'status': 'success',
            'message': message,
            'item_removed': item_removed,
            'cart_total': float(cart_total),  # Convert Decimal to float for JSON serialization
            'cart_count': cart_items.count(),
            'item_total': float(cart_item.product.price * cart_item.quantity) if not item_removed else 0
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while updating the cart',
            'error': str(e)
        }, status=500)


def api_rate_product(request):
    """
    API endpoint to submit product ratings via AJAX.
    Expects JSON data with product_id and rating (1-5).
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'Authentication required',
            'login_required': True
        }, status=401)
    
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Only POST method is allowed'
        }, status=405)
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        rating = int(data.get('rating', 0))
        review_text = data.get('review', '').strip()
        
        if not product_id:
            raise ValueError('product_id is required')
            
        if not (1 <= rating <= 5):
            raise ValueError('Rating must be between 1 and 5')
            
        product = get_object_or_404(Product, id=product_id)
        
        # Check if user has purchased the product
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status='delivered',
            product=product
        ).exists()
        
        if not has_purchased:
            return JsonResponse({
                'status': 'error',
                'message': 'You must purchase the product before rating it',
                'purchase_required': True
            }, status=403)
        
        # Check if user has already rated this product
        from .models import ProductRating
        
        rating_obj, created = ProductRating.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={
                'rating': rating,
                'review': review_text,
                'is_approved': True  # Auto-approve for now, can be moderated later
            }
        )
        
        # Update product's average rating
        product.update_average_rating()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you for your rating!',
            'created': created,
            'rating': rating_obj.rating,
            'review': rating_obj.review,
            'user_name': request.user.get_full_name() or request.user.username,
            'created_at': rating_obj.created_at.strftime('%B %d, %Y'),
            'average_rating': float(product.average_rating) if product.average_rating else 0,
            'rating_count': product.ratings.count()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except ValueError as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while submitting your rating',
            'error': str(e)
        }, status=500)


class ProductSearchView(ListView):
    model = Product
    template_name = 'store/product_search.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Get search query
        query = self.request.GET.get('q', '').strip()
        
        # Get filter parameters
        category = self.request.GET.get('category', '')
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        in_stock = self.request.GET.get('in_stock')
        sort_by = self.request.GET.get('sort_by', 'relevance')
        
        # Apply search query
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(short_description__icontains=query) |
                Q(category__name__icontains=query) |
                Q(tags__name__icontains=query)
            ).distinct()
        
        # Apply filters
        if category:
            queryset = queryset.filter(category__slug=category)
            
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
            
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
            
        if in_stock == 'true':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        # Apply sorting
        if sort_by == 'price_asc':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price')
        elif sort_by == 'name_asc':
            queryset = queryset.order_by('name')
        elif sort_by == 'name_desc':
            queryset = queryset.order_by('-name')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'bestselling':
            queryset = queryset.order_by('-sold_count')
        elif sort_by == 'relevance' and query:
            # For relevance, we'll order by best match first
            from django.db.models import Case, When, Value, IntegerField
            
            # Create a case to order by the number of matches
            queryset = queryset.annotate(
                relevance=Case(
                    When(name__icontains=query, then=Value(3)),
                    When(description__icontains=query, then=Value(2)),
                    When(short_description__icontains=query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ).order_by('-relevance', '-created_at')
        else:
            # Default sorting by creation date
            queryset = queryset.order_by('-created_at')
            
        return queryset.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current search parameters
        query = self.request.GET.get('q', '')
        category = self.request.GET.get('category', '')
        min_price = self.request.GET.get('min_price', '')
        max_price = self.request.GET.get('max_price', '')
        in_stock = self.request.GET.get('in_stock', '')
        sort_by = self.request.GET.get('sort_by', 'relevance')
        
        # Get all categories for the filter
        categories = Category.objects.all()
        
        # Get min and max prices for the price range filter
        price_range = Product.objects.filter(is_active=True).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        
        # Build filter URL
        base_url = f"{reverse('product_search')}?"
        params = []
        
        if query:
            params.append(f"q={query}")
        if category:
            params.append(f"category={category}")
        if min_price:
            params.append(f"min_price={min_price}")
        if max_price:
            params.append(f"max_price={max_price}")
        if in_stock:
            params.append(f"in_stock={in_stock}")
            
        filter_url = base_url + '&'.join(params) if params else base_url
        
        context.update({
            'query': query,
            'selected_category': category,
            'min_price': min_price,
            'max_price': max_price,
            'price_min': price_range['min_price'] or 0,
            'price_max': price_range['max_price'] or 1000,
            'in_stock': in_stock == 'true',
            'sort_by': sort_by,
            'categories': categories,
            'filter_url': filter_url,
            'result_count': self.get_queryset().count(),
            'page_title': f"Search Results for '{query}'" if query else "Search Products"
        })
        
        return context


class ShippingReturnsView(TemplateView):
    template_name = 'store/shipping_returns.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Shipping & Returns - Angel\'s Plant Shop'
        context['last_updated'] = 'May 14, 2025'
        
        # Sample shipping and returns content
        context['sections'] = [
            {
                'title': 'Shipping Information',
                'content': 'We offer fast and reliable shipping to all 50 states. All orders are processed within 1-3 business days (excluding weekends and holidays) after receiving your order confirmation email.',
                'subsections': [
                    {
                        'title': 'Processing Time',
                        'content': 'Orders are not shipped or delivered on weekends or holidays. If we are experiencing a high volume of orders, shipments may be delayed by a few days. Please allow additional days in transit for delivery.'
                    },
                    {
                        'title': 'Shipping Rates & Delivery Estimates',
                        'content': 'Shipping charges for your order will be calculated and displayed at checkout. Delivery estimates are based on the shipping method you select during checkout.'
                    },
                    {
                        'title': 'Shipping Methods',
                        'content': 'We offer the following shipping methods:\n- Standard Shipping: 3-7 business days\n- Expedited Shipping: 2-3 business days\n- Overnight Shipping: 1 business day (order by 12 PM EST)'
                    }
                ]
            },
            {
                'title': 'Order Tracking',
                'content': 'You will receive a shipping confirmation email with a tracking number once your order has shipped. You can track your package using the tracking number provided.'
            },
            {
                'title': 'Returns & Exchanges',
                'content': 'We want you to be completely satisfied with your purchase. If you\'re not happy with your order, we\'re here to help!',
                'subsections': [
                    {
                        'title': 'Return Policy',
                        'content': 'You have 14 calendar days to return an item from the date you received it. To be eligible for a return, your item must be unused and in the same condition that you received it. Your item must be in the original packaging.'
                    },
                    {
                        'title': 'Refunds',
                        'content': 'Once we receive your item, we will inspect it and notify you that we have received your returned item. We will immediately notify you on the status of your refund after inspecting the item. If your return is approved, we will initiate a refund to your original method of payment. You will receive the credit within a certain amount of days, depending on your card issuer\'s policies.'
                    },
                    {
                        'title': 'Exchanges',
                        'content': 'The fastest way to ensure you get what you want is to return the item you have, and once the return is accepted, make a separate purchase for the new item.'
                    },
                    {
                        'title': 'Damaged or Defective Items',
                        'content': 'If you received a damaged or defective item, please contact us immediately at support@angelsplants.com with your order number and photos of the damaged item. We will work with you to resolve the issue as quickly as possible.'
                    }
                ]
            },
            {
                'title': 'Non-returnable Items',
                'content': 'The following items cannot be returned:\n- Gift cards\n- Downloadable software products\n- Personalized or custom orders\n- Plants that have been planted or repotted\n- Perishable goods such as food, flowers, or plants'
            },
            {
                'title': 'International Shipping',
                'content': 'We currently only ship within the United States. We do not ship internationally at this time.'
            },
            {
                'title': 'Contact Us',
                'content': 'If you have any questions about our shipping and returns policy, please contact us at support@angelsplants.com or call us at (555) 123-4567 during our business hours: Monday-Friday, 9:00 AM - 5:00 PM EST.'
            }
        ]
        return context


class PrivacyView(TemplateView):
    template_name = 'store/privacy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Privacy Policy - Angel\'s Plant Shop'
        context['last_updated'] = 'May 14, 2025'
        context['company_name'] = 'Angel\'s Plant Shop'
        context['company_email'] = 'privacy@angelsplants.com'
        
        # Sample privacy policy content - you might want to move this to a model or markdown file
        context['sections'] = [
            {
                'title': 'Introduction',
                'content': f"Welcome to {context['company_name']}'s Privacy Policy. We respect your privacy and are committed to protecting your personal data. This privacy policy will inform you about how we look after your personal data when you visit our website and tell you about your privacy rights and how the law protects you."
            },
            {
                'title': 'Information We Collect',
                'content': 'We may collect, use, store and transfer different kinds of personal data about you which we have grouped together as follows: Identity Data, Contact Data, Financial Data, Transaction Data, Technical Data, Profile Data, Usage Data, and Marketing and Communications Data.'
            },
            {
                'title': 'How We Use Your Data',
                'content': 'We will only use your personal data when the law allows us to. Most commonly, we will use your personal data to process and deliver your order, manage our relationship with you, enable you to participate in promotions, and improve our website.'
            },
            {
                'title': 'Data Security',
                'content': 'We have put in place appropriate security measures to prevent your personal data from being accidentally lost, used or accessed in an unauthorized way, altered or disclosed. We limit access to your personal data to those employees and other staff who have a business need to know such data.'
            },
            {
                'title': 'Data Retention',
                'content': 'We will only retain your personal data for as long as necessary to fulfill the purposes we collected it for, including for the purposes of satisfying any legal, accounting, or reporting requirements.'
            },
            {
                'title': 'Your Legal Rights',
                'content': 'Under certain circumstances, you have rights under data protection laws in relation to your personal data including the right to request access, correction, erasure, restriction, transfer, to object to processing, to portability of data and (where the lawful ground of processing is consent) to withdraw consent.'
            },
            {
                'title': 'Third-Party Links',
                'content': 'Our website may include links to third-party websites, plug-ins and applications. Clicking on those links may allow third parties to collect or share data about you. We do not control these third-party websites and are not responsible for their privacy statements.'
            },
            {
                'title': 'Cookies',
                'content': 'Our website uses cookies to distinguish you from other users of our website. This helps us to provide you with a good experience when you browse our website and also allows us to improve our site.'
            },
            {
                'title': 'Changes to This Policy',
                'content': f"We may update this privacy policy from time to time. We will notify you of any changes by posting the new privacy policy on this page. You are advised to review this privacy policy periodically for any changes."
            },
            {
                'title': 'Contact Us',
                'content': f"If you have any questions about this privacy policy or our privacy practices, please contact us at {context['company_email']}."
            }
        ]
        return context


class TermsView(TemplateView):
    template_name = 'store/terms.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Terms & Conditions - Angel\'s Plant Shop'
        context['last_updated'] = 'May 14, 2025'
        
        # Sample terms content - you might want to move this to a model or markdown file
        context['sections'] = [
            {
                'title': 'Introduction',
                'content': 'Welcome to Angel\'s Plant Shop. These terms and conditions outline the rules and regulations for the use of our website.'
            },
            {
                'title': 'Intellectual Property',
                'content': 'The content, layout, design, data, and graphics on this website are protected by intellectual property laws and are owned by Angel\'s Plant Shop unless otherwise stated.'
            },
            {
                'title': 'Use of the Website',
                'content': 'By accessing this website, you agree to use it only for lawful purposes and in a way that does not infringe the rights of, restrict, or inhibit anyone else\'s use and enjoyment of the website.'
            },
            {
                'title': 'Product Information',
                'content': 'We make every effort to display our products as accurately as possible. However, the actual colors and specifications you see will depend on your computer monitor and we cannot guarantee that your monitor\'s display will be accurate.'
            },
            {
                'title': 'Pricing and Payment',
                'content': 'All prices are listed in USD and are subject to change without notice. We reserve the right to modify or discontinue any product at any time.'
            },
            {
                'title': 'Shipping and Delivery',
                'content': 'We aim to process and ship all orders within 1-3 business days. Delivery times may vary depending on your location and the shipping method selected.'
            },
            {
                'title': 'Returns and Refunds',
                'content': 'Please refer to our Returns Policy for information about returning products and requesting refunds.'
            },
            {
                'title': 'Limitation of Liability',
                'content': 'Angel\'s Plant Shop will not be liable for any damages of any kind arising from the use of this website or from any products purchased through this website.'
            },
            {
                'title': 'Changes to Terms',
                'content': 'We reserve the right to modify these terms at any time. Your continued use of the website following any changes constitutes your acceptance of the new terms.'
            },
            {
                'title': 'Governing Law',
                'content': 'These terms and conditions are governed by and construed in accordance with the laws of the state where our business is registered.'
            }
        ]
        return context


class FAQView(TemplateView):
    template_name = 'store/faq.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Frequently Asked Questions - Angel\'s Plant Shop'
        
        # Sample FAQ data - you can move this to a model in the future
        context['faqs'] = [
            {
                'question': 'How often should I water my plants?',
                'answer': 'The watering frequency depends on the plant type, but most houseplants need watering when the top inch of soil feels dry to the touch.'
            },
            {
                'question': 'What kind of light do my plants need?',
                'answer': 'Different plants have different light requirements. Most houseplants prefer bright, indirect light, while some can tolerate low light conditions.'
            },
            {
                'question': 'How do I know if my plant is getting too much sun?',
                'answer': 'Signs of too much sun include scorched or bleached leaves, brown crispy edges, or leaves that curl and dry out.'
            },
            {
                'question': 'What should I do if my plant has pests?',
                'answer': 'Isolate the affected plant, identify the pest, and treat it with appropriate organic or chemical controls. Neem oil is a good general-purpose treatment.'
            },
            {
                'question': 'How often should I fertilize my plants?',
                'answer': 'Most houseplants benefit from monthly fertilization during the growing season (spring and summer) and less frequently during fall and winter.'
            },
            {
                'question': 'What is your return policy?',
                'answer': 'We accept returns within 14 days of delivery for store credit. Plants must be in their original condition with receipt.'
            },
            {
                'question': 'Do you offer international shipping?',
                'answer': 'Currently, we only ship within the United States due to agricultural restrictions.'
            },
        ]
        return context


class WishlistView(LoginRequiredMixin, ListView):
    """
    View to display user's wishlist.
    """
    model = Wishlist
    template_name = 'store/wishlist.html'
    context_object_name = 'wishlist_items'
    paginate_by = 10
    
    def get_queryset(self):
        return Wishlist.objects.filter(
            user=self.request.user
        ).select_related('product')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional context data here if needed
        return context


class ContactThanksView(TemplateView):
    template_name = 'store/contact_thanks.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Message Sent'
        return context


class ProductListView(ListView):
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        # Get all active products that are in stock
        queryset = Product.objects.filter(is_active=True, quantity__gt=0).select_related('category').prefetch_related('tags')
        
        # Filter by category if category_slug is provided in URL
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
            print(f"Filtered by category '{category.name}': {queryset.count()} products")
        
        # Apply search query if present
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(short_description__icontains=search_query) |
                Q(tags__name__icontains=search_query)
            ).distinct()
            print(f"After search for '{search_query}': {queryset.count()} products")
        
        # Apply sorting
        sort_by = self.request.GET.get('sort_by', 'newest')
        sort_mapping = {
            'price_asc': 'price',
            'price_desc': '-price',
            'name_asc': 'name',
            'name_desc': '-name',
            'newest': '-created_at',
            'created_at': '-created_at'
        }
        
        order_field = sort_mapping.get(sort_by, '-created_at')
        queryset = queryset.order_by(order_field)
        
        # Debug info
        print(f"\n=== DEBUG: Product List Query ===")
        print(f"Total products in stock: {queryset.count()}")
        if queryset.exists():
            print(f"Sample product: {queryset[0].name} (ID: {queryset[0].id}, Stock: {queryset[0].quantity})")
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categories = Category.objects.all()
        products = self.get_queryset()
        
        # Initialize filterset
        self.filterset = ProductFilter(self.request.GET, queryset=products)
        products = self.filterset.qs
        
        # Get current category if in category view
        category_slug = self.kwargs.get('category_slug')
        current_category = None
        if category_slug:
            current_category = get_object_or_404(Category, slug=category_slug)
            context['category'] = current_category
            context['category_slug'] = category_slug
        
        # Debug output
        print("\n=== DEBUG: ProductListView ===")
        print(f"Categories found: {categories.count()}")
        print(f"Current category: {current_category}" if current_category else "No category filter")
        print(f"Products found: {products.count()}")
        if products.exists():
            print(f"First product: {products[0].name} (ID: {products[0].id}, Stock: {products[0].quantity})")
        
        context['categories'] = categories
        context['featured_products'] = Product.objects.filter(is_featured=True, is_active=True, quantity__gt=0)[:4]
        context['bestsellers'] = Product.objects.filter(is_bestseller=True, is_active=True, quantity__gt=0)[:4]
        context['filter'] = self.filterset
        
        # Add filter parameters to pagination
        get_copy = self.request.GET.copy()
        params = get_copy.pop('page', True) and get_copy.urlencode()
        context['params'] = params
        
        # Add current sorting parameter
        context['current_sort'] = self.request.GET.get('sort_by', 'newest')
        
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('category').prefetch_related('product_images')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        # Get related products (same category, excluding current product)
        related_products = Product.objects.filter(
            category=product.category,
            is_active=True
        ).exclude(id=product.id)[:4]
        
        # Get recently viewed products from session
        recently_viewed = []
        if 'recently_viewed' in self.request.session:
            # Get product IDs from session, excluding current product
            product_ids = [pid for pid in self.request.session['recently_viewed'] if pid != product.id]
            # Get products and maintain order
            recently_viewed = list(Product.objects.filter(id__in=product_ids[:4]))
            # Sort to maintain the order from the session
            recently_viewed.sort(key=lambda x: product_ids.index(x.id))
        
        # Check if product is in user's wishlist
        in_wishlist = False
        if self.request.user.is_authenticated:
            in_wishlist = Wishlist.objects.filter(
                user=self.request.user, 
                product=product
            ).exists()
            
        context.update({
            'related_products': related_products,
            'recently_viewed': recently_viewed,
            'meta_title': product.meta_title or f"{product.name} | Angel's Plant Shop",
            'meta_description': product.meta_description or product.short_description,
            'in_wishlist': in_wishlist,
        })
        
        # Add current product to recently viewed
        self.update_recently_viewed(product.id)
        
        return context
    
    def update_recently_viewed(self, product_id):
        """Update the recently viewed products in the session"""
        if 'recently_viewed' in self.request.session:
            # Remove if product already exists in the list
            if product_id in self.request.session['recently_viewed']:
                self.request.session['recently_viewed'].remove(product_id)
            # Add to the beginning of the list
            self.request.session['recently_viewed'].insert(0, product_id)
            # Keep only the last 5 viewed items
            if len(self.request.session['recently_viewed']) > 5:
                self.request.session['recently_viewed'] = self.request.session['recently_viewed'][:5]
        else:
            self.request.session['recently_viewed'] = [product_id]
            
        self.request.session.modified = True


class CartView(LoginRequiredMixin, View):
    # Constants for cart calculations
    TAX_RATE = Decimal('0.18')  # 18% tax rate
    SHIPPING_COST = Decimal('5.00')  # Flat rate shipping cost
    
    def get(self, request, *args, **kwargs):
        logger.debug(f"[CartView] Loading cart for user {request.user.id}")
        
        try:
            # Get or create cart with proper locking
            with transaction.atomic():
                cart, created = Cart.objects.select_for_update().get_or_create(
                    user=request.user, 
                    status='active', 
                    defaults={'status': 'active'}
                )
                
                logger.debug(f"[CartView] Cart ID: {cart.id}, Created: {created}")
                
                # Get all items with related product data
                all_items = list(cart.items.select_related('product').filter(product__isnull=False))
                logger.debug(f"[CartView] Found {len(all_items)} items in cart")
                
                active_items = []
                inactive_items = []
                
                # Process each cart item
                for item in all_items:
                    try:
                        logger.debug(
                            f"[CartView] Processing item {item.id}: {item.product.name if item.product else 'No product'}, "
                            f"Qty: {item.quantity}, "
                            f"Active: {getattr(item.product, 'is_active', 'N/A')}, "
                            f"In Stock: {getattr(item.product, 'quantity', 'N/A')}, "
                            f"Track Qty: {getattr(item.product, 'track_quantity', 'N/A')}"
                        )
                        
                        # Check if product exists and is active
                        if not item.product:
                            logger.warning(f"[CartView] Item {item.id} has no associated product")
                            inactive_items.append(item)
                            continue
                            
                        # Refresh product data
                        item.product.refresh_from_db()
                        
                        if not item.product.is_active:
                            logger.debug(f"[CartView] Product {item.product.id} is not active")
                            inactive_items.append(item)
                            continue
                            
                        # Check stock if tracking is enabled
                        if item.product.track_quantity:
                            if item.quantity > item.product.quantity:
                                if item.product.quantity > 0:
                                    # Reduce quantity to available stock
                                    old_qty = item.quantity
                                    item.quantity = item.product.quantity
                                    item.save(update_fields=['quantity', 'updated_at'])
                                    
                                    logger.info(f"[CartView] Reduced quantity of {item.product.name} from {old_qty} to {item.quantity}")
                                    messages.warning(
                                        request, 
                                        f"Reduced quantity of '{item.product.name}' to available stock ({item.product.quantity}).",
                                        extra_tags='cart_warning'
                                    )
                                    active_items.append(item)
                                else:
                                    # Out of stock
                                    logger.info(f"[CartView] Product {item.product.id} is out of stock")
                                    inactive_items.append(item)
                                    messages.warning(
                                        request, 
                                        f"The product '{item.product.name}' is out of stock and has been removed from your cart.",
                                        extra_tags='cart_warning'
                                    )
                            else:
                                # Sufficient stock
                                active_items.append(item)
                        else:
                            # Product doesn't track quantity
                            active_items.append(item)
                            
                    except Exception as e:
                        logger.error(f"[CartView] Error processing cart item {item.id}: {str(e)}", exc_info=True)
                        inactive_items.append(item)
            
            # Remove inactive items
            if inactive_items:
                inactive_count = len(inactive_items)
                inactive_names = ", ".join([f"'{item.product.name}'" for item in inactive_items if item.product])
                logger.info(f"[CartView] Removing {inactive_count} inactive items: {inactive_names}")
            for item in inactive_items:
                product_name = getattr(item.product, 'name', 'Unknown Product')
                print(f"[WARNING] Cart {cart.id} has an inactive/out-of-stock product: {product_name} (Product ID: {getattr(item.product, 'id', 'N/A')})")
                
                if not hasattr(request, '_dont_show_unavailable_message'):
                    messages.warning(
                        request,
                        f"The product '{product_name}' is no longer available and has been removed from your cart.",
                        extra_tags='cart_warning'
                    )
                
                # Delete the item
                item.delete()
            
            # Update cart totals after removing items
            cart.update_totals()
            
            # Use only active items for the rest of the view
            items = active_items
            
            # Calculate total with shipping and tax
            tax = (cart.total * self.TAX_RATE).quantize(Decimal('0.00'))
            total_with_shipping = (cart.total + self.SHIPPING_COST + tax).quantize(Decimal('0.00'))
            
            # Prepare context with all necessary data
            context = {
                'cart': cart,
                'items': items,  # Only include items with active products
                'shipping_cost': self.SHIPPING_COST.quantize(Decimal('0.00')),
                'tax': tax,
                'total_with_shipping': total_with_shipping,
                'is_cart_empty': len(items) == 0,  # Check if there are any items
                'tax_rate': int(self.TAX_RATE * 100)  # For display purposes (e.g., '18%')
            }
            
            print(f"[DEBUG] CartView - Rendering template with {len(items)} items")
            return render(request, 'store/cart.html', context)
            
        except Exception as e:
            error_msg = f"Error in CartView: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            
            # Return empty cart context if there's an error
            context = {
                'cart': None,
                'items': [],
                'shipping_cost': Decimal('0.00'),
                'tax': Decimal('0.00'),
                'total_with_shipping': Decimal('0.00'),
                'is_cart_empty': True,
                'error': 'An error occurred while loading your cart.'
            }
            return render(request, 'store/cart.html', context)

class AddToCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        product = get_object_or_404(Product, id=product_id, available=True)
        
        # Check if there's enough stock
        if product.stock < quantity:
            messages.error(request, f"Sorry, only {product.stock} units of {product.name} are available.")
            return redirect('store:product_detail', slug=product.slug)
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'status': 'active'}
        )
        
        # Get or create order
        order, created = Order.objects.get_or_create(
            user=request.user,
            payment_status__exact=False,
            defaults={
                'status': 'pending',
                'payment_status': False,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'address': '',  # Empty address for now
                'city': '',
                'state': '',
                'postal_code': '',
                'country': 'India',
                'payment_method': 'cash_on_delivery'
            }
        )
        
        # Create payment record if it doesn't exist
        if not hasattr(order, 'payment'):
            Payment.objects.create(
                order=order,
                payment_id=f'PAY-{order.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}',
                payment_method='pending',
                amount=0,  # Will be updated when checkout is complete
                status='pending'
            )
        
        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'price': product.price,
                'quantity': quantity
            }
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > product.stock:
                messages.error(request, f"You can't add more than {product.stock} units of {product.name} to your cart.")
                return redirect('store:cart')
                
            cart_item.increase_quantity(quantity)  # Use our custom method that updates price and total
            messages.success(request, f"Updated {product.name} quantity in your cart!")
        else:
            messages.success(request, f"{product.name} added to your cart!")
        
        # Create or update order item
        order_item, created = OrderItem.objects.get_or_create(
            order=order,
            product=product,
            defaults={
                'price': product.price,
                'quantity': quantity
            }
        )
        
        if not created:
            order_item.quantity += quantity
            order_item.save()
            
        # Update order total
        order.get_total_cost()
        
        # Update order total
        order.get_total_cost()
        
        # Redirect to the previous page or cart
        next_url = request.POST.get('next', None)
        if next_url:
            return redirect(next_url)
            
        return redirect('store:cart')

class RemoveFromCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        product_id = kwargs.get('product_id')
        cart = get_object_or_404(Cart, user=request.user, status='active')
        
        try:
            item = cart.items.get(product_id=product_id)
            product_name = item.product.name
            item.delete()
            
            messages.success(request, f"{product_name} removed from your cart!")
            return redirect('store:cart')
        except CartItem.DoesNotExist:
            messages.error(request, "Item not found in cart")
            return redirect('store:cart')

class CheckoutSuccessView(LoginRequiredMixin, View):
    """
    View to display order confirmation after successful checkout.
    Optimized for performance with select_related and prefetch_related.
    """
    def get(self, request, *args, **kwargs):
        order_number = kwargs.get('order_number')
        
        # Clean the order number in case it contains any extra characters
        order_number = order_number.strip()
        
        # Optimize database queries
        try:
            order = Order.objects.select_related(
                'user',
                'cart'
            ).prefetch_related(
                'items',
                'items__product',
                'items__product__category',
                'items__product__product_images'  # Changed from 'images' to 'product_images'
            ).get(
                order_number=order_number, 
                user=request.user
            )
            
            # Clear the cart in the background using a task or async operation
            self._clear_cart_async(request.user)
            
            # Get the most recent payment for this order
            payment = Payment.objects.filter(
                order=order,
                status='completed'
            ).order_by('-created_at').first()
            
            context = {
                'order': order,
                'payment': payment,
                'order_items': order.items.all(),
                'order_items_count': order.items.count(),
            }
            
            # Add payment to context
            context.update({
                'payment': payment,
                'shipping_cost': Decimal('99.00'),  # Flat rate for India
                'tax': (order.total_amount * Decimal('0.18')).quantize(Decimal('0.01')),  # 18% GST
                'total_with_shipping': order.total_amount,
            })
            
            # Add cache control headers
            response = render(request, 'store/order_confirmation.html', context)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response
            
        except Order.DoesNotExist:
            messages.error(request, "Order not found.")
            return redirect('store:cart')
    
    def _clear_cart_async(self, user):
        """Clear cart asynchronously to not block the response"""
        from django.db import transaction
        from django.db.models import F
        
        def clear_cart():
            try:
                with transaction.atomic():
                    # Use update with F() to avoid race conditions
                    Cart.objects.filter(
                        user=user, 
                        status='active'
                    ).update(status='completed')
                    
                    # Delete cart items in bulk
                    CartItem.objects.filter(cart__user=user, cart__status='active').delete()
                    
            except Exception as e:
                # Log the error but don't fail the request
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error clearing cart for user {user.id}: {str(e)}")
        
        # Run in a separate thread to not block the response
        import threading
        thread = threading.Thread(target=clear_cart)
        thread.daemon = True
        thread.start()

class ClearCartView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            cart = Cart.objects.get(user=request.user, status='active')
            cart.items.all().delete()
            messages.success(request, "Your cart has been cleared!")
            return redirect('store:cart')
        except Cart.DoesNotExist:
            messages.info(request, "Your cart is already empty.")
            return redirect('store:cart')

class CheckoutView(LoginRequiredMixin, View):
    login_url = '/accounts/login/'
    redirect_field_name = 'next'
    
    def process_cart_items(self, cart):
        """Process cart items and return active and inactive items."""
        try:
            # Get all cart items with product information and lock them for update
            with transaction.atomic():
                all_cart_items = list(cart.items.select_related('product')
                    .select_for_update()
                    .filter(product__isnull=False))
            
            # Debug: Log all cart items and their active status
            logger.debug(f"[Checkout] Processing cart {cart.id} with {len(all_cart_items)} items")
            
            # Filter for active products with sufficient stock
            active_cart_items = []
            inactive_items = []
            
            with transaction.atomic():
                for item in all_cart_items:
                    try:
                        # Log item details before processing
                        item_debug = (
                            f"[Cart Item {item.id}] Product: {item.product.name if item.product else 'None'}, "
                            f"Active: {getattr(item.product, 'is_active', 'N/A')}, "
                            f"Quantity: {item.quantity}, "
                            f"In Stock: {getattr(item.product, 'quantity', 'N/A')}, "
                            f"Track Qty: {getattr(item.product, 'track_quantity', 'N/A')}"
                        )
                        logger.debug(item_debug)
                        
                        # Check if product exists and is active
                        if not item.product:
                            logger.debug(f"[Cart Item {item.id}] No product associated")
                            inactive_items.append(item)
                            continue
                            
                        # Refresh the product to get the latest stock
                        item.product.refresh_from_db()
                        
                        if not item.product.is_active:
                            logger.debug(f"[Cart Item {item.id}] Product is not active")
                            inactive_items.append(item)
                            continue
                            
                        # Check stock if tracking is enabled
                        if item.product.track_quantity:
                            if item.quantity > item.product.quantity:
                                if item.product.quantity > 0:
                                    # Reduce quantity to available stock
                                    old_qty = item.quantity
                                    item.quantity = item.product.quantity
                                    item.save(update_fields=['quantity', 'updated_at'])
                                    
                                    logger.debug(f"[Cart Item {item.id}] Reduced quantity from {old_qty} to {item.quantity}")
                                    messages.warning(
                                        self.request,
                                        f"Reduced quantity of '{item.product.name}' to available stock ({item.product.quantity}).",
                                        extra_tags='cart_warning'
                                    )
                                    active_cart_items.append(item)
                                else:
                                    # Product is out of stock
                                    logger.debug(f"[Cart Item {item.id}] Product is out of stock")
                                    inactive_items.append(item)
                                    messages.warning(
                                        self.request,
                                        f"'{item.product.name}' is out of stock and has been removed from your cart.",
                                        extra_tags='cart_warning'
                                    )
                            else:
                                # Sufficient stock available
                                logger.debug(f"[Cart Item {item.id}] Sufficient stock available")
                                active_cart_items.append(item)
                        else:
                            # Product doesn't track quantity
                            logger.debug(f"[Cart Item {item.id}] Product doesn't track quantity")
                            active_cart_items.append(item)
                            
                    except Exception as e:
                        logger.error(f"Error processing cart item {item.id}: {str(e)}", exc_info=True)
                        inactive_items.append(item)
            
            # Remove inactive items from cart
            if inactive_items:
                inactive_count = len(inactive_items)
                inactive_names = ", ".join([f"'{item.product.name}'" for item in inactive_items if item.product])
                messages.warning(
                    self.request, 
                    f"Removed {inactive_count} inactive items from cart: {inactive_names}",
                    extra_tags='cart_warning'
                )
                CartItem.objects.filter(id__in=[item.id for item in inactive_items]).delete()
            
            return active_cart_items, inactive_items
            
        except Exception as e:
            logger.error(f"Error processing cart items: {str(e)}", exc_info=True)
            return [], []
    def get(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Lock the cart to prevent race conditions
                cart = Cart.objects.select_for_update().filter(
                    user=request.user, 
                    status='active'
                ).first()
                
                if not cart:
                    messages.error(request, "No active cart found. Please add some products to your cart first.")
                    return redirect('store:cart')
                
                # Process cart items and get active/inactive items
                active_cart_items, inactive_items = self.process_cart_items(cart)
                
                if not active_cart_items:
                    messages.error(
                        request,
                        "Your cart contains no active products. "
                        "Please add some products before checking out.",
                        extra_tags='cart_error'
                    )
                    return redirect('store:cart')
                
                # Calculate order total from active cart items
                order_total = sum(item.total_price for item in active_cart_items)
                
                # Create or update order
                order, created = Order.objects.update_or_create(
                    user=request.user,
                    status='pending',
                    payment_status=False,
                    cart=cart,
                    defaults={
                        'first_name': request.user.first_name or '',
                        'last_name': request.user.last_name or '',
                        'email': request.user.email,
                        'phone': getattr(request.user.profile, 'phone', ''),
                        'total_amount': order_total
                    }
                )
                
                # Clear existing order items
                order.items.all().delete()
                
                # Create order items from active cart items
                for cart_item in active_cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        price=cart_item.price,
                        quantity=cart_item.quantity
                    )
                
                # Update product quantities if tracking is enabled
                for cart_item in active_cart_items:
                    if cart_item.product.track_quantity:
                        cart_item.product.quantity -= cart_item.quantity
                        cart_item.product.save(update_fields=['quantity', 'updated_at'])
                
                # Clear the cart after successful order creation
                cart.items.all().delete()
                cart.update_totals()
                
                # Create payment record
                payment, _ = Payment.objects.update_or_create(
                    order=order,
                    defaults={
                        'payment_id': f'PAY-{order.id}-{timezone.now().strftime("%Y%m%d%H%M%S")}',
                        'payment_method': 'pending',
                        'amount': order.total_amount,
                        'status': 'pending'
                    }
                )
                
                # Calculate values for display in template
                display_shipping_cost = Decimal('99.00')  # Flat rate for India
                display_tax_rate = Decimal('0.18')  # 18% GST
                display_tax = (order.total_amount * display_tax_rate).quantize(Decimal('0.01'))
                display_total = (order.total_amount + display_shipping_cost + display_tax).quantize(Decimal('0.01'))
                
                # Update order total (including shipping and tax)
                order.total_amount = display_total
                order.save(update_fields=['total_amount', 'updated_at'])
                
                context = {
                    'order': order,
                    'cart': cart,
                    'shipping_cost': display_shipping_cost,
                    'tax': display_tax,
                    'total_with_shipping': display_total,
                    'payment': payment,
                    'razorpay_key': settings.RAZORPAY_KEY_ID,
                    'razorpay_amount': int(display_total * 100),  # Convert to paise
                    'razorpay_currency': 'INR',
                    'razorpay_order_id': f'order_{order.id}_{int(time.time())}',
                    'razorpay_name': 'Angel Plants',
                    'razorpay_description': f'Order #{order.id}',
                    'razorpay_prefill': {
                        'name': f"{order.first_name} {order.last_name}".strip(),
                        'email': order.email,
                        'contact': order.phone or ''
                    },
                    'theme': {
                        'color': '#3399cc'
                    }
                }
                
                return render(request, 'store/checkout.html', context)
                
        except Exception as e:
            logger.error(f"Error during checkout: {str(e)}", exc_info=True)
            messages.error(
                request,
                "An error occurred while processing your order. Please try again.",
                extra_tags='error'
            )
            return redirect('store:cart')
    
    def post(self, request, *args, **kwargs):
        try:
            # Get the order
            order = Order.objects.filter(
                user=request.user,
                payment_status=False,
                status='pending'
            ).first()
            
            if not order:
                error_details = {
                    'error_type': 'OrderNotFound',
                    'message': 'No active order found for the user'
                }
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'No active order found. Please add items to your cart first.',
                        'error_details': error_details
                    }, status=400)
                messages.error(request, "No active order found. Please add items to your cart first.")
                return redirect('store:cart')
            
            if order.items.count() == 0:
                error_details = {
                    'error_type': 'EmptyOrder',
                    'message': 'Order has no items'
                }
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Your cart is empty. Add some products before checking out.',
                        'error_details': error_details
                    }, status=400)
                messages.error(request, "Your cart is empty. Add some products before checking out.")
                return redirect('store:cart')
            
            # Validate required fields
            required_fields = ['first_name', 'last_name', 'email', 'address', 'district', 'postal_code', 'phone', 'payment_method']
            missing_fields = [field for field in required_fields if not request.POST.get(field)]
            
            if missing_fields:
                error_details = {
                    'error_type': 'ValidationError',
                    'message': 'Missing required fields',
                    'missing_fields': missing_fields
                }
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f"Please fill in all required fields: {', '.join(missing_fields)}",
                        'error_details': error_details
                    }, status=400)
                messages.error(request, f"Please fill in all required fields: {', '.join(missing_fields)}")
                return redirect('store:checkout')
            
            # Validate phone number
            phone = request.POST.get('phone', '')
            if not phone.isdigit() or len(phone) != 10:
                error_details = {
                    'error_type': 'ValidationError',
                    'message': 'Invalid phone number',
                    'phone': phone
                }
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Please enter a valid 10-digit phone number',
                        'error_details': error_details
                    }, status=400)
                messages.error(request, 'Please enter a valid 10-digit phone number')
                return redirect('store:checkout')
            
            # Update order details from form data
            order.first_name = request.POST.get('first_name', '')
            order.last_name = request.POST.get('last_name', '')
            order.email = request.POST.get('email', '')
            order.address = request.POST.get('address', '')
            order.address2 = request.POST.get('address2', '')
            order.district = request.POST.get('district', '')
            order.city = request.POST.get('district', '')  # Using district as city
            order.state = request.POST.get('state', 'Kerala')
            order.postal_code = request.POST.get('postal_code', '')
            order.country = request.POST.get('country', 'India')
            order.phone = request.POST.get('phone', '')
            order.payment_method = request.POST.get('payment_method', 'cash_on_delivery')
            
            # Save the updated order
            order.save()
            
            # Process payment based on payment method
            if order.payment_method == 'cash_on_delivery':
                # For cash on delivery, just update the order status
                order.payment_status = True
                order.status = 'pending'
                order.save()
                
                # Update product quantity
                for item in order.items.all():
                    product = item.product
                    if product.quantity >= item.quantity:  # Check if enough stock is available
                        product.quantity -= item.quantity
                        product.save()
                    else:
                        # Handle case where there's not enough stock
                        logger.warning(f"Not enough stock for product {product.id}. Available: {product.quantity}, Requested: {item.quantity}")
                        messages.warning(request, f"Not enough stock for {product.name}. Only {product.quantity} available.")
                        return redirect('store:cart')
                
                # Clear the cart
                cart = Cart.objects.filter(user=request.user, status='active').first()
                if cart:
                    cart.status = 'completed'
                    cart.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('store:checkout_success', kwargs={'order_number': order.order_number})
                    })
                
                messages.success(request, "Your order has been placed successfully!")
                return redirect('store:checkout_success', order_number=order.order_number)
                
            elif order.payment_method == 'razorpay':
                try:
                    # Initialize Razorpay client
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    
                    # Convert amount to paise (Razorpay expects amount in smallest currency unit)
                    amount = int(order.total_amount * 100)
                    
                    # Create Razorpay order
                    razorpay_order = client.order.create({
                        'amount': amount,
                        'currency': 'INR',
                        'receipt': f'order_{order.id}',
                        'payment_capture': 1  # Auto-capture payment
                    })
                    
                    # Update order with Razorpay order ID
                    order.razorpay_order_id = razorpay_order['id']
                    order.save()
                    
                    # Return Razorpay order details to frontend
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'order_number': order.order_number,
                            'order_id': order.id,
                            'redirect_url': reverse('store:checkout_success', kwargs={'order_number': order.order_number}),
                            'razorpay': {
                                'key_id': settings.RAZORPAY_KEY_ID,
                                'order_id': razorpay_order['id'],
                                'amount': razorpay_order['amount'],
                                'currency': razorpay_order['currency'],
                                'name': "Angel's Plant Shop",
                                'description': f'Order #{order.order_number}'
                            }
                        })
                    
                    return redirect('store:checkout_success', order_number=order.order_number)
                    
                except Exception as e:
                    logger.error(f"Razorpay order creation failed: {str(e)}", exc_info=True)
                    error_details = {
                        'error_type': 'RazorpayError',
                        'message': str(e),
                        'traceback': traceback.format_exc()
                    }
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'message': 'An error occurred while processing your payment. Please try again.',
                            'error_details': error_details
                        }, status=400)
                    
                    messages.error(request, 'An error occurred while processing your payment. Please try again.')
                    return redirect('store:checkout')
            
        except Exception as e:
            logger.error(f"Error in checkout POST: {str(e)}", exc_info=True)
            error_details = {
                'error_type': type(e).__name__,
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'An error occurred while processing your order. Please try again.',
                    'error_details': error_details
                }, status=500)
            
            messages.error(request, 'An error occurred while processing your order. Please try again.')
            return redirect('store:checkout')


        
        # Calculate shipping cost and tax for the confirmation page
        shipping_cost = Decimal('5.99')
        tax_rate = Decimal('0.08')  # 8% tax rate
        tax = order.total_amount * tax_rate
        
        # Get categories from ordered items
        ordered_categories = order.items.values_list('product__category', flat=True).distinct()
        
        # Get related products (products from the same categories as ordered items)
        related_products = Product.objects.filter(
            category__in=ordered_categories,
            is_active=True
        ).exclude(
            id__in=order.items.values_list('product_id', flat=True)
        ).distinct().order_by('?')[:8]  # Get 8 random related products
        
        # If not enough related products, get some random products
        if related_products.count() < 4:
            additional_products = Product.objects.filter(
                is_active=True
            ).exclude(
                id__in=order.items.values_list('product_id', flat=True)
            ).exclude(
                id__in=related_products.values_list('id', flat=True)
            ).order_by('?')[:8 - related_products.count()]
            related_products = list(related_products) + list(additional_products)
        
        context = {
            'order': order,
            'shipping_cost': shipping_cost,
            'tax': tax.quantize(Decimal('0.01')),
            'total_with_shipping': (order.total_amount + shipping_cost + tax).quantize(Decimal('0.01')),
            'related_products': related_products[:8],  # Ensure we don't return more than 8 products
        }
        
        return render(request, 'store/order_confirmation.html', context)


class StaffProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View for staff to delete products
    """
    model = Product
    template_name = 'store/staff/product_confirm_delete.html'
    context_object_name = 'product'
    success_url = reverse_lazy('store:staff_product_list')
    pk_url_kwarg = 'pk'
    
    def test_func(self):
        """Only staff members can access this view"""
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Delete Product')
        return context
    
    def delete(self, request, *args, **kwargs):
        """Handle successful deletion"""
        response = super().delete(request, *args, **kwargs)
        messages.success(self.request, _('Product has been deleted successfully.'))
        return response
    
    def handle_no_permission(self):
        """Redirect to login page if user doesn't have permission"""
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, _('You do not have permission to access this page.'))
        return redirect('store:home')


class StaffProductUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for staff to update existing products
    """
    model = Product
    form_class = ProductForm
    template_name = 'store/staff/product_form.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'product'
    
    def test_func(self):
        """Only staff members can access this view"""
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Product')
        context['form_action'] = 'edit'
        return context
    
    def get_success_url(self):
        """Redirect to product list with success message"""
        messages.success(self.request, _('Product has been updated successfully.'))
        return reverse_lazy('store:staff_product_edit', kwargs={'pk': self.object.pk})
    
    def handle_no_permission(self):
        """Redirect to login page if user doesn't have permission"""
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, _('You do not have permission to access this page.'))
        return redirect('store:home')


class StaffProductCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for staff to create new products
    """
    model = Product
    form_class = ProductForm
    template_name = 'store/staff/product_form.html'
    success_url = reverse_lazy('store:staff_product_list')
    
    def test_func(self):
        """Only staff members can access this view"""
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Add New Product')
        context['form_action'] = 'add'
        return context
    
    def form_valid(self, form):
        """Set the created_by field to the current user"""
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, _('Product has been created successfully.'))
        return response
    
    def handle_no_permission(self):
        """Redirect to login page if user doesn't have permission"""
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, _('You do not have permission to access this page.'))
        return redirect('store:home')


class StaffProductListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View for staff to list all products with management options
    """
    model = Product
    template_name = 'store/staff/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def test_func(self):
        """Only staff members can access this view"""
        return self.request.user.is_staff
    
    def get_queryset(self):
        """Return the list of products with related data"""
        queryset = Product.objects.all().select_related('category').prefetch_related('images', 'tags')
        
        # Handle search query
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(sku__iexact=query) |
                Q(category__name__icontains=query)
            )
        
        # Handle category filter
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Handle status filter
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Handle sort
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['name', 'price', 'stock', 'created_at']:
            queryset = queryset.order_by(sort_by)
        elif sort_by == '-name':
            queryset = queryset.order_by(Lower('name').desc())
        elif sort_by == 'name':
            queryset = queryset.order_by(Lower('name'))
        else:
            queryset = queryset.order_by('-created_at')
            
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Manage Products')
        context['categories'] = Category.objects.all()
        context['total_products'] = Product.objects.count()
        context['active_products'] = Product.objects.filter(is_active=True).count()
        context['low_stock_products'] = Product.objects.filter(stock__lt=F('stock_alert_threshold')).count()
        
        # Add filter parameters to context for template
        context['current_query'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        return context
    
    def handle_no_permission(self):
        """Redirect to login page if user doesn't have permission"""
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, _('You do not have permission to access this page.'))
        return redirect('store:home')


class BlogPostListView(ListView):
    """
    View for displaying a list of blog posts
    """
    model = BlogPost
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = BlogPost.objects.filter(
            status=BlogPost.PUBLISHED,
            publish_date__lte=timezone.now()
        ).select_related('author').prefetch_related('categories', 'tags')
        
        # Filter by category slug if provided
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
            
        # Filter by tag slug if provided
        tag_slug = self.kwargs.get('tag_slug')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
            
        return queryset.order_by('-publish_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add categories for sidebar
        context['categories'] = BlogCategory.objects.filter(is_active=True).annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
        ).filter(post_count__gt=0)
        
        # Add popular tags
        context['popular_tags'] = BlogTag.objects.annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
        ).filter(post_count__gt=0).order_by('-post_count')[:10]
        
        # Add archive dates
        context['archive_dates'] = BlogPost.objects.filter(
            status=BlogPost.PUBLISHED
        ).dates('publish_date', 'month', order='DESC')
        
        # Add current filters
        context['current_category'] = self.kwargs.get('category_slug')
        context['current_tag'] = self.kwargs.get('tag_slug')
        
        return context


class BlogPostDetailView(DetailView):
    """
    View for displaying a single blog post
    """
    model = BlogPost
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    
    def get_queryset(self):
        return BlogPost.objects.filter(
            status=BlogPost.PUBLISHED,
            publish_date__lte=timezone.now()
        ).select_related('author').prefetch_related('categories', 'tags')
    
    def get_object(self, queryset=None):
        # Get the post based on the URL parameters
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        slug = self.kwargs.get('slug')
        
        try:
            post = get_object_or_404(
                BlogPost,
                publish_date__year=year,
                publish_date__month=month,
                publish_date__day=day,
                slug=slug,
                status=BlogPost.PUBLISHED
            )
            
            # Increment view count
            post.view_count += 1
            post.save(update_fields=['view_count'])
            
            return post
            
        except (ValueError, Http404):
            raise Http404("Post not found")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        # Add related posts (same category)
        related_posts = BlogPost.objects.filter(
            status=BlogPost.PUBLISHED,
            categories__in=post.categories.all(),
            publish_date__lte=timezone.now()
        ).exclude(id=post.id).distinct()[:3]
        
        context.update({
            'related_posts': related_posts,
            'meta_title': post.meta_title or post.title,
            'meta_description': post.meta_description or post.excerpt_text,
            'meta_image': post.featured_image.url if post.featured_image else None,
            'categories': BlogCategory.objects.filter(is_active=True).annotate(
                post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
            ).filter(post_count__gt=0),
            'popular_tags': BlogTag.objects.annotate(
                post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
            ).filter(post_count__gt=0).order_by('-post_count')[:10],
            'archive_dates': BlogPost.objects.filter(
                status=BlogPost.PUBLISHED
            ).dates('publish_date', 'month', order='DESC'),
        })
        
        return context


class BlogCategoryView(BlogPostListView):
    """
    View for displaying blog posts filtered by category
    """
    def get_queryset(self):
        self.category = get_object_or_404(BlogCategory, slug=self.kwargs['category_slug'])
        return super().get_queryset().filter(categories=self.category)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class BlogTagView(BlogPostListView):
    """
    View for displaying blog posts filtered by tag
    """
    def get_queryset(self):
        self.tag = get_object_or_404(BlogTag, slug=self.kwargs['tag_slug'])
        return super().get_queryset().filter(tags=self.tag)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


from django.views.generic.dates import YearArchiveView, MonthArchiveView, DayArchiveView

class BlogYearArchiveView(YearArchiveView):
    """
    View for displaying blog posts filtered by year
    """
    queryset = BlogPost.objects.filter(status=BlogPost.PUBLISHED, publish_date__lte=timezone.now())
    date_field = 'publish_date'
    make_object_list = True
    allow_future = False
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        return super().get_queryset().select_related('author').prefetch_related('categories', 'tags')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Archive: {self.get_year()}"
        
        # Add sidebar data
        self._add_sidebar_context(context)
        return context
    
    def _add_sidebar_context(self, context):
        """Helper method to add sidebar context"""
        # Add categories for sidebar
        context['categories'] = BlogCategory.objects.filter(is_active=True).annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
        ).filter(post_count__gt=0)
        
        # Add popular tags
        context['popular_tags'] = BlogTag.objects.annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
        ).filter(post_count__gt=0).order_by('-post_count')[:10]
        
        # Add archive dates
        context['archive_dates'] = BlogPost.objects.filter(
            status=BlogPost.PUBLISHED
        ).dates('publish_date', 'month', order='DESC')


class BlogMonthArchiveView(MonthArchiveView):
    """
    View for displaying blog posts filtered by year and month
    """
    queryset = BlogPost.objects.filter(status=BlogPost.PUBLISHED, publish_date__lte=timezone.now())
    date_field = 'publish_date'
    month_format = '%m'  # Format for month in URLs (e.g., '01' for January)
    allow_future = False
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 10
    
    def get_queryset(self):
        return super().get_queryset().select_related('author').prefetch_related('categories', 'tags')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        month_name = self.get_date().strftime("%B %Y")
        context['title'] = f"Archive: {month_name}"
        
        # Add sidebar data
        self._add_sidebar_context(context)
        return context
    
    def _add_sidebar_context(self, context):
        """Helper method to add sidebar context"""
        # Add categories for sidebar
        context['categories'] = BlogCategory.objects.filter(is_active=True).annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
        ).filter(post_count__gt=0)
        
        # Add popular tags
        context['popular_tags'] = BlogTag.objects.annotate(
            post_count=Count('blog_posts', filter=Q(blog_posts__status=BlogPost.PUBLISHED))
        ).filter(post_count__gt=0).order_by('-post_count')[:10]
        
        # Add archive dates
        context['archive_dates'] = BlogPost.objects.filter(
            status=BlogPost.PUBLISHED
        ).dates('publish_date', 'month', order='DESC')
