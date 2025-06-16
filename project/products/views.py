from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from .models import Product, Category
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


# SEÑALES PARA INVALIDAR CACHE AUTOMÁTICAMENTE
@receiver([post_save, post_delete], sender=Product)
def invalidate_product_cache(sender, **kwargs):
    """Invalidar cache cuando se modifica un producto"""
    cache.delete('active_categories_available')
    cache.delete('active_categories')
    # Invalidar cache de páginas también
    cache.delete_many(['productlist_*', 'productdetail_*'])
    print("✅ Cache de productos invalidado automáticamente")

@receiver([post_save, post_delete], sender=Category)
def invalidate_category_cache(sender, **kwargs):
    """Invalidar cache cuando se modifica una categoría"""
    cache.delete('active_categories_available')
    cache.delete('active_categories')
    print("✅ Cache de categorías invalidado automáticamente")


# SIN CACHE en desarrollo para evitar problemas
# @method_decorator(cache_page(60 * 5), name='dispatch')  # COMENTADO TEMPORALMENTE
class ProductListView(LoginRequiredMixin, ListView):
    """Lista todos los productos disponibles"""
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = None  # ← Eliminar paginación server-side
    
    def get_queryset(self):
        # SOLO carga inicial - sin filtros dinámicos
        return Product.objects.select_related('category').filter(
            is_available=True
        ).only(
            'id', 'name', 'price', 'weight', 'image',
            'category__name', 'category__slug'
        ).order_by('category__name', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Categorías para filtros JS
        context['categories'] = Category.objects.filter(
            products__is_available=True
        ).distinct().only('name', 'slug')
        
        # Flag para decidir entre JS vs Server pagination
        products_count = context['products'].count()
        context['use_js_filtering'] = products_count <= 100
        context['products_count'] = products_count
        
        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Muestra detalles de un producto específico"""
    model = Product
    template_name = 'products/detail.html'
    context_object_name = 'product'
    pk_url_kwarg = 'product_id'
    login_url = 'login'
    
    def get_queryset(self):
        # ASEGURAR: Solo productos disponibles
        return Product.objects.select_related('category').filter(is_available=True)
    
    def get_object(self, queryset=None):
        """Override para manejar productos no disponibles"""
        try:
            return super().get_object(queryset)
        except Product.DoesNotExist:
            # Si el producto no está disponible, redirigir con mensaje
            messages.error(self.request, 'El producto solicitado no está disponible.')
            return redirect('products:list')