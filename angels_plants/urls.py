"""
URL configuration for angels_plants project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve
from django.views.decorators.cache import never_cache
from django.contrib.auth import views as auth_views
from django.views.decorators.http import require_http_methods
from django.contrib.auth import logout
from django.shortcuts import redirect
from accounts.views import SignUpView
from store.admin import angel_plants_admin

@require_http_methods(["GET", "POST"])
def custom_logout(request):
    logout(request)
    return redirect('/')

urlpatterns = [
    # Default admin site
    path('admin/', admin.site.urls),
    
    # Custom admin site
    path('angel-plants-admin/', angel_plants_admin.urls),
    
    # Store app
    path('', include('store.urls', namespace='store')),
    
    # Payment app
    path('payment/', include('payment.urls', namespace='payment')),
    
    # Authentication
    path('accounts/logout/', custom_logout, name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', SignUpView.as_view(), name='signup'),
    path('accounts/profile/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('media/<path:path>', serve, {
            'document_root': settings.MEDIA_ROOT,
            'show_indexes': True,
        }),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

