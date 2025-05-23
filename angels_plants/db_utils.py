from django.db import models
from django.db.models import Prefetch
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

def query_debugger(func):
    """
    Decorator to log slow database queries
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from django.db import connection
        
        # Reset the query count
        start_queries = len(connection.queries)
        start_time = time.time()
        
        # Execute the function
        result = func(*args, **kwargs)
        
        # Calculate statistics
        end_time = time.time()
        duration = end_time - start_time
        queries = len(connection.queries) - start_queries
        
        # Log if the query took too long or had too many queries
        if duration > 1.0 or queries > 10:  # Thresholds can be adjusted
            logger.warning(
                'Query performance: %s took %.2f seconds, %d queries',
                func.__name__,
                duration,
                queries
            )
            
            # Log the actual queries if in debug mode
            if hasattr(func, '_queryset'):
                logger.debug('Query: %s', str(func._queryset.query))
            
            for i, query in enumerate(connection.queries[start_queries:], 1):
                logger.debug('Query %d: %s', i, query['sql'])
        
        return result
    return wrapper

class QueryOptimizer:
    """
    Utility class to optimize common query patterns
    """
    @staticmethod
    def prefetch_related_optimized(queryset, *args, **kwargs):
        """
        Enhanced prefetch_related with common optimizations
        """
        return queryset.prefetch_related(
            *args,
            **{
                **kwargs,
                '_prefetch_related_lookups': [
                    Prefetch(
                        lookup,
                        queryset=related_model._default_manager.all(),
                        to_attr=f'prefetched_{lookup}'
                    )
                    for lookup in args if hasattr(queryset.model, lookup)
                ]
            }
        )
    
    @staticmethod
    def select_related_optimized(queryset, *args, **kwargs):
        """
        Enhanced select_related with common optimizations
        """
        return queryset.select_related(*args, **kwargs)

    @classmethod
    def optimize_queryset(cls, queryset, select_related=None, prefetch_related=None):
        """
        Apply common optimizations to a queryset
        """
        if select_related:
            queryset = cls.select_related_optimized(queryset, *select_related)
        if prefetch_related:
            queryset = cls.prefetch_related_optimized(queryset, *prefetch_related)
        return queryset

def analyze_queries():
    """
    Print query analysis for the current request
    """
    from django.db import connection
    from django.db.backends.utils import CursorDebugWrapper
    
    queries = connection.queries
    total_time = sum(float(q['time']) for q in queries)
    
    print(f"\n{'='*80}")
    print(f"QUERY ANALYSIS: {len(queries)} queries in {total_time:.3f} seconds")
    print("-"*80)
    
    # Group similar queries
    query_groups = {}
    for q in queries:
        sql = q['sql']
        if sql in query_groups:
            query_groups[sql]['count'] += 1
            query_groups[sql]['time'] += float(q['time'])
        else:
            query_groups[sql] = {
                'sql': sql,
                'count': 1,
                'time': float(q['time'])
            }
    
    # Sort by total time
    sorted_queries = sorted(
        query_groups.values(),
        key=lambda x: x['time'],
        reverse=True
    )
    
    # Print top 10 slowest queries
    print("\nTOP 10 SLOWEST QUERIES:")
    for i, q in enumerate(sorted_queries[:10], 1):
        print(f"{i}. {q['time']:.3f}s (x{q['count']}): {q['sql'][:100]}...")
    
    # Print query count by model
    print("\nQUERY COUNT BY MODEL:")
    from collections import defaultdict
    models = defaultdict(int)
    for q in queries:
        if 'FROM' in q['sql']:
            table = q['sql'].split('FROM')[1].split()[0].strip('`"\'')
            models[table] += 1
    
    for model, count in sorted(models.items(), key=lambda x: x[1], reverse=True):
        print(f"{model}: {count} queries")
    
    print("="*80 + "\n")
