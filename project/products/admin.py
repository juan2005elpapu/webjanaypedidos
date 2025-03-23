from django.contrib import admin
from .models import Product, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'weight', 'is_available')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description', 'ingredients')
    list_editable = ('price', 'is_available')
    autocomplete_fields = ('category',)
