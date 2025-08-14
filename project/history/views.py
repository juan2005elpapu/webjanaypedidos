from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
import json
from orders.models import Order, BusinessSettings


@login_required
def order_history_list(request):
    """Vista principal del historial de pedidos del usuario"""
    
    # ✅ OBTENER configuraciones PRIMERO antes del loop
    settings = BusinessSettings.get_settings()
    
    # Filtros de búsqueda
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # ✅ USAR directamente el modelo Order existente
    orders = Order.objects.filter(
        user=request.user
    ).exclude(status='draft').select_related('user').prefetch_related('items__product')
    
    # Aplicar filtros
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Ordenar por fecha más reciente
    orders = orders.order_by('-created_at')
    

    for i, order in enumerate(orders):
        # Calcular subtotal de productos
        items = order.items.all()
        order.calculated_subtotal = sum(item.total_price for item in items)    
        # Calcular costo de envío basado en configuración actual del negocio
        if order.delivery_type == 'delivery':
            if order.calculated_subtotal >= settings.free_delivery_threshold:
                order.calculated_shipping = 0
            else:
                order.calculated_shipping = settings.delivery_cost  # ✅ CAMBIO: Usar configuración del negocio
        else:
            order.calculated_shipping = 0
        
        # Calcular total final
        order.calculated_total = order.calculated_subtotal + order.calculated_shipping
        
        # Verificar si califica para envío gratis
        order.qualifies_for_free_shipping = (
            order.delivery_type == 'delivery' and 
            order.calculated_subtotal >= settings.free_delivery_threshold
        )
        
        # ✅ AGREGAR: Verificar si se puede cancelar (24 horas antes)
        order.can_be_cancelled = _can_cancel_order(order)
        
    # Paginación
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    
    # ✅ USAR los métodos y campos existentes del modelo Order
    stats = {
        'total_orders': Order.objects.filter(user=request.user).exclude(status='draft').count(),
        'pending_orders': Order.objects.filter(user=request.user, status='pending').count(),
        'completed_orders': Order.objects.filter(user=request.user, status='delivered').count(),
    }
    
    context = {
        'page_obj': page_obj,
        'orders': page_obj,
        'stats': stats,
        'search_query': search_query,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Order.ORDER_STATUS,
        'settings': settings,  # ✅ AGREGAR settings al contexto
        'title': 'Historial de Pedidos'
    }
    
    
    return render(request, 'history/order_list.html', context)

@login_required
def order_detail_history(request, order_id):
    """Vista de detalle de un pedido específico"""
    
    # ✅ USAR directamente el modelo Order existente
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'), 
        id=order_id, 
        user=request.user
    )
    
    
    # ✅ CALCULAR totales correctos igual que en la lista
    settings = BusinessSettings.get_settings()
    
    # Calcular subtotal de productos
    items = order.items.all()
    order.calculated_subtotal = sum(item.total_price for item in items)   
    # Calcular costo de envío basado en configuración actual del negocio
    if order.delivery_type == 'delivery':
        if order.calculated_subtotal >= settings.free_delivery_threshold:
            order.calculated_shipping = 0
        else:
            order.calculated_shipping = settings.delivery_cost  # ✅ CAMBIO: Usar configuración del negocio
    else:
        order.calculated_shipping = 0
    
    # Calcular total final
    order.calculated_total = order.calculated_subtotal + order.calculated_shipping
    
    # Verificar si califica para envío gratis
    order.qualifies_for_free_shipping = (
        order.delivery_type == 'delivery' and 
        order.calculated_subtotal >= settings.free_delivery_threshold
    )

    # ✅ AGREGAR: Verificar si se puede cancelar (24 horas antes)
    order.can_be_cancelled = _can_cancel_order(order)

    context = {
        'order': order,
        'settings': settings,
        'title': f'Pedido #{order.order_number}'
    }
    
    
    return render(request, 'history/order_detail.html', context)

def _can_cancel_order(order):
    """
    Función auxiliar para verificar si un pedido se puede cancelar.
    Reglas:
    1. No debe estar cancelado o entregado
    2. No debe estar en preparación o listo
    3. Debe haber mínimo 24 horas hasta la entrega
    """
    
    # Verificar estados que no permiten cancelación
    if order.status in ['cancelled', 'delivered', 'preparing', 'ready']:
        return False
    
    # Combinar fecha y hora de entrega deseada
    try:
        # Crear datetime combinando fecha y hora deseadas
        delivery_datetime = datetime.combine(order.desired_date, order.desired_time)
        
        # Obtener datetime actual
        now = datetime.now()
        
        # Calcular diferencia
        time_until_delivery = delivery_datetime - now
        
        # Verificar si hay al menos 24 horas (1 día)
        return time_until_delivery.total_seconds() >= 24 * 60 * 60  # 24 horas en segundos
        
    except Exception:
        # Si hay algún error en el cálculo, por seguridad no permitir cancelación
        return False

@login_required
@require_http_methods(["POST"])
def cancel_order(request, order_id):
    """Vista para cancelar un pedido"""
    
    try:
        # Obtener el pedido del usuario
        order = get_object_or_404(
            Order.objects.select_related('user'), 
            id=order_id, 
            user=request.user
        )
        
        # ✅ VERIFICAR con la nueva función
        if not _can_cancel_order(order):
            # Determinar el mensaje específico según la razón
            if order.status in ['cancelled', 'delivered']:
                message = 'Este pedido no se puede cancelar porque ya está cancelado o entregado'
            elif order.status in ['preparing', 'ready']:
                message = 'No se puede cancelar un pedido que ya está en preparación'
            else:
                # Verificar si es por el tiempo
                delivery_datetime = datetime.combine(order.desired_date, order.desired_time)
                now = datetime.now()
                time_until_delivery = delivery_datetime - now
                
                if time_until_delivery.total_seconds() < 24 * 60 * 60:
                    hours_remaining = int(time_until_delivery.total_seconds() / 3600)
                    if hours_remaining <= 0:
                        message = 'No se puede cancelar un pedido programado para hoy'
                    else:
                        message = f'No se puede cancelar. Solo quedan {hours_remaining} horas para la entrega (mínimo 24 horas requeridas)'
                else:
                    message = 'Este pedido no se puede cancelar'
            
            return JsonResponse({
                'success': False,
                'message': message
            })
        
        # Cambiar el estado a cancelado
        order.status = 'cancelled'
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Pedido cancelado exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error interno del servidor'
        })
