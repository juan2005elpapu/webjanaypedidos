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
    paginate_by = 12
    login_url = 'login'
    
    def get_queryset(self):
        # ASEGURAR: Solo productos disponibles + optimización
        queryset = Product.objects.select_related('category').filter(is_available=True)
        
        # Aplicar filtro de búsqueda si existe
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(ingredients__icontains=search_query)
            )
        
        # Aplicar filtro de categoría si existe
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
            
        return queryset.order_by('category__name', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # SIN CACHE para categorías en desarrollo
        # categories = cache.get('active_categories_available')
        # if categories is None:
        
        # SIEMPRE CONSULTAR DB - Solo categorías que tienen productos disponibles
        categories = Category.objects.filter(
            products__is_available=True
        ).distinct().order_by('name')
        # cache.set('active_categories_available', categories, 60 * 15)
            
        context['categories'] = categories
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('q', '')
        
        # Agregar información de la categoría seleccionada para el template
        if context['selected_category']:
            try:
                selected_category_obj = categories.get(slug=context['selected_category'])
                context['selected_category_name'] = selected_category_obj.name
            except Category.DoesNotExist:
                context['selected_category_name'] = 'Categoría no encontrada'
        
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