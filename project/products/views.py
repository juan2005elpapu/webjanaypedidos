from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .models import Product, Category


class ProductListView(LoginRequiredMixin, ListView):
    """Lista todos los productos disponibles"""
    model = Product
    template_name = 'products/list.html'
    context_object_name = 'products'
    login_url = 'login'
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_available=True)
        
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
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Muestra detalles de un producto específico"""
    model = Product
    template_name = 'products/detail.html'
    context_object_name = 'product'
    pk_url_kwarg = 'product_id'
    login_url = 'login'
    
    def get_queryset(self):
        return Product.objects.filter(is_available=True)
