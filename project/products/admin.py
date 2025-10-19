from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from cloudinary.forms import CloudinaryFileField
from unfold.admin import ModelAdmin
from .models import Product, Category

class ProductForm(forms.ModelForm):
    image = CloudinaryFileField(
        options={
            "folder": "products",
            "resource_type": "image",
            "multiple": False,
            "cropping": False,
            "client_allowed_formats": ["jpg", "jpeg", "png", "webp", "gif"],
            "tags": ["product"],
            "secure": True,
        },
        required=False,
    )

    class Meta:
        model = Product
        fields = '__all__'
        
    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image is False:
            return None
        return image

    class Media:
        js = ("https://widget.cloudinary.com/v2.0/global/all.js",)

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
                duplicated_product.image = original_product.image
                duplicated_product.save(update_fields=["image"])
            
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
            'description': 'puedes subir una imagen desde el disco duro.'
        }),
        ('Peso y contenido', {
            'fields': ('weight', 'ingredients')
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
        url = obj.image_secure_url() if obj.image else ""
        if url:
             return format_html(
                 '<img src="{}" alt="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">',
                 url,
                 obj.name
             )
        return format_html(
            '<div style="width: 50px; height: 50px; background-color: #f3f4f6; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 12px;">Sin imagen</div>'
        )
    image_preview.short_description = 'Imagen'
    
    def image_preview_large(self, obj):
        """Previsualización grande para el formulario"""
        url = obj.image_secure_url() if obj.image else ""
        if url:
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
                 url,
                 obj.name,
                 obj.image.public_id if obj.image else "",
                 url,
                 url
             )
        return format_html(
            '<div style="padding: 20px; background-color: #f9fafb; border-radius: 8px; text-align: center; color: #6b7280;">No hay imagen cargada</div>'
        )
    image_preview_large.short_description = 'Vista previa'
