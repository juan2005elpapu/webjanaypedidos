from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from datetime import datetime, timedelta
import json
from orders.models import Order, BusinessSettings, OrderModificationRequest


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
    orders = (
        Order.objects.filter(user=request.user)
        .exclude(status='draft')
        .exclude(payment_status='cancelled')
        .select_related('user')
        .prefetch_related('items__product')
    )
    
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
        'total_orders': (
            Order.objects.filter(user=request.user)
            .exclude(status='draft')
            .exclude(payment_status='cancelled')
            .count()
        ),
        'pending_orders': Order.objects.filter(
            user=request.user, status='pending'
        )
        .exclude(payment_status='cancelled')
        .count(),
        'completed_orders': Order.objects.filter(
            user=request.user, status='delivered'
        )
        .exclude(payment_status='cancelled')
        .count(),
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
    
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'), 
        id=order_id, 
        user=request.user
    )
    
    # ✅ CAMBIO: Siempre obtener la solicitud más reciente (si existe)
    modification_request = OrderModificationRequest.objects.filter(
        order=order
    ).order_by('-created_at').first()
    
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
            order.calculated_shipping = settings.delivery_cost
    else:
        order.calculated_shipping = 0
    
    # Calcular total final
    order.calculated_total = order.calculated_subtotal + order.calculated_shipping
    
    # Verificar si califica para envío gratis
    order.qualifies_for_free_shipping = (
        order.delivery_type == 'delivery' and 
        order.calculated_subtotal >= settings.free_delivery_threshold
    )

    # Verificar si se puede cancelar (24 horas antes)
    order.can_be_cancelled = _can_cancel_order(order)

    context = {
        'order': order,
        'settings': settings,
        'modification_request': modification_request,  # ✅ Siempre incluir si existe
        'title': f'Pedido #{order.order_number}'
    }
    
    return render(request, 'history/order_detail.html', context)

def _can_cancel_order(order):
    """
    Función auxiliar para verificar si un pedido se puede cancelar.
    Reglas:
    1. No debe estar cancelado o entregado
    2. No debe estar en preparación, listo o en camino
    3. Debe haber mínimo X días hasta la entrega (configurado en BusinessSettings)
    4. No bloquear por modificaciones si está confirmado
    """
    
    # Verificar estados que no permiten cancelación
    if order.status in ['cancelled', 'delivered', 'preparing', 'ready', 'in_delivery']:
        return False
    
    # Solo bloquear si está en modification_requested, no si está confirmado con historial de modificaciones
    if order.status == 'modification_requested':
        return False
    
    # ✅ CAMBIO: Usar configuración de BusinessSettings
    settings = BusinessSettings.get_settings()
    cancellation_days_limit = settings.cancellation_time_limit_days
    
    # Combinar fecha y hora de entrega deseada
    try:
        delivery_datetime = timezone.datetime.combine(order.desired_date, order.desired_time)
        delivery_datetime = timezone.make_aware(delivery_datetime)
        
        # Verificar que falten al menos X días configurados
        now = timezone.now()
        return delivery_datetime > now + timezone.timedelta(days=cancellation_days_limit)
        
    except Exception:
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

@login_required
def modify_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # ✅ AGREGAR: Obtener configuraciones
    settings = BusinessSettings.get_settings()
    
    # Verificar estado y tiempo usando las configuraciones
    if order.status != 'confirmed':
        messages.error(request, 'Solo se pueden modificar pedidos que estén confirmados.')
        return redirect('history:order_detail', order_id=order_id)
    
    # Verificar si el pedido puede ser modificado (tiempo)
    if not order.can_be_modified:
        messages.error(request, f'Este pedido ya no puede ser modificado (muy cerca de la entrega - límite: {settings.modification_time_limit_hours} horas).')
        return redirect('history:order_detail', order_id=order_id)
    
    # Obtener la última solicitud para mostrar historial (opcional)
    latest_request = OrderModificationRequest.objects.filter(
        order=order
    ).order_by('-created_at').first()
    
    context = {
        'title': f'Modificar Pedido #{order.order_number}',
        'order': order,
        'latest_request': latest_request,
        'settings': settings,  # ✅ AGREGAR settings al contexto
    }
    return render(request, 'history/order_modification.html', context)

@login_required
@require_POST
def submit_modification(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        settings = BusinessSettings.get_settings()  # ✅ AGREGAR
        
        # Verificar: Solo estado del pedido
        if order.status != 'confirmed':
            return JsonResponse({
                'success': False,
                'message': 'Solo se pueden modificar pedidos confirmados.'
            })
        
        # Verificar tiempo límite usando configuraciones
        if not order.can_be_modified:
            return JsonResponse({
                'success': False,
                'message': f'Este pedido ya no puede ser modificado (muy cerca de la entrega - límite: {settings.modification_time_limit_hours} horas).'
            })
        
        data = json.loads(request.body)
        modification_details = data.get('modification_details', '').strip()
        modification_type = data.get('modification_type', 'general') or 'general'
        
        if not modification_details:
            return JsonResponse({
                'success': False,
                'message': 'Por favor, especifica los detalles de la modificación.'
            })
        
        # Crear nueva solicitud de modificación
        modification_request = OrderModificationRequest.objects.create(
            order=order,
            requested_by=request.user,
            modification_type=modification_type,
            current_data={
                'customer_name': order.customer_name,
                'customer_phone': order.customer_phone,
                'delivery_type': order.delivery_type,
                'delivery_address': order.delivery_address,
                'delivery_neighborhood': order.delivery_neighborhood,
                'desired_date': str(order.desired_date),
                'desired_time': str(order.desired_time),
                'notes': order.notes,
            },
            requested_data={
                'modification_details': modification_details,
                'modification_type': modification_type
            },
            reason=modification_details
        )
        
        # Cambiar estado del pedido a 'modification_requested'
        order.status = 'modification_requested'
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Solicitud de modificación enviada exitosamente. Te contactaremos pronto al {settings.contact_phone} o {settings.contact_email}.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al procesar la solicitud: {str(e)}'
        })
