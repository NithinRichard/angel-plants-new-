"""
Performance monitoring and optimization utilities.
"""
import time
import logging
from functools import wraps
from django.conf import settings
from django.db import connection, reset_queries
from django.core.cache import cache

logger = logging.getLogger(__name__)

def query_debugger(func):
    """
    Decorator to log SQL queries and execution time for a function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not settings.DEBUG:
            return func(*args, **kwargs)
            
        reset_queries()
        start_queries = len(connection.queries)
        start_time = time.perf_counter()
        
        result = func(*args, **kwargs)
        
        end_time = time.perf_counter()
        end_queries = len(connection.queries)
        
        queries = end_queries - start_queries
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        
        logger.debug(
            "%s: %d queries in %.2fms",
            func.__qualname__,
            queries,
            duration
        )
        
        if queries > 10:  # Log warning for too many queries
            logger.warning(
                "%s: High query count (%d) in %.2fms",
                func.__qualname__,
                queries,
                duration
            )
            
        return result
    return wrapper


class PerformanceMiddleware:
    """
    Middleware to measure request processing time and query count.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.threshold = getattr(settings, 'PERFORMANCE_THRESHOLD_MS', 500)

    def __call__(self, request):
        # Skip performance logging for static/media files
        if any(path in request.path for path in ['/static/', '/media/']):
            return self.get_response(request)
            
        # Start timing
        start_time = time.time()
        
        # Reset query count
        if settings.DEBUG:
            reset_queries()
        
        # Process the request
        response = self.get_response(request)
        
        # Calculate timing
        total_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Get query count if in debug mode
        query_count = len(connection.queries) if settings.DEBUG else 0
        
        # Log slow requests
        if total_time > self.threshold:
            logger.warning(
                'Slow request: %s %s - %.2fms (%d queries)',
                request.method,
                request.path,
                total_time,
                query_count
            )
        
        # Add performance headers
        if settings.DEBUG:
            response['X-Request-Time'] = f"{total_time:.2f}ms"
            response['X-Query-Count'] = query_count
        
        return response


def cache_page(timeout):
    """
    A more flexible page cache decorator that works with varying arguments.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Generate cache key
            cache_key = f"page_cache:{request.path}:{request.GET.urlencode()}"
            
            # Try to get response from cache
            response = cache.get(cache_key)
            if response is not None:
                return response
            
            # Generate the response
            response = view_func(request, *args, **kwargs)
            
            # Cache the response if it's a successful response
            if response.status_code == 200:
                cache.set(cache_key, response, timeout)
            
            return response
        return _wrapped_view
    return decorator


class QueryCounter:
    """
    Context manager to count and log database queries.
    """
    def __init__(self, name=None):
        self.name = name or "unnamed"
        self.queries_before = 0
        self.queries_after = 0
    
    def __enter__(self):
        if settings.DEBUG:
            reset_queries()
            self.queries_before = len(connection.queries)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if settings.DEBUG:
            self.queries_after = len(connection.queries)
            query_count = self.queries_after - self.queries_before
            logger.debug(
                "QueryCounter[%s]: %d queries executed",
                self.name,
                query_count
            )
            
            if query_count > 10:  # Log warning for too many queries
                logger.warning(
                    "QueryCounter[%s]: High query count: %d",
                    self.name,
                    query_count
                )


def log_memory_usage():
    """
    Log current memory usage of the process.
    Requires psutil to be installed.
    """
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        logger.debug(
            "Memory usage: %.2f MB RSS, %.2f MB VMS",
            mem_info.rss / 1024 / 1024,
            mem_info.vms / 1024 / 1024
        )
    except ImportError:
        logger.warning("psutil not installed, memory tracking not available")
