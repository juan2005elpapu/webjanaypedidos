from django.db import models
from django.utils.text import slugify
from .utils import convert_to_webp, validate_image_format  # Añadir validate_image_format
from django.core.files.uploadedfile import UploadedFile  # Añadir esta importación
import os 
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver



class Category(models.Model):
    name = models.CharField('Nombre', max_length=100)
    slug = models.SlugField(unique=True)
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField('Nombre', max_length=200)
    description = models.TextField('Descripción', blank=True)
    price = models.DecimalField('Precio', max_digits=10, decimal_places=2)
    weight = models.DecimalField('Peso (g)', max_digits=7, decimal_places=2, blank=True, null=True)
    ingredients = models.TextField('Ingredientes', blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Categoría')
    image = models.ImageField('Imagen', upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField('Disponible', default=True)
    created_at = models.DateTimeField('Fecha de creación', auto_now_add=True)
    updated_at = models.DateTimeField('Última actualización', auto_now=True)
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['category', 'name']
        
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Si no hay imagen, guarda directamente
        if self.image is None:
            super().save(*args, **kwargs)
            return
        
        # Manejo seguro para problemas con la imagen
        try:
            if hasattr(self.image, 'file') and self.image.file is None:
                self.image = None
                super().save(*args, **kwargs)
                return
        except (ValueError, AttributeError):
            # Si hay error al acceder, establece a None
            self.image = None
            super().save(*args, **kwargs)
            return
        
        # Código para imagen válida
        old_image = None
        if self.pk:
            try:
                old_product = Product.objects.get(pk=self.pk)
                old_image = getattr(old_product, 'image', None)
            except Product.DoesNotExist:
                pass

        # Verificar si necesita conversión
        needs_conversion = False
        if self.image and hasattr(self.image, 'file') and self.image.file:
            if not old_image:
                needs_conversion = True
            elif old_image and old_image.name != getattr(self.image, 'name', None):
                needs_conversion = True

        # Convertir a WebP si es necesario
        if needs_conversion and hasattr(self.image, 'file') and self.image.file:
            try:
                image_before_conversion = self.image
                webp_image = convert_to_webp(self.image)
                if webp_image:
                    self.image = webp_image
                else:
                    self.image = image_before_conversion
            except Exception:
                pass

        # Guardar el modelo
        super().save(*args, **kwargs)

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


@receiver(pre_save, sender=Product)
def delete_old_image(sender, instance, **kwargs):
    """Elimina la imagen anterior si se reemplaza o elimina"""
    if not instance.pk:
        return
    
    try:
        old_product = Product.objects.get(pk=instance.pk)
        
        if not old_product.image:
            return
            
        if not instance.image or old_product.image.name != getattr(instance.image, 'name', None):
            if hasattr(old_product.image, 'path'):
                file_path = old_product.image.path
                if os.path.isfile(file_path):
                    os.remove(file_path)
    except Exception:
        pass


@receiver(post_delete, sender=Product)
def delete_image_on_delete(sender, instance, **kwargs):
    """Elimina el archivo de imagen cuando se elimina el objeto Product"""
    if not instance.image:
        return
    
    try:
        if hasattr(instance.image, 'path'):
            path = instance.image.path
            if os.path.isfile(path):
                os.remove(path)
    except Exception:
        pass



