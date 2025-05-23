# Angel Plants - Performance Optimization Guide

This guide covers the performance optimizations implemented in the Angel Plants Django application and how to maintain them.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Performance Features](#performance-features)
3. [Monitoring & Profiling](#monitoring--profiling)
4. [Database Optimization](#database-optimization)
5. [Caching Strategy](#caching-strategy)
6. [Static Files](#static-files)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- PostgreSQL (recommended) or SQLite
- Node.js (for frontend assets)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/angel-plants.git
   cd angel-plants
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run database migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Performance Features

### 1. Database Optimization
- **Query Optimization**: Uses `select_related` and `prefetch_related`
- **Database Router**: Supports read replicas for scaling
- **Connection Pooling**: Reuses database connections
- **Indexing**: Proper database indexes for common queries

### 2. Caching
- **Page Caching**: Cache entire pages
- **Template Fragment Caching**: Cache parts of templates
- **View Caching**: Cache entire views
- **Low-level Cache API**: For custom caching needs

### 3. Static Files
- **WhiteNoise**: Efficient static file serving
- **Django Compressor**: CSS/JS minification
- **CDN Support**: For production deployments

### 4. Asynchronous Tasks
- **Celery**: For background tasks
- **Django Channels**: For WebSocket support

## Monitoring & Profiling

### Performance Monitoring

Run the performance monitor:
```bash
python scripts/performance_monitor.py --monitor --duration 300
```

### Database Profiling

Use Django Debug Toolbar by adding `?debug_toolbar=on` to any URL when `DEBUG=True`.

### Logging

Logs are stored in the `logs/` directory:
- `django.log`: Application logs
- `performance.log`: Performance metrics
- `access.log`: HTTP access logs (in production)
- `error.log`: Error logs (in production)

## Database Optimization

### Optimize Database

Run database optimizations:
```bash
python manage.py optimize_db --all
```

### Common Optimizations

1. **Add Indexes**:
   ```python
   class Meta:
       indexes = [
           models.Index(fields=['name'], name='name_idx'),
       ]
   ```

2. **Use `select_related` for ForeignKey fields**
3. **Use `prefetch_related` for ManyToMany fields**
4. **Use `only()` and `defer()` to limit fields**

## Caching Strategy

### Cache Backend
Configured to use Redis by default. Update `CACHES` in `settings.py` if needed.

### Template Caching
```django
{% load cache %}
{% cache 300 expensive_template request.user.username %}
    {# Expensive template logic #}
{% endcache %}
```

### View Caching
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # 15 minutes
def my_view(request):
    # View logic
```

## Static Files

### Collect Static Files
```bash
python manage.py collectstatic --noinput
python manage.py compress --force
```

### CDN Configuration
Set `STATIC_URL` and `STATIC_CDN_DOMAIN` in your `.env` file.

## Deployment

### Production Checklist
1. Set `DEBUG=False`
2. Update `ALLOWED_HOSTS`
3. Configure database connection
4. Set up Redis
5. Configure email backend
6. Set up SSL/TLS
7. Configure logging

### Gunicorn
```bash
gunicorn angels_plants.wsgi:application \
    --workers=4 \
    --threads=2 \
    --bind=0.0.0.0:8000 \
    --access-logfile=logs/access.log \
    --error-logfile=logs/error.log
```

### Nginx Configuration
Example Nginx configuration is available in `deployment/nginx.conf.example`.

## Troubleshooting

### Common Issues

1. **High CPU Usage**
   - Check for infinite loops
   - Profile CPU-intensive operations
   - Consider adding caching

2. **Memory Leaks**
   - Monitor memory usage over time
   - Check for large data structures in memory
   - Review caching strategy

3. **Slow Database Queries**
   - Use `connection.queries` in development
   - Add database indexes
   - Optimize ORM queries

### Performance Profiling

Use Django Debug Toolbar or `cProfile`:
```bash
python -m cProfile manage.py shell
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

For more information, please contact [Your Name] at [your.email@example.com]
