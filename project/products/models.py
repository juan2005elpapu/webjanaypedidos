from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from decimal import Decimal, ROUND_HALF_UP
from cloudinary.models import CloudinaryField
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from cloudinary.uploader import destroy

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
    image = CloudinaryField(
        "product_image",
        blank=True,
        null=True,
        overwrite=True,
        resource_type="image",
        transformation={"fetch_format": "auto", "quality": "auto"},
        folder="products"
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
            return self.image.build_url(secure=True, fetch_format="auto", quality="auto")
        return ""

def _delete_cloudinary_image(image_field):
    public_id = getattr(image_field, "public_id", None)
    if public_id:
        try:
            destroy(public_id, invalidate=True)
        except Exception:
            pass

@receiver(pre_save, sender=Product)
def delete_replaced_image(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        previous = Product.objects.get(pk=instance.pk)
    except Product.DoesNotExist:
        return
    prev_id = getattr(previous.image, "public_id", None)
    new_id = getattr(instance.image, "public_id", None)
    if prev_id and prev_id != new_id:
        _delete_cloudinary_image(previous.image)

@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):
    if instance.image:
        _delete_cloudinary_image(instance.image)



