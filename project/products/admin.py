from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Product, Category
from .supabase_storage import SupabaseStorage


class ProductForm(forms.ModelForm):
    image_file = forms.FileField(required=False, label="Subir imagen")
    clear_image = forms.BooleanField(required=False, label="Eliminar imagen")

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'weight', 'category', 'is_available', 'ingredients']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.image:
            self.fields['clear_image'].help_text = f"Imagen actual: {self.instance.image}"
        else:
            self.fields['clear_image'].widget = forms.HiddenInput()

    def save(self, commit=True):
        instance = super().save(commit=False)
        storage = SupabaseStorage()
        
        # Eliminar imagen si se marcó clear_image
        if self.cleaned_data.get('clear_image'):
            if instance.image:
                storage.delete(instance.image)
            instance.image = None
        
        # Subir nueva imagen si se proporcionó
        elif self.cleaned_data.get('image_file'):
            uploaded_file = self.cleaned_data['image_file']
            
            # Eliminar imagen anterior si existe
            if instance.image:
                storage.delete(instance.image)
            
            # Subir nueva imagen a Supabase
            new_key = storage._save(uploaded_file.name, uploaded_file)
            instance.image = new_key
        
        if commit:
            instance.save()
        
        return instance


def duplicate_products(_modeladmin, request, queryset):
    duplicated_count = 0
    errors = []
    storage = SupabaseStorage()
    
    for original_product in queryset:
        try:
            duplicated_product = Product(
                name=f"{original_product.name} (Copia)",
                description=original_product.description,
                price=original_product.price,
                weight=original_product.weight,
                category=original_product.category,
                is_available=original_product.is_available,
                ingredients=original_product.ingredients,
            )
            
            # Duplicar imagen si existe
            if original_product.image:
                try:
                    new_key = storage.copy(original_product.image)
                    duplicated_product.image = new_key
                except Exception as img_error:
                    errors.append(f'Imagen no duplicada para "{original_product.name}": {str(img_error)}')
            
            duplicated_product.save()
            duplicated_count += 1
            
        except Exception as e:
            errors.append(f'Error duplicando "{original_product.name}": {str(e)}')
    
    if duplicated_count > 0:
        if duplicated_count == 1:
            messages.success(request, 'Se duplicó 1 producto exitosamente.')
        else:
            messages.success(request, f'Se duplicaron {duplicated_count} productos exitosamente.')
    
    if errors:
        for error in errors:
            messages.warning(request, error)

duplicate_products.short_description = "Duplicar productos seleccionados"


@admin.register(Category)
class CategoryAdmin(UnfoldModelAdmin):
    list_display = ('name', 'slug', 'products_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    
    def products_count(self, obj):
        count = obj.products.count()
        if count > 0:
            url = reverse('admin:products_product_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}" target="_blank">{} productos</a>', url, count)
        return '0 productos'
    
    products_count.short_description = 'Productos'


@admin.register(Product)
class ProductAdmin(UnfoldModelAdmin):
    form = ProductForm
    list_display = ['image_preview', 'name_link', 'price', 'weight', 'category', 'is_available']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['price', 'weight', 'is_available']
    readonly_fields = ['image_preview_large', 'created_at', 'updated_at']
    actions = [duplicate_products]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'description', 'category')
        }),
        ('Precio y Disponibilidad', {
            'fields': ('price', 'is_available'),
        }),
        ('Imagen', {
            'fields': ('image_file', 'clear_image', 'image_preview_large'),
            'description': 'Sube una imagen o marca "Eliminar imagen" para borrarla.'
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
        url = reverse('admin:products_product_change', args=[obj.pk])
        color = '#ffffff' if obj.is_available else '#ef4444'
        return format_html('<a href="{}" style="text-decoration: none; color: {}; font-weight: 500;">{}</a>', url, color, obj.name)
    name_link.short_description = 'Nombre'
    name_link.admin_order_field = 'name'
    
    def image_preview(self, obj):
        url = obj.image_secure_url()
        if url:
            return format_html(
                '<img src="{}" alt="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;">',
                url,
                obj.name
            )
        return format_html(
            '<div style="width: 50px; height: 50px; background-color: #f3f4f6; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 10px;">Sin img</div>'
        )
    image_preview.short_description = 'Img'
    
    def image_preview_large(self, obj):
        url = obj.image_secure_url()
        if url:
            return format_html(
                '''
                <div style="margin-top: 10px;">
                    <img src="{}" alt="{}" style="max-width: 300px; max-height: 300px; object-fit: cover; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <p style="margin-top: 8px; font-size: 12px; color: #e5e7eb;">
                        <strong style="color:#f9fafb;">Archivo:</strong> <span style="color:#d1d5db;">{}</span><br>
                        <a href="{}" target="_blank" style="color:#93c5fd; text-decoration: underline;">Ver imagen completa</a>
                    </p>
                </div>
                ''',
                url,
                obj.name,
                obj.image or "",
                url
            )
        return format_html(
            '<div style="padding: 20px; background-color: #111827; border-radius: 8px; text-align: center; color: #e5e7eb;">No hay imagen cargada</div>'
        )
    image_preview_large.short_description = 'Vista previa'
