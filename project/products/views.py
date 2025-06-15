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


@method_decorator(cache_page(60 * 5), name='dispatch')  # Cache por 5 minutos
class ProductListView(LoginRequiredMixin, ListView):
    """Lista todos los productos disponibles"""
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    paginate_by = 12
    login_url = 'login'
    
    def get_queryset(self):
        # Optimizar con select_related para evitar N+1 queries
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
        
        # Cache para categorías
        categories = cache.get('active_categories')
        if categories is None:
            categories = Category.objects.all()
            cache.set('active_categories', categories, 60 * 15)  # Cache por 15 minutos
            
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
        return Product.objects.select_related('category').filter(is_available=True)