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
    """
    Action para duplicar productos seleccionados en el admin
    Crea objetos completamente nuevos e independientes
    """
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
                # NO incluir: id, created_at, updated_at, image (por ahora)
            }
            
            # Crear producto completamente nuevo
            duplicated_product = Product(**original_data)
            duplicated_product.save()  # Esto genera un nuevo ID automáticamente
            
            # Copiar la imagen si existe (crear archivo físico independiente)
            if original_product.image:
                try:
                    # Obtener información del archivo original
                    original_path = original_product.image.path
                    original_name = os.path.basename(original_path)
                    
                    # Generar nombre único para la imagen duplicada
                    name_parts = os.path.splitext(original_name)
                    new_name = f"{name_parts[0]}_copy_{duplicated_product.id}{name_parts[1]}"
                    
                    # Construir nueva ruta
                    original_dir = os.path.dirname(original_product.image.name)
                    new_relative_path = os.path.join(original_dir, new_name)
                    new_absolute_path = os.path.join(settings.MEDIA_ROOT, new_relative_path)
                    
                    # Crear directorio si no existe
                    os.makedirs(os.path.dirname(new_absolute_path), exist_ok=True)
                    
                    # Copiar archivo físico
                    shutil.copy2(original_path, new_absolute_path)
                    
                    # Asignar nueva imagen al producto duplicado
                    duplicated_product.image = new_relative_path
                    duplicated_product.save()
                    
                except Exception as e:
                    # Si falla la copia de imagen, continuar sin ella
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

# Configurar el action
duplicate_products.short_description = "Duplicar productos seleccionados"


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name', 'slug', 'products_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    
    def products_count(self, obj):
        """Muestra el número de productos en la categoría"""
        count = obj.product_set.count()
        if count > 0:
            url = reverse('admin:products_product_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}" target="_blank">{} productos</a>', url, count)
        return '0 productos'
    
    products_count.short_description = 'Productos'


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductForm
    list_display = ('name', 'category', 'price', 'weight', 'is_available', 'display_image')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description', 'ingredients')
    list_editable = ('price', 'is_available')
    autocomplete_fields = ('category',)
    readonly_fields = ('display_image_large', 'created_at', 'updated_at')
    
    # 🔥 AGREGAR EL ACTION DE DUPLICACIÓN
    actions = [duplicate_products]
    
    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "Sin imagen"
    display_image.short_description = 'Vista previa'
    
    def display_image_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="300" style="max-height: 300px; object-fit: contain;" />', obj.image.url)
        return "Sin imagen"
    display_image_large.short_description = 'Vista previa de imagen'
    
    fieldsets = (
        ('Información básica', {
            'fields': ('name', 'category', 'description', 'price')
        }),
        ('Detalles adicionales', {
            'fields': ('weight', 'ingredients', 'is_available')
        }),
        ('Imagen', {
            'fields': ('image', 'display_image_large'),
            'description': 'Formatos aceptados: JPEG, PNG, GIF, BMP, TIFF. Se convertirá automáticamente a WebP para optimización web.'
        }),
        ('Información del sistema', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Sobreescribe el método save_model para manejar correctamente
        el caso donde la imagen ha sido eliminada.
        """
        # Si el formulario tenía una imagen marcada para eliminar (Clear)
        if 'image' in form.cleaned_data and form.cleaned_data['image'] is False:
            obj.image = None
        
        super().save_model(request, obj, form, change)
        
        # Si la imagen se eliminó, asegurarnos de que se guarde con None
        if 'image' in form.cleaned_data and form.cleaned_data['image'] is False:
            obj.image = None
