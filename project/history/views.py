from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from orders.models import Order, BusinessSettings  # ✅ IMPORTAR BusinessSettings también
import logging

# Configurar logger
logger = logging.getLogger(__name__)

@login_required
def order_history_list(request):
    """Vista principal del historial de pedidos del usuario"""
    
    logger.info(f"🔍 Iniciando order_history_list para usuario: {request.user.username}")
    
    # ✅ OBTENER configuraciones PRIMERO antes del loop
    settings = BusinessSettings.get_settings()
    logger.info(f"⚙️ Settings obtenidos - Free delivery threshold: ${settings.free_delivery_threshold}")
    
    # Filtros de búsqueda
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    logger.info(f"🔎 Filtros aplicados - Search: '{search_query}', Status: '{status_filter}', Date from: '{date_from}', Date to: '{date_to}'")
    
    # ✅ USAR directamente el modelo Order existente
    orders = Order.objects.filter(
        user=request.user
    ).exclude(status='draft').select_related('user').prefetch_related('items__product')
    
    logger.info(f"📦 Pedidos iniciales encontrados: {orders.count()}")
    
    # Aplicar filtros
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )
        logger.info(f"🔍 Después de filtro de búsqueda: {orders.count()} pedidos")
    
    if status_filter:
        orders = orders.filter(status=status_filter)
        logger.info(f"📊 Después de filtro de estado: {orders.count()} pedidos")
    
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
        logger.info(f"📅 Después de filtro fecha desde: {orders.count()} pedidos")
    
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
        logger.info(f"📅 Después de filtro fecha hasta: {orders.count()} pedidos")
    
    # Ordenar por fecha más reciente
    orders = orders.order_by('-created_at')
    
    # ✅ RECALCULAR TOTALES para pedidos antiguos que no tienen delivery_fee calculado
    logger.info("💰 Iniciando recálculo de totales...")
    
    for i, order in enumerate(orders):
        logger.info(f"📝 Procesando pedido {i+1}: #{order.order_number}")
        
        # Calcular subtotal de productos
        items = order.items.all()
        order.calculated_subtotal = sum(item.total_price for item in items)
        logger.info(f"   💵 Subtotal calculado: ${order.calculated_subtotal}")
        logger.info(f"   🚚 Tipo de entrega: {order.delivery_type}")
        
        # Calcular costo de envío basado en configuración actual del negocio
        if order.delivery_type == 'delivery':
            if order.calculated_subtotal >= settings.free_delivery_threshold:
                order.calculated_shipping = 0
                logger.info(f"   ✅ Envío GRATIS (subtotal ${order.calculated_subtotal} >= threshold ${settings.free_delivery_threshold})")
            else:
                order.calculated_shipping = 5000  # Costo fijo de envío
                logger.info(f"   💸 Envío CON COSTO: $5000 (subtotal ${order.calculated_subtotal} < threshold ${settings.free_delivery_threshold})")
        else:
            order.calculated_shipping = 0
            logger.info(f"   🏪 Pickup - Sin costo de envío")
        
        # Calcular total final
        order.calculated_total = order.calculated_subtotal + order.calculated_shipping
        logger.info(f"   🧾 Total final: ${order.calculated_total} (${order.calculated_subtotal} + ${order.calculated_shipping})")
        
        # Verificar si califica para envío gratis
        order.qualifies_for_free_shipping = (
            order.delivery_type == 'delivery' and 
            order.calculated_subtotal >= settings.free_delivery_threshold
        )
        logger.info(f"   🎯 Califica para envío gratis: {order.qualifies_for_free_shipping}")
        
        # Log del pedido original para comparar
        logger.info(f"   📊 Total original en BD: ${getattr(order, 'total', 'N/A')}")
        logger.info(f"   📊 Delivery fee original en BD: ${getattr(order, 'delivery_fee', 'N/A')}")
        logger.info(f"   ---")
    
    logger.info(f"✅ Recálculo completado para {orders.count()} pedidos")
    
    # Paginación
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    logger.info(f"📄 Paginación: Página {page_number or 1}, {len(page_obj)} pedidos en esta página")
    
    # ✅ USAR los métodos y campos existentes del modelo Order
    stats = {
        'total_orders': Order.objects.filter(user=request.user).exclude(status='draft').count(),
        'pending_orders': Order.objects.filter(user=request.user, status='pending').count(),
        'completed_orders': Order.objects.filter(user=request.user, status='delivered').count(),
    }
    
    logger.info(f"📈 Stats calculados: {stats}")
    
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
    
    logger.info("🚀 Context preparado, renderizando template...")
    
    return render(request, 'history/order_list.html', context)

@login_required
def order_detail_history(request, order_id):
    """Vista de detalle de un pedido específico"""
    
    logger.info(f"🔍 Iniciando order_detail_history para pedido: {order_id}, usuario: {request.user.username}")
    
    # ✅ USAR directamente el modelo Order existente
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'), 
        id=order_id, 
        user=request.user
    )
    
    logger.info(f"📦 Pedido encontrado: #{order.order_number}")
    
    # ✅ CALCULAR totales correctos igual que en la lista
    settings = BusinessSettings.get_settings()
    logger.info(f"⚙️ Settings obtenidos - Free delivery threshold: ${settings.free_delivery_threshold}")
    
    # Calcular subtotal de productos
    items = order.items.all()
    order.calculated_subtotal = sum(item.total_price for item in items)
    logger.info(f"💵 Subtotal calculado: ${order.calculated_subtotal}")
    logger.info(f"🚚 Tipo de entrega: {order.delivery_type}")
    
    # Calcular costo de envío basado en configuración actual del negocio
    if order.delivery_type == 'delivery':
        if order.calculated_subtotal >= settings.free_delivery_threshold:
            order.calculated_shipping = 0
            logger.info(f"✅ Envío GRATIS (subtotal ${order.calculated_subtotal} >= threshold ${settings.free_delivery_threshold})")
        else:
            order.calculated_shipping = 5000  # Costo fijo de envío
            logger.info(f"💸 Envío CON COSTO: $5000 (subtotal ${order.calculated_subtotal} < threshold ${settings.free_delivery_threshold})")
    else:
        order.calculated_shipping = 0
        logger.info(f"🏪 Pickup - Sin costo de envío")
    
    # Calcular total final
    order.calculated_total = order.calculated_subtotal + order.calculated_shipping
    logger.info(f"🧾 Total final: ${order.calculated_total} (${order.calculated_subtotal} + ${order.calculated_shipping})")
    
    # Verificar si califica para envío gratis
    order.qualifies_for_free_shipping = (
        order.delivery_type == 'delivery' and 
        order.calculated_subtotal >= settings.free_delivery_threshold
    )
    logger.info(f"🎯 Califica para envío gratis: {order.qualifies_for_free_shipping}")
    
    # Log del pedido original para comparar
    logger.info(f"📊 Total original en BD: ${getattr(order, 'total', 'N/A')}")
    logger.info(f"📊 Delivery fee original en BD: ${getattr(order, 'delivery_fee', 'N/A')}")
    
    context = {
        'order': order,
        'settings': settings,
        'title': f'Pedido #{order.order_number}'
    }
    
    logger.info("🚀 Context preparado, renderizando template de detalle...")
    
    return render(request, 'history/order_detail.html', context)
