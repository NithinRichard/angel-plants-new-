from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.decorators.csrf import requires_csrf_token
from django.template import loader
from django.contrib.auth import views as auth_views
from store.views import HomeView

# Simple test view
def test_view(request):
    return HttpResponse("Test view is working!")

# Better error handling for catch-all
@requires_csrf_token
def custom_page_not_found(request, exception=None, template_name='404.html'):
    return JsonResponse({
        'status': 'error',
        'message': 'Page not found',
        'path': request.path
    }, status=404)

# Redirect to store home
def home_view(request):
    return redirect('store:home')  # This will redirect to the store's home page (root URL of store app)

urlpatterns = [
    # Home page - serve store's home view directly
    path('', views.HomeView.as_view(), name='home'),
    
    # Store app - include with empty prefix
    path('', include('store.urls')),
    
    # Auth URLs - Moved to accounts app
    path('accounts/', include('accounts.urls', namespace='accounts')),
    
    # Test URL
    path('test/', test_view, name='test'),
    
    # Admin URLs
    path('admin/', admin.site.urls),
    
    # Store app
    path('store/', include('store.urls', namespace='store')),
    
    # Payment app - Handle both /payment/ and /payments/
    path('payment/', include([
        path('', include('payment.urls', namespace='payment')),  # Handles /payment/
        path('pay/', include('payment.urls', namespace='payment_pay')),  # Handles /payment/pay/
    ])),
    # Redirect /payments/ to /payment/
    path('payments/', lambda request: redirect('payment:payment_home', permanent=True)),
]

# Custom error handlers
handler404 = 'angels_plants.urls.custom_page_not_found'
handler500 = 'angels_plants.urls.custom_page_not_found'

# Serve media files in development
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
