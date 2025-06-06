from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from datetime import timedelta

from .models import Order, OrderStatusUpdate, Product
from .forms import UpdateOrderStatusForm


class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin dashboard view showing order statistics and recent orders."""
    template_name = 'store/admin/dashboard.html'
    context_object_name = 'recent_orders'
    paginate_by = 10
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        return Order.objects.all().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        
        # Order statistics
        total_orders = Order.objects.count()
        today_orders = Order.objects.filter(created_at__date=now.date()).count()
        pending_orders = Order.objects.filter(status__in=['pending', 'processing']).count()
        
        # Sales statistics
        total_sales = Order.objects.aggregate(
            total=Sum('total_paid')
        )['total'] or 0
        
        # Order status distribution
        status_distribution = Order.objects.values('status').annotate(
            count=Count('id'),
            percentage=Count('id') * 100 / total_orders if total_orders > 0 else 0
        ).order_by('-count')
        
        # Recent status updates
        recent_updates = OrderStatusUpdate.objects.select_related('order').order_by('-created_at')[:5]
        
        # Low stock products
        low_stock_products = Product.objects.filter(quantity__lt=10).order_by('quantity')[:5]
        
        context.update({
            'total_orders': total_orders,
            'today_orders': today_orders,
            'pending_orders': pending_orders,
            'total_sales': total_sales,
            'status_distribution': status_distribution,
            'recent_updates': recent_updates,
            'low_stock_products': low_stock_products,
        })
        
        return context


class AdminOrderListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin view to list all orders with filtering and search."""
    model = Order
    template_name = 'store/admin/order_list.html'
    context_object_name = 'orders'
    paginate_by = 25
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status and status in dict(Order.Status.choices):
            queryset = queryset.filter(status=status)
            
        # Search by order number, customer name, or email
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(order_number__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
            
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = [('', 'All Status')] + list(Order.Status.choices)
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        return context


class AdminOrderDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Admin view to view order details and update status."""
    model = Order
    template_name = 'store/admin/order_detail.html'
    context_object_name = 'order'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_form'] = UpdateOrderStatusForm(
            instance=self.object,
            initial={
                'status': self.object.status,
                'tracking_number': self.object.tracking_number,
                'tracking_url': self.object.tracking_url,
                'shipping_provider': self.object.shipping_provider,
                'delivery_instructions': self.object.delivery_instructions,
            }
        )
        context['status_updates'] = self.object.status_updates.all().order_by('-created_at')
        return context


class AdminUpdateOrderStatusView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Admin view to update order status and tracking information."""
    model = Order
    form_class = UpdateOrderStatusForm
    template_name = 'store/admin/update_order_status.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_success_url(self):
        return reverse_lazy('admin_order_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        old_status = self.get_object().status
        response = super().form_valid(form)
        new_status = self.object.status
        
        # Create status update if status changed
        if old_status != new_status:
            OrderStatusUpdate.objects.create(
                order=self.object,
                status=new_status,
                note=form.cleaned_data.get('status_note', ''),
                created_by=self.request.user
            )
            
            # Send notification to customer if needed
            self._send_status_notification(old_status, new_status)
            
        messages.success(self.request, _('Order status updated successfully.'))
        return response
    
    def _send_status_notification(self, old_status, new_status):
        """Send notification to customer about status change."""
        # Implement email/SMS notification logic here
        pass


def update_order_status_ajax(request, order_id):
    """AJAX endpoint for quick status updates from the order list."""
    if not request.user.is_staff or not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        order = Order.objects.get(id=order_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(Order.Status.choices):
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Create status update
            OrderStatusUpdate.objects.create(
                order=order,
                status=new_status,
                note=f'Status updated via quick action by {request.user.get_full_name() or request.user.email}',
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'status_display': order.get_status_display(),
                'status_class': order.get_status_class()
            })
            
    except (Order.DoesNotExist, ValueError, KeyError) as e:
        pass
        
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
