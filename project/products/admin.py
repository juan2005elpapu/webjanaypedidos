from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.html import format_html
from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from unfold.admin import ModelAdmin
from .models import Product, Category
from .utils import validate_image_format
import os
import shutil
from django.conf import settings


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        
    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        # Si se marcó "Clear"
        if image is False:
            if self.instance and self.instance.pk and hasattr(self.instance, 'image') and self.instance.image:
                try:
                    old_path = self.instance.image.path
                    self.instance.image = None
                    import os
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                except Exception:
                    pass
            return None
        
        # Si el campo está vacío
        if image is None or image == '':
            return None
        
        # Si el usuario subió una imagen nueva
        if isinstance(image, UploadedFile):
            validate_image_format(image)
            return image
        
        # Mantener imagen existente
        return self.instance.image if hasattr(self.instance, 'image') else None


def duplicate_products(modeladmin, request, queryset):
    """Action para duplicar productos seleccionados en el admin"""
    duplicated_count = 0
    errors = []
    
    for original_product in queryset:
        try:
            # Obtener datos del producto original (SIN el ID)
            original_data = {
                'name': f"{original_product.name} (Copia)",
                'description': original_product.description,
                'price': original_product.price,
                'weight': original_product.weight,
                'category': original_product.category,
                'is_available': original_product.is_available,
                'ingredients': original_product.ingredients,
            }
            
            # Crear producto completamente nuevo
            duplicated_product = Product(**original_data)
            duplicated_product.save()
            
            # Copiar la imagen si existe
            if original_product.image:
                try:
                    original_path = original_product.image.path
                    original_name = os.path.basename(original_path)
                    
                    name_parts = os.path.splitext(original_name)
                    new_name = f"{name_parts[0]}_copy_{duplicated_product.id}{name_parts[1]}"
                    
                    original_dir = os.path.dirname(original_product.image.name)
                    new_relative_path = os.path.join(original_dir, new_name)
                    new_absolute_path = os.path.join(settings.MEDIA_ROOT, new_relative_path)
                    
                    os.makedirs(os.path.dirname(new_absolute_path), exist_ok=True)
                    shutil.copy2(original_path, new_absolute_path)
                    
                    duplicated_product.image = new_relative_path
                    duplicated_product.save()
                    
                except Exception as e:
                    errors.append(f'Producto "{original_product.name}" duplicado sin imagen. Error: {str(e)}')
            
            duplicated_count += 1
            
        except Exception as e:
            errors.append(f'Error duplicando "{original_product.name}": {str(e)}')
    
    # Mostrar mensajes de resultado
    if duplicated_count > 0:
        if duplicated_count == 1:
            messages.success(request, f'Se duplicó 1 producto exitosamente.')
        else:
            messages.success(request, f'Se duplicaron {duplicated_count} productos exitosamente.')
    
    if errors:
        for error in errors:
            messages.warning(request, error)
    
    if duplicated_count == 0 and not errors:
        messages.error(request, 'No se pudo duplicar ningún producto.')

duplicate_products.short_description = "Duplicar productos seleccionados"

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'products_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    
    def products_count(self, obj):
        """Muestra el número de productos en la categoría"""
        count = obj.products.count()
        if count > 0:
            url = reverse('admin:products_product_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}" target="_blank">{} productos</a>', url, count)
        return '0 productos'
    
    products_count.short_description = 'Productos'

@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductForm
    # SIMPLIFICADO: Sin availability_status
    list_display = ['image_preview', 'name_link', 'price', 'weight', 'category', 'is_available']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'description']
    # CORREGIDO: Solo campos que están en list_display
    list_editable = ['price', 'weight', 'is_available']
    readonly_fields = ['image_preview_large', 'created_at', 'updated_at']
    actions = [duplicate_products]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'category')
        }),
        ('Precio y Disponibilidad', {
            'fields': ('price', 'is_available'),
            'description': 'El precio se guardará sin decimales automáticamente'
        }),
        ('Imagen', {
            'fields': ('image', 'image_preview_large'),
            'description': 'Las imágenes se convertirán automáticamente a WebP'
        }),
        ('Detalles del Producto', {
            'fields': ('weight', 'ingredients'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def name_link(self, obj):
        """Nombre del producto como enlace a la página de edición"""
        url = reverse('admin:products_product_change', args=[obj.pk])
        # MEJORADO: Color diferente si no está disponible
        color = '#ffffff' if obj.is_available else '#ef4444'
        return format_html('<a href="{}" style="text-decoration: none; color: {}; font-weight: 500;">{}</a>', url, color, obj.name)
    name_link.short_description = 'Nombre'
    name_link.admin_order_field = 'name'
    
    def image_preview(self, obj):
        """Previsualización pequeña para la lista"""
        if obj.image:
            return format_html(
                '<img src="{}" alt="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">',
                obj.image.url,
                obj.name
            )
        return format_html(
            '<div style="width: 50px; height: 50px; background-color: #f3f4f6; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 12px;">Sin imagen</div>'
        )
    image_preview.short_description = 'Imagen'
    
    def image_preview_large(self, obj):
        """Previsualización grande para el formulario"""
        if obj.image:
            return format_html(
                '''
                <div style="margin-top: 10px;">
                    <img src="{}" alt="{}" style="max-width: 300px; max-height: 300px; object-fit: cover; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <p style="margin-top: 8px; font-size: 12px; color: #6b7280;">
                        <strong>Archivo:</strong> {}<br>
                        <strong>URL:</strong> <a href="{}" target="_blank">{}</a>
                    </p>
                </div>
                ''',
                obj.image.url,
                obj.name,
                obj.image.name,
                obj.image.url,
                obj.image.url
            )
        return format_html(
            '<div style="padding: 20px; background-color: #f9fafb; border-radius: 8px; text-align: center; color: #6b7280;">No hay imagen cargada</div>'
        )
    image_preview_large.short_description = 'Vista previa'
