from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.html import format_html
from django.contrib import admin
from .models import Product, Category
from .utils import validate_image_format

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ('name', 'category', 'price', 'weight', 'is_available', 'display_image')
    list_filter = ('category', 'is_available', 'created_at')
    search_fields = ('name', 'description', 'ingredients')
    list_editable = ('price', 'is_available')
    autocomplete_fields = ('category',)
    readonly_fields = ('display_image_large',)
    
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
    )
    
    def save_model(self, request, obj, form, change):
        """
        Sobreescribe el método save_model para manejar correctamente
        el caso donde la imagen ha sido eliminada.
        """
        # Si el formulario tenía una imagen marcada para eliminar (Clear)
        if 'image' in form.cleaned_data and form.cleaned_data['image'] is False:
            # Asegurarnos de que el objeto tenga image=None antes de guardarlo
            obj.image = None
        
        # Guardar el modelo como normalmente se haría
        super().save_model(request, obj, form, change)
        
        # Si la imagen se eliminó, asegurarnos de que se guarde con None
        if 'image' in form.cleaned_data and form.cleaned_data['image'] is False:
            # Esto asegura que después de guardar, no intentemos acceder a la imagen eliminada
            obj.image = None
