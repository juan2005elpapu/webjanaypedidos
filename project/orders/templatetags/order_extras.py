from django import template

register = template.Library()

@register.filter
def filter_by_category(products, category):
    """Filtrar productos por categoría"""
    return products.filter(category=category)

@register.filter
def get_item(dictionary, key):
    """Obtener item de diccionario por key"""
    return dictionary.get(key)