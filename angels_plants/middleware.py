import time
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class SimpleMiddlewareTiming:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.
        self.threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 2.0)  # seconds

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        start_time = time.time()
        
        # Get the response
        response = self.get_response(request)
        
        # Calculate request time
        total_time = time.time() - start_time
        
        # Log slow requests
        if total_time > self.threshold:
            logger.warning(
                'Slow request: %.2f seconds - %s %s',
                total_time,
                request.method,
                request.path,
                extra={
                    'request': request,
                    'time_taken': total_time,
                }
            )
        
        # Add timing header for debugging
        if settings.DEBUG:
            response['X-Request-Time'] = f"{total_time:.2f}s"
        
        return response
        
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Get the view name as a string
        view = f"{view_func.__module__}.{view_func.__name__}"
        
        # Store the view name and start time in the request
        request._view_name = view
        request._view_start_time = time.time()
        
        return None  # Continue processing the request
        
    def process_template_response(self, request, response):
        # Only process if we have timing data
        if hasattr(request, '_view_start_time') and hasattr(response, 'context_data'):
            timing = time.time() - request._view_start_time
            if hasattr(response, 'context_data') and response.context_data is not None:
                response.context_data['view_time'] = f"{timing:.3f}s"
        return response
