from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Order, OrderItem, OrderModificationRequest, BusinessSettings

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price', 'total_price')
    fields = ('product', 'quantity', 'unit_price', 'total_price')

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        'order_number', 'customer_name', 'status', 'delivery_type_badge', 
        'desired_date', 'desired_time', 'total_formatted', 'payment_status', 'time_status'
    )
    list_editable = ('status', 'payment_status')
    
    list_filter = (
        'status', 'delivery_type', 'payment_status', 'desired_date', 
        'created_at', 'delivery_city'
    )
    search_fields = ('order_number', 'customer_name', 'customer_phone', 'customer_email')
    readonly_fields = ('order_number', 'subtotal', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]
    date_hierarchy = 'desired_date'
    
    fieldsets = (
        ('Información del Pedido', {
            'fields': ('order_number', 'user', 'status', 'delivery_type')
        }),
        ('Cliente', {
            'fields': ('customer_name', 'customer_phone', 'customer_email')
        }),
        ('Entrega', {
            'fields': (
                'delivery_address', 'delivery_neighborhood', 'delivery_city', 
                'delivery_department', 'delivery_references'
            ),
            'classes': ('collapse',)
        }),
        ('Fechas y Horarios', {
            'fields': ('desired_date', 'desired_time', 'estimated_delivery', 'created_at', 'updated_at')
        }),
        ('Pagos', {
            'fields': ('payment_status', 'payment_method')
        }),
        ('Totales', {
            'fields': ('subtotal', 'delivery_fee', 'total')
        }),
        ('Notas', {
            'fields': ('notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
    )
    
    def delivery_type_badge(self, obj):
        icon = '🏪' if obj.delivery_type == 'pickup' else '🚚'
        return f"{icon} {obj.get_delivery_type_display()}"
    delivery_type_badge.short_description = 'Entrega'
    
    def total_formatted(self, obj):
        return f"${obj.total:,.0f}"
    total_formatted.short_description = 'Total'
    
    def time_status(self, obj):
        if obj.desired_date:
            today = timezone.now().date()
            if obj.desired_date == today:
                return format_html('<span style="color: #f59e0b; font-weight: bold;">HOY</span>')
            elif obj.desired_date < today:
                return format_html('<span style="color: #ef4444;">Vencido</span>')
            else:
                days = (obj.desired_date - today).days
                return f"En {days} día{'s' if days > 1 else ''}"
        return '-'
    time_status.short_description = 'Entrega'

@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order_number', 'product', 'quantity', 'unit_price', 'total_price')
    list_filter = ('order__status', 'product__category', 'order__delivery_type')
    search_fields = ('order__order_number', 'order__customer_name', 'product__name')
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'Pedido'

@admin.register(OrderModificationRequest)
class OrderModificationRequestAdmin(ModelAdmin):
    list_display = ('order', 'modification_type', 'status', 'requested_by', 'created_at')
    list_filter = ('status', 'modification_type', 'created_at')
    search_fields = ('order__order_number', 'order__customer_name', 'reason')
    readonly_fields = ('created_at', 'reviewed_at')

@admin.register(BusinessSettings)
class BusinessSettingsAdmin(ModelAdmin):
    list_display = ('business_name', 'contact_email', 'minimum_order_amount', 'free_delivery_threshold')
    
    fieldsets = (
        ('Información del Negocio', {
            'fields': ('business_name', 'address', 'city', 'department')
        }),
        ('Contacto', {
            'fields': ('contact_email', 'contact_phone', 'whatsapp_number')
        }),
        ('Configuración de Pedidos', {
            'fields': ('minimum_order_amount', 'free_delivery_threshold', 'min_advance_days', 'max_advance_days')
        }),
        ('Horarios', {
            'fields': ('delivery_start_time', 'delivery_end_time')
        }),
        ('Métodos de Pago', {
            'fields': ('accept_cash', 'accept_transfer', 'accept_card', 'accept_pse')
        }),
    )
    
    def has_add_permission(self, request):
        # Solo permitir una configuración
        return not BusinessSettings.objects.exists()
