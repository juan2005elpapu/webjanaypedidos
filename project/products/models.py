from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal, ROUND_HALF_UP
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings

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
        decimal_places=0,
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
    image = models.CharField(
        'Imagen',
        max_length=500,
        blank=True,
        null=True
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
        if self.price:
            self.price = self.price.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

    @property
    def formatted_price(self):
        return f"${self.price:,.0f}"

    def image_secure_url(self):
        if self.image:
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{self.image}"
        return ""


@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):
    if instance.image:
        try:
            from .supabase_storage import SupabaseStorage
            storage = SupabaseStorage()
            storage.delete(instance.image)
        except Exception:
            pass



