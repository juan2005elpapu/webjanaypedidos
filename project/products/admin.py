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

    def clean_image(self):
        image = self.cleaned_data.get('image')
        print(f"DEBUG FORM - Valor inicial en clean_image: {image}, tipo: {type(image)}")
        
        # Si se marcó "Clear" (valor False)
        if image is False:
            print("DEBUG FORM - Se marcó Clear, eliminando imagen")
            # Si hay instancia y tiene imagen actual, la eliminamos explícitamente
            if self.instance and self.instance.pk and hasattr(self.instance, 'image') and self.instance.image:
                try:
                    # Guardamos la ruta para eliminarla después
                    old_path = self.instance.image.path
                    # Establecemos None para que Django sepa que debe eliminar la referencia
                    self.instance.image = None
                    # Si el archivo existe físicamente, lo eliminamos
                    import os
                    if os.path.isfile(old_path):
                        os.remove(old_path)
                        print(f"DEBUG FORM - Archivo físico eliminado: {old_path}")
                except Exception as e:
                    print(f"ERROR al eliminar archivo en clean_image: {e}")
            return None  # Retornamos None para continuar con el proceso normal
        
        # Si el campo está vacío (sin marcar Clear)
        if image is None or image == '':
            return None
        
        # Si el usuario subió una imagen nueva
        if isinstance(image, UploadedFile):
            validate_image_format(image)
            return image
        
        # Si no hay cambios (mantener la imagen existente)
        return self.instance.image if hasattr(self.instance, 'image') else None

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
