from django.db import models
from django.utils.text import slugify
from .utils import convert_to_webp
import os # Needed for os.path.basename
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.core.files import File


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
        print(f"DEBUG - Estado de la imagen al iniciar save(): {self.image}")
        
        # PRIMERA COMPROBACIÓN: Si no hay imagen, guarda directamente sin más procesamiento
        if self.image is None:
            print("DEBUG - La imagen es None, guardando sin conversión")
            super().save(*args, **kwargs)
            return
        
        # NUEVA COMPROBACIÓN: Manejo seguro para evitar el error ValueError
        try:
            # Intenta comprobar de forma segura si tiene un archivo
            if hasattr(self.image, 'file') and self.image.file is None:
                print("DEBUG - Se detectó ImageFieldFile con file=None (Clear marcado)")
                self.image = None
                super().save(*args, **kwargs)
                return
        except (ValueError, AttributeError) as e:
            # Si ocurre cualquier error al acceder a los atributos, es una señal
            # de que el valor es inválido y debería ser None
            print(f"DEBUG - Error al verificar imagen, estableciendo a None: {e}")
            self.image = None
            super().save(*args, **kwargs)
            return
        
        # El resto del código solo ejecuta si hay una imagen válida
        old_image = None
        if self.pk:
            try:
                old_product = Product.objects.get(pk=self.pk)
                # Usa getattr con valor predeterminado None para evitar errores
                old_image = getattr(old_product, 'image', None)
            except Product.DoesNotExist:
                pass

        # VERIFICA QUE EXISTA UNA IMAGEN ANTES DE INTENTAR CONVERTIRLA
        needs_conversion = False
        if self.image and hasattr(self.image, 'file') and self.image.file:
            if not old_image:
                needs_conversion = True
            elif old_image and old_image.name != getattr(self.image, 'name', None):
                needs_conversion = True

        if needs_conversion and hasattr(self.image, 'file') and self.image.file:
            try:
                image_before_conversion = self.image
                webp_image = convert_to_webp(self.image)
                if webp_image:
                    self.image = webp_image
                else:
                    print(f"WARN: WebP conversion failed for {self.image.name}")
                    self.image = image_before_conversion
            except Exception as e:
                print(f"ERROR: WebP conversion error for {self.image.name}: {e}")

        # Finalmente guarda el modelo
        super().save(*args, **kwargs)


@receiver(pre_save, sender=Product)
def delete_old_image(sender, instance, **kwargs):
    """Elimina la imagen anterior si se reemplaza o elimina"""
    if not instance.pk:
        return  # Es un objeto nuevo, no necesitamos hacer nada
    
    try:
        # Obtener el objeto anterior
        old_product = Product.objects.get(pk=instance.pk)
        
        # Si no tenía imagen antes, no hay que borrar
        if not old_product.image:
            return
            
        # Si la instancia actual no tiene imagen (Clear) o la imagen cambió
        if not instance.image or old_product.image.name != getattr(instance.image, 'name', None):
            # En caso de clear o cambio de imagen:
            if hasattr(old_product.image, 'path'):
                file_path = old_product.image.path
                # Intenta borrar, si falla registra el error
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"DEBUG: Imagen eliminada con éxito: {file_path}")
                else:
                    print(f"DEBUG: El archivo no existe: {file_path}")
                    
    except Exception as e:
        print(f"ERROR detallado al intentar eliminar imagen: {str(e)}")


@receiver(post_delete, sender=Product)
def delete_image_on_delete(sender, instance, **kwargs):
    """Elimina el archivo de imagen cuando se elimina el objeto Product"""
    if not instance.image:
        print("DEBUG: Producto eliminado sin imagen asociada")
        return
        
    print(f"DEBUG: Intentando eliminar imagen de producto borrado: {instance.image}")
    
    try:
        if hasattr(instance.image, 'path'):
            path = instance.image.path
            print(f"DEBUG: Ruta de archivo a eliminar: {path}")
            
            if os.path.isfile(path):
                os.remove(path)
                print(f"DEBUG: ÉXITO - Archivo eliminado: {path}")
            else:
                print(f"DEBUG: El archivo no existe físicamente: {path}")
        else:
            print("DEBUG: La imagen no tiene atributo 'path'")
    except Exception as e:
        print(f"ERROR detallado al eliminar imagen de producto borrado: {str(e)}")



