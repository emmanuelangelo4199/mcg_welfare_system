from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    return dictionary.get(key)

@register.filter
def get_attr(obj, attr):
    try:
        return getattr(obj, attr)
    except Exception:
        return None