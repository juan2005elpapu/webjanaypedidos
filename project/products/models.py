from django.db import models
from django.utils.text import slugify
from .utils import convert_to_webp
from django.core.files.uploadedfile import UploadedFile  
import os 
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from decimal import Decimal, ROUND_HALF_UP

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
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=0,  # SIN DECIMALES
        validators=[MinValueValidator(Decimal('1'))],
        verbose_name="Precio",
        help_text="Precio en pesos colombianos (sin decimales)"
    )
    category = models.ForeignKey(
        'Category', 
        on_delete=models.CASCADE, 
        related_name='products',
        verbose_name="Categoría"
    )
    image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True,
        verbose_name="Imagen"
    )
    is_available = models.BooleanField(default=True, verbose_name="Disponible")
    weight = models.PositiveIntegerField(
        blank=True, 
        null=True, 
        verbose_name="Peso (gramos)",
        help_text="Peso del producto en gramos"
    )
    ingredients = models.TextField(
        blank=True, 
        verbose_name="Ingredientes",
        help_text="Lista de ingredientes del producto"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['category__name', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Redondear precio al guardar y manejar conversión de imagen"""
        # PASO 1: Redondear precio
        if self.price:
            self.price = self.price.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # PASO 2: Manejar imagen
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
            self.image = None
            super().save(*args, **kwargs)
            return
        
        # PASO 3: Conversión a WebP si es necesario
        needs_conversion = self._needs_webp_conversion()
        
        if needs_conversion:
            self._convert_to_webp()

        super().save(*args, **kwargs)

    @property
    def formatted_price(self):
        """Devuelve el precio formateado sin decimales"""
        return f"${self.price:,.0f}"

    def _needs_webp_conversion(self):
        """Determina si la imagen necesita ser convertida a WebP"""
        if not (self.image and hasattr(self.image, 'file') and self.image.file):
            return False
            
        old_image = None
        if self.pk:
            try:
                old_product = Product.objects.get(pk=self.pk)
                old_image = getattr(old_product, 'image', None)
            except Product.DoesNotExist:
                pass
                
        if not old_image:
            return True
        elif old_image and old_image.name != getattr(self.image, 'name', None):
            return True
        return False
        
    def _convert_to_webp(self):
        """Convierte la imagen actual a formato WebP"""
        try:
            webp_image = convert_to_webp(self.image)
            if webp_image:
                self.image = webp_image
        except Exception as e:
            print(f"Error al convertir imagen a WebP: {e}")

# SEÑALES PARA MANEJO DE IMÁGENES
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
    except Exception as e:
        print(f"Error al eliminar imagen anterior: {e}")

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



