from django import template
from urllib.parse import urlencode
from collections import namedtuple

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Replace or add a parameter in the URL.
    
    Usage in template:
    {% url_replace request 'page' page_obj.next_page_number %}
    """
    # Create a mutable copy of the GET parameters
    dict_ = request.GET.copy()
    
    # Update or add the parameter
    dict_[field] = value
    
    # Remove page parameter if value is 1 (first page)
    if field == 'page' and int(value) == 1:
        dict_.pop('page', None)
    
    # Return the encoded URL with the updated parameters
    return urlencode(dict_)
