from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Allows accessing a dictionary's value by a key variable in templates."""
    return dictionary.get(key)