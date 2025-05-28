from django.urls import path
from django.http import HttpResponse

def test_view(request):
    return HttpResponse("Test view is working!")

def catch_all(request, path=''):
    return HttpResponse(f"Path requested: {path}")

urlpatterns = [
    path('test/', test_view, name='test'),
    path('', catch_all, name='home'),
    path('<path:path>', catch_all),  # Catch all other paths
]
