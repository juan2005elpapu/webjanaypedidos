from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from unfold.admin import ModelAdmin
from .models import Order, OrderItem, OrderModificationRequest, BusinessSettings
from django.contrib.admin import SimpleListFilter

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('unit_price', 'total_price')
    fields = ('product', 'quantity', 'unit_price', 'total_price')

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = (
        'order_number', 'customer_name', 'status', 'delivery_type_badge',
        'desired_date', 'desired_time', 'total_formatted',
        'payment_method_display', 'payment_status', 'time_status'
    )
    list_editable = ('status', 'payment_status')
    
    list_filter = (
        'status', 'delivery_type', 'payment_status', 'desired_date', 
        'created_at', 'delivery_city'
    )
    search_fields = ('order_number', 'customer_name', 'customer_phone', 'customer_email')
    readonly_fields = ('order_number', 'subtotal', 'total', 'created_at', 'updated_at', 'payment_reference')
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
            'fields': ('payment_status', 'payment_method', 'payment_reference')
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

    def payment_method_display(self, obj):
        return obj.get_payment_method_display()
    payment_method_display.short_description = 'Método de pago'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.GET.get("payment_status__exact"):
            return qs
        return qs.exclude(payment_status="cancelled")

class OrderIdFilter(SimpleListFilter):
    title = 'Pedido (ID)'
    parameter_name = 'order_id'

    def lookups(self, request, model_admin):
        ids = (
            model_admin.model.objects.order_by('order__id')
            .values_list('order__id', 'order__order_number')
            .distinct()[:50]
        )
        return [(str(order_id), f"#{order_number} (ID {order_id})") for order_id, order_number in ids]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(order__id=self.value())
        return queryset

@admin.register(OrderItem)
class OrderItemAdmin(ModelAdmin):
    list_display = ('order_number', 'product', 'quantity', 'unit_price', 'total_price')
    list_filter = ('order__status', 'product__category', 'order__delivery_type', OrderIdFilter)
    search_fields = ('order__order_number', 'order__customer_name', 'product__name')
    
    def order_number(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
    order_number.short_description = 'Pedido'

@admin.register(OrderModificationRequest)
class OrderModificationRequestAdmin(ModelAdmin):
    list_display = ('order_info', 'modification_type', 'order_status_link', 'requested_by', 'created_at')
    list_filter = ('modification_type', 'order__status', 'created_at')
    search_fields = ('order__order_number', 'order__customer_name', 'reason')
    
    readonly_fields = (
        'created_at', 'reviewed_at', 'order_link', 
        'current_data_formatted', 'requested_data_formatted', 'manage_order_status'
    )
    
    fieldsets = (
        ('Información de la Solicitud', {
            'fields': ('order_link', 'requested_by', 'modification_type', 'created_at')
        }),
        ('Detalles de la Modificación', {
            'fields': ('reason',),
        }),
        ('Datos Actuales vs Solicitados', {
            'fields': ('current_data_formatted', 'requested_data_formatted'),
            'classes': ('wide',)
        }),
        ('Gestión del Pedido', {
            'fields': ('manage_order_status',),
            'description': 'Gestionar el estado del pedido asociado:'
        }),
        ('Respuesta del Administrador', {
            'fields': ('admin_response', 'reviewed_by', 'reviewed_at'),
        }),
    )

    def get_queryset(self, request):
        """
        ✅ FILTRAR: Solo mostrar solicitudes de pedidos con estado 'modification_requested'
        y solo la más reciente de cada pedido
        """
        qs = super().get_queryset(request)
        
        # Filtrar solo pedidos con estado 'modification_requested'
        qs = qs.filter(order__status='modification_requested')
        
        # Para cada pedido, obtener solo la solicitud más reciente
        # Esto se hace con una subconsulta que agrupa por order y toma el max(id)
        from django.db.models import Max
        
        # Obtener el ID más reciente de cada pedido con estado modification_requested
        latest_requests_ids = (
            qs.values('order')
            .annotate(latest_id=Max('id'))
            .values_list('latest_id', flat=True)
        )
        
        # Filtrar solo esos IDs
        qs = qs.filter(id__in=latest_requests_ids)
        
        return qs.order_by('-created_at')
    
    # ✅ AGREGAR: Método para mostrar contador en el admin
    def changelist_view(self, request, extra_context=None):
        """Agregar contexto adicional para mostrar información útil"""
        extra_context = extra_context or {}
        
        # Contar pedidos con modificaciones pendientes
        total_pending = Order.objects.filter(status='modification_requested').count()
        extra_context['subtitle'] = f"Mostrando {total_pending} pedido{'s' if total_pending != 1 else ''} con modificaciones pendientes"
        
        return super().changelist_view(request, extra_context=extra_context)
    
    def order_info(self, obj):
        """Mostrar información básica del pedido"""
        return f"{obj.order.order_number} - {obj.order.customer_name}"
    order_info.short_description = 'Información del Pedido'
    
    def order_link(self, obj):
        """Link directo al pedido en el admin de Order"""
        if obj.pk:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html(
                '<a href="{}" class="button" target="_blank">Ver/Editar Pedido {}</a>',
                url, obj.order.order_number
            )
        return "Guarda primero"
    order_link.short_description = 'Gestionar Pedido'
    
    def order_status_link(self, obj):
        """Estado del pedido CON link al pedido"""
        colors = {
            'pending': '#f59e0b',
            'confirmed': '#3b82f6',
            'preparing': '#8b5cf6',
            'ready': '#f97316',
            'delivered': '#10b981',
            'cancelled': '#ef4444',
            'modification_requested': '#ec4899'
        }
        color = colors.get(obj.order.status, '#6b7280')
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html(
            '<a href="{}" style="color: {}; font-weight: bold; text-decoration: none;">{}</a>',
            url, color, obj.order.get_status_display()
        )
    order_status_link.short_description = 'Estado (Click para gestionar)'
    
    def current_data_formatted(self, obj):
        """Formatear los datos actuales de manera legible"""
        if obj.current_data:
            html = "<div style='background: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #dee2e6;'>"
            html += "<h4 style='margin: 0 0 10px 0; color: #495057; font-size: 14px;'>📋 Información Actual del Pedido</h4>"
            for key, value in obj.current_data.items():
                if value:  # Solo mostrar si tiene valor
                    field_name = key.replace('_', ' ').title()
                    html += f"<div style='margin: 8px 0; padding: 5px 0; border-bottom: 1px solid #e9ecef;'>"
                    html += f"<strong style='color: #212529; display: inline-block; min-width: 120px;'>{field_name}:</strong>"
                    html += f"<span style='color: #495057; margin-left: 10px;'>{value}</span>"
                    html += "</div>"
            html += "</div>"
            return format_html(html)
        return format_html('<div style="color: #6c757d; font-style: italic;">Sin datos</div>')
    current_data_formatted.short_description = 'Datos Actuales del Pedido'
    
    def requested_data_formatted(self, obj):
        """Formatear los datos solicitados de manera legible"""
        if obj.requested_data:
            html = "<div style='background: #fff3cd; padding: 15px; border-radius: 6px; border: 1px solid #ffeaa7; border-left: 4px solid #f39c12;'>"
            html += "<h4 style='margin: 0 0 10px 0; color: #856404; font-size: 14px;'>🔄 Cambios Solicitados</h4>"
            for key, value in obj.requested_data.items():
                if value:  # Solo mostrar si tiene valor
                    field_name = key.replace('_', ' ').title()
                    html += f"<div style='margin: 8px 0; padding: 5px 0; border-bottom: 1px solid #f7dc6f;'>"
                    html += f"<strong style='color: #856404; display: inline-block; min-width: 120px;'>{field_name}:</strong>"
                    html += f"<span style='color: #6c5ce7; margin-left: 10px; font-weight: 500;'>{value}</span>"
                    html += "</div>"
            html += "</div>"
            return format_html(html)
        return format_html('<div style="color: #6c757d; font-style: italic;">Sin datos</div>')
    requested_data_formatted.short_description = 'Cambios Solicitados'
    
    def manage_order_status(self, obj):
        """Gestión rápida del estado del pedido"""
        if obj.pk:
            current_status = obj.order.get_status_display()
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            
            # Colores para estados
            status_colors = {
                'pending': '#f59e0b',
                'confirmed': '#3b82f6',
                'preparing': '#8b5cf6',
                'ready': '#f97316',
                'delivered': '#10b981',
                'cancelled': '#ef4444',
                'modification_requested': '#ec4899'
            }
            
            color = status_colors.get(obj.order.status, '#6b7280')
            
            html = f'''
            <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; border: 1px solid #dee2e6;">
                <div style="margin-bottom: 15px;">
                    <strong style="color: #495057;">Estado actual del pedido:</strong>
                    <span style="color: {color}; font-weight: bold; margin-left: 8px;">
                        {current_status}
                    </span>
                </div>
                
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <a href="{url}" 
                       style="display: inline-block; padding: 8px 16px; background: #007cba; color: white; text-decoration: none; border-radius: 4px; font-size: 13px; text-align: center;"
                       target="_blank">
                        🔧 Gestionar Estado del Pedido
                    </a>
                </div>
            </div>
            '''
            
            return format_html(html)
        return format_html('<div style="color: #6c757d; font-style: italic;">Guarda primero para gestionar el estado</div>')
    manage_order_status.short_description = 'Gestión de Estado'
    
    def get_readonly_fields(self, request, obj=None):
        """Hacer ciertos campos de solo lectura"""
        readonly = list(self.readonly_fields)
        if obj:  # Si es edición
            readonly.extend(['order', 'requested_by', 'modification_type', 'current_data', 'requested_data', 'reason'])
        return readonly

    # ✅ OPCIONAL: Agregar acción masiva para aprobar modificaciones
    def approve_modifications(self, request, queryset):
        """Acción para aprobar múltiples modificaciones de una vez"""
        count = 0
        for modification in queryset:
            if modification.order.status == 'modification_requested':
                modification.order.status = 'confirmed'
                modification.order.save()
                count += 1
        
        self.message_user(
            request,
            f"{count} solicitud{'es' if count != 1 else ''} aprobada{'s' if count != 1 else ''} y pedido{'s' if count != 1 else ''} confirmado{'s' if count != 1 else ''}."
        )
    approve_modifications.short_description = "Aprobar modificaciones seleccionadas"
    
    actions = ['approve_modifications']

@admin.register(BusinessSettings)
class BusinessSettingsAdmin(ModelAdmin):
    list_display = ('business_name', 'contact_email', 'minimum_order_amount', 'free_delivery_threshold', 'delivery_cost')
    
    fieldsets = (
        ('Información del Negocio', {
            'fields': ('business_name', 'address', 'city', 'department')
        }),
        ('Contacto', {
            'fields': ('contact_email', 'contact_phone', 'whatsapp_number')
        }),
        ('Configuración de Pedidos', {
            'fields': ('minimum_order_amount', 'free_delivery_threshold', 'delivery_cost', 'min_advance_days', 'max_advance_days')
        }),
        # ✅ AGREGAR: Nueva sección para tiempos de modificación y cancelación
        ('Tiempos Límite', {
            'fields': ('modification_time_limit_hours', 'cancellation_time_limit_days'),
            'description': 'Configure los tiempos límite para modificaciones y cancelaciones de pedidos'
        }),
        ('Horarios', {
            'fields': ('delivery_start_time', 'delivery_end_time')
        }),
        ('Métodos de Pago', {
            'fields': ('accept_cash', 'accept_wompi')
        }),
        ('Configuración Wompi', {
            'fields': ('wompi_environment', 'wompi_public_key', 'wompi_private_key', 'wompi_integrity_key'),
            'description': 'Configura las llaves proporcionadas por Wompi para habilitar pagos en línea.'
        }),
    )
    
    def has_add_permission(self, request):
        # Solo permitir una configuración
        return not BusinessSettings.objects.exists()
