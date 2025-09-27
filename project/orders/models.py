from django.db import models
from django.contrib.auth.models import User
from products.models import Product
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import random
import string
from datetime import datetime
from django.utils import timezone
        

class Order(models.Model):
    ORDER_STATUS = [
        ('draft', 'Borrador'),
        ('pending', 'Pendiente confirmación'),
        ('confirmed', 'Confirmado'),
        ('preparing', 'En preparación'),
        ('ready', 'Listo para entrega'),
        ('in_delivery', 'En camino'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado'),
        ('modification_requested', 'Modificación solicitada'),
    ]
    
    DELIVERY_TYPE = [
        ('pickup', 'Recoger en tienda'),
        ('delivery', 'Delivery'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmado'),
        ('cancelled', 'Cancelado'),
    ]
    
    PAYMENT_METHOD = [
        ('cash', 'Efectivo'),
        ('transfer', 'Transferencia'),
        ('card', 'Tarjeta'),
        ('pse', 'PSE'),
        ('pay_later', 'Pagar después'),
    ]
    
    # Información básica del pedido
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Usuario')
    order_number = models.CharField(max_length=20, unique=True, verbose_name='Número de pedido')
    status = models.CharField(max_length=30, choices=ORDER_STATUS, default='draft', verbose_name='Estado')
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_TYPE, verbose_name='Tipo de entrega')
    
    # Información del cliente
    customer_name = models.CharField(max_length=100, verbose_name='Nombre del cliente')
    customer_phone = models.CharField(max_length=20, verbose_name='Teléfono')
    customer_email = models.EmailField(blank=True, verbose_name='Email')
    
    # Información de ubicación (solo para delivery)
    delivery_address = models.TextField(blank=True, null=True, verbose_name='Dirección de entrega')
    delivery_neighborhood = models.CharField(max_length=100, blank=True, verbose_name='Barrio')
    delivery_city = models.CharField(max_length=100, default='Villanueva', verbose_name='Ciudad')
    delivery_department = models.CharField(max_length=100, default='Casanare', verbose_name='Departamento')
    delivery_references = models.TextField(blank=True, verbose_name='Referencias de ubicación')
    
    # Fechas y horarios
    desired_date = models.DateField(verbose_name='Fecha deseada')
    desired_time = models.TimeField(verbose_name='Hora deseada')
    estimated_delivery = models.DateTimeField(blank=True, null=True, verbose_name='Entrega estimada')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')
    
    # Totales y costos
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Subtotal')
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Costo de envío')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Total')
    
    # Información de pago
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending', verbose_name='Estado del pago')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD, blank=True, verbose_name='Método de pago')
    
    # Notas y comentarios
    notes = models.TextField(blank=True, verbose_name='Notas del cliente')
    admin_notes = models.TextField(blank=True, verbose_name='Notas del administrador')
    
    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Genera un número único para el pedido"""

        # Formato: JY + YYYYMMDD + NNNN (4 dígitos aleatorios)
        date_part = datetime.now().strftime('%Y%m%d')  # 8 dígitos: 20250804
        random_part = ''.join(random.choices(string.digits, k=4))  # 4 dígitos
        
        order_number = f"JY{date_part}{random_part}"  # JY20250804NNNN = 14 dígitos
        
        # Verificar si ya existe
        while Order.objects.filter(order_number=order_number).exists():
            random_part = ''.join(random.choices(string.digits, k=4))
            order_number = f"JY{date_part}{random_part}"
        
        return order_number
    
    def __str__(self):
        return f"{self.order_number} - {self.customer_name} ({self.get_status_display()})"
    
    @property
    def desired_datetime(self):
        """Combina fecha y hora deseada"""
        if self.desired_date and self.desired_time:
            return datetime.combine(self.desired_date, self.desired_time)
        return None
    
    @property
    def is_within_allowed_timeframe(self):
        """Verifica si la fecha está dentro del rango permitido (2 días - 3 meses)"""
        if not self.desired_date:
            return False
        
        today = timezone.now().date()
        min_date = today + timedelta(days=2)
        max_date = today + timedelta(days=90)  # 3 meses aproximadamente
        
        return min_date <= self.desired_date <= max_date
    
    @property
    def days_until_delivery(self):
        """Días hasta la entrega"""
        if self.desired_date:
            return (self.desired_date - timezone.now().date()).days
        return None
    
    @property
    def can_be_modified(self):
        """
        Verifica si el pedido puede ser modificado.
        Solo se puede modificar hasta X horas antes de la entrega (configurado en BusinessSettings),
        y únicamente si está en estado 'confirmed'.
        """
        if self.status in ['cancelled', 'delivered']:
            return False
        
        # Solo puede modificar si está confirmado
        if self.status != 'confirmed':
            return False
            
        # ✅ CAMBIO: Usar configuración de BusinessSettings
        settings = BusinessSettings.get_settings()
        modification_hours_limit = settings.modification_time_limit_hours
        
        # Verificar que no sea muy cerca de la entrega
        now = timezone.now()
        delivery_datetime = timezone.datetime.combine(self.desired_date, self.desired_time)
        delivery_datetime = timezone.make_aware(delivery_datetime)
        
        return delivery_datetime > now + timezone.timedelta(hours=modification_hours_limit)
    
    @property
    def meets_minimum_order(self):
        """Verifica si cumple con el pedido mínimo de 50mil COP"""
        return self.subtotal >= Decimal('50000')
    
    @property
    def qualifies_for_free_delivery(self):
        """Verifica si califica para envío gratis (500mil COP)"""
        return self.subtotal >= Decimal('500000')
    
    def calculate_delivery_fee(self):
        """Calcula el costo de envío basado en ubicación y cantidad"""
        if self.delivery_type == 'pickup':
            return Decimal('0')
        
        if self.qualifies_for_free_delivery:
            return Decimal('0')
        
        # ✅ CAMBIAR: Usar configuración en lugar de valor fijo
        settings = BusinessSettings.get_settings()
        return settings.delivery_cost
    
    
    def calculate_total(self):
        """Calcular el total basado en los items"""
        self.subtotal = sum(item.total_price for item in self.items.all())
        
        if self.delivery_type == 'delivery':
            self.delivery_fee = self.calculate_delivery_fee()
        else:
            self.delivery_fee = Decimal('0')
            
        self.total = self.subtotal + self.delivery_fee
        self.save()
    
    def get_delivery_time_slots(self):
        """Obtiene los horarios disponibles para entrega (5am - 9pm)"""
        slots = []
        for hour in range(5, 22):  # 5am a 9pm
            slots.append(f"{hour:02d}:00")
            slots.append(f"{hour:02d}:30")
        return slots


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Pedido')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Producto')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Cantidad')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio unitario')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Item del pedido'
        verbose_name_plural = 'Items del pedido'
    
    def save(self, *args, **kwargs):
        self.unit_price = self.product.price
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        # Actualizar total del pedido
        self.order.calculate_total()
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity} - ${self.total_price:,.0f}"
    
    @property
    def has_customizations(self):
        """Verifica si tiene instrucciones especiales"""
        return bool(self.special_instructions)


class OrderModificationRequest(models.Model):
    """Modelo para solicitudes de modificación de pedidos"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name='Pedido')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Solicitado por')
    
    # Información de la modificación
    modification_type = models.CharField(
        max_length=50, 
        default='general',
        verbose_name='Tipo de modificación',
        help_text='Ejemplo: cambio de fecha, cambio de dirección, etc.'
    )
    current_data = models.JSONField(verbose_name='Datos actuales')
    requested_data = models.JSONField(verbose_name='Datos solicitados')
    reason = models.TextField(verbose_name='Razón de la modificación')
    
    admin_response = models.TextField(blank=True, verbose_name='Respuesta del administrador')
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='reviewed_modifications',
        verbose_name='Revisado por'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de solicitud')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de revisión')
    
    class Meta:
        verbose_name = 'Solicitud de modificación'
        verbose_name_plural = 'Solicitudes de modificación'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Modificación {self.order.order_number} - {self.modification_type.title()}"
    
    @property
    def status(self):
        """El estado se obtiene del pedido asociado"""
        return self.order.status
    
    @property
    def status_display(self):
        """Obtiene el display del estado del pedido"""
        return self.order.get_status_display()


class BusinessSettings(models.Model):
    """Configuraciones del negocio"""
    # Configuraciones de pedidos
    minimum_order_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('50000'),
        verbose_name='Monto mínimo de pedido'
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('500000'),
        verbose_name='Monto para envío gratis'
    )
    delivery_cost = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('5000'),
        verbose_name='Costo de envío',
        help_text='Precio del envío cuando no califica para envío gratis'
    )
    
    min_advance_days = models.PositiveIntegerField(default=2, verbose_name='Días mínimos de anticipación')
    max_advance_days = models.PositiveIntegerField(default=90, verbose_name='Días máximos de anticipación')
    
    # ✅ AGREGAR: Nuevos campos para tiempos de modificación y cancelación
    modification_time_limit_hours = models.PositiveIntegerField(
        default=4, 
        verbose_name='Tiempo límite para modificaciones (horas)',
        help_text='Horas antes de la entrega hasta cuando se pueden solicitar modificaciones'
    )
    cancellation_time_limit_days = models.PositiveIntegerField(
        default=1, 
        verbose_name='Tiempo límite para cancelaciones (días)',
        help_text='Días antes de la entrega hasta cuando se pueden cancelar pedidos'
    )
    
    # Información de contacto
    business_name = models.CharField(max_length=100, default='Janay', verbose_name='Nombre del negocio')
    contact_email = models.EmailField(verbose_name='Email de contacto')
    contact_phone = models.CharField(max_length=20, verbose_name='Teléfono de contacto')
    whatsapp_number = models.CharField(max_length=20, blank=True, verbose_name='WhatsApp')
    
    # Ubicación
    address = models.TextField(verbose_name='Dirección del negocio')
    city = models.CharField(max_length=100, default='Villanueva', verbose_name='Ciudad')
    department = models.CharField(max_length=100, default='Casanare', verbose_name='Departamento')
    
    # Horarios
    delivery_start_time = models.TimeField(default='05:00', verbose_name='Hora inicio entregas')
    delivery_end_time = models.TimeField(default='21:00', verbose_name='Hora fin entregas')
    
    # Configuraciones de pago
    accept_cash = models.BooleanField(default=True, verbose_name='Acepta efectivo')
    accept_transfer = models.BooleanField(default=True, verbose_name='Acepta transferencia')
    accept_card = models.BooleanField(default=True, verbose_name='Acepta tarjeta')
    accept_pse = models.BooleanField(default=False, verbose_name='Acepta PSE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración del negocio'
        verbose_name_plural = 'Configuraciones del negocio'
    
    def __str__(self):
        return f"Configuraciones {self.business_name}"
    
    @classmethod
    def get_settings(cls):
        """Obtiene la configuración del negocio, crea una por defecto si no existe"""
        settings = cls.objects.first()
        if not settings:
            # Crear configuración por defecto
            settings = cls.objects.create(
                business_name='Janay',
                contact_email='info@janay.com',
                contact_phone='+57 300 123 4567',
                address='Villanueva, Casanare, Colombia',
                city='Villanueva',
                department='Casanare',
                delivery_cost=Decimal('5000'),
                modification_time_limit_hours=4,  # ✅ AGREGAR valores por defecto
                cancellation_time_limit_days=1
            )
        return settings
