from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Order, OrderStatusUpdate
from .forms import UpdateOrderStatusForm

class OrderTrackingView(LoginRequiredMixin, DetailView):
    """View for customers to track their order status"""
    model = Order
    template_name = 'store/order_tracking.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        # Users can only see their own orders
        return Order.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_updates'] = self.object.status_updates.all().order_by('-created_at')
        return context


@login_required
def update_order_status(request, order_id):
    """View for admin to update order status and tracking info"""
    if not request.user.is_staff:
        messages.error(request, _("You don't have permission to update order status."))
        return redirect('home')
    
    order = get_object_or_404(Order, pk=order_id)
    
    if request.method == 'POST':
        form = UpdateOrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, _("Order status updated successfully."))
            return redirect('admin:store_order_change', order.id)
    else:
        form = UpdateOrderStatusForm(instance=order)
    
    return render(request, 'admin/store/order/update_status.html', {
        'form': form,
        'order': order,
        'opts': Order._meta,
        'title': _('Update Order Status'),
    })


def public_order_tracking(request, order_number):
    """Public order tracking page (no login required)"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Only show limited information for public tracking
    context = {
        'order': order,
        'status_updates': order.status_updates.all().order_by('-created_at'),
        'show_limited_info': True,
    }
    
    return render(request, 'store/public_order_tracking.html', context)
