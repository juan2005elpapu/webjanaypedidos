from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from orders.models import Order, BusinessSettings  # ✅ IMPORTAR BusinessSettings también

@login_required
def order_history_list(request):
    """Vista principal del historial de pedidos del usuario"""
    
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
    
    # ✅ RECALCULAR TOTALES para pedidos antiguos que no tienen delivery_fee calculado
    for order in orders:
        if not hasattr(order, '_totals_calculated'):
            order.calculate_total()  # Esto recalculará delivery_fee y total
            order._totals_calculated = True
    
    # Paginación
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # ✅ OBTENER configuraciones para mostrar en template
    settings = BusinessSettings.get_settings()
    
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
    
    # ✅ RECALCULAR totales si es necesario
    order.calculate_total()
    
    # ✅ OBTENER configuraciones
    settings = BusinessSettings.get_settings()
    
    context = {
        'order': order,
        'settings': settings,  # ✅ AGREGAR settings al contexto
        'title': f'Pedido #{order.order_number}'
    }
    
    return render(request, 'history/order_detail.html', context)
