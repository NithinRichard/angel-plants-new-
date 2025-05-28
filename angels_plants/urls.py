from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.conf import settings
from django.conf.urls.static import static

# Test view
def test_view(request):
    return HttpResponse("Test view is working!")

# Catch-all for debugging
def catch_all(request, path=''):
    return HttpResponse(f"Path requested: {path}")

urlpatterns = [
    # Test URL
    path('test/', test_view, name='test'),
    
    # Admin URLs
    path('admin/', admin.site.urls),
    
    # Store app
    path('', include('store.urls', namespace='store')),
    
    # Payment app
    path('payment/', include('payment.urls', namespace='payment')),
    
    # Catch-all for debugging (keep this last)
    path('<path:path>', catch_all),
]

# Serve media files in development
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_URL)
