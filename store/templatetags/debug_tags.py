from django import template
from django.utils.safestring import mark_safe
import pprint

register = template.Library()

@register.filter
def get_type(value):
    """Return the type of the value"""
    return type(value).__name__

@register.filter
def get_attributes(value):
    """Return all attributes of an object"""
    if hasattr(value, '__dict__'):
        return {k: v for k, v in value.__dict__.items() if not k.startswith('_')}
    return {}

@register.filter
def pprint_filter(value):
    """Pretty print a value"""
    return mark_safe(f'<pre>{pprint.pformat(value)}</pre>')
