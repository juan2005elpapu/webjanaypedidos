from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.core.cache import cache
import traceback

from .models import Order, OrderItem, BusinessSettings
from products.models import Product, Category

@login_required
def create_order(request):
    """Vista principal para crear pedido - redirige al Step 1"""
    return redirect('orders:step1')

@login_required
def order_step1(request):
    """Step 1: Información básica del pedido"""
    settings = BusinessSettings.get_settings()
    
    # Obtener datos del carrito desde la sesión si existen
    cart_data = request.session.get('order_cart', {})
    order_info = cart_data.get('order_info', {})
    
    if request.method == 'POST':
        # Procesar el formulario del Step 1
        delivery_type = request.POST.get('delivery_type')
        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')
        customer_email = request.POST.get('customer_email')
        desired_date = request.POST.get('desired_date')
        desired_time = request.POST.get('desired_time')
        
        # Validaciones
        errors = []
        
        if not all([delivery_type, customer_name, customer_phone, desired_date, desired_time]):
            errors.append("Todos los campos obligatorios deben ser completados.")
        
        # Validar fecha
        try:
            date_obj = datetime.strptime(desired_date, '%Y-%m-%d').date()
            today = timezone.now().date()
            min_date = today + timedelta(days=settings.min_advance_days)
            max_date = today + timedelta(days=settings.max_advance_days)
            
            if date_obj < min_date:
                errors.append(f"La fecha debe ser al menos {settings.min_advance_days} días de anticipación.")
            elif date_obj > max_date:
                errors.append(f"La fecha no puede ser más de {settings.max_advance_days} días de anticipación.")
                
        except ValueError:
            errors.append("Formato de fecha inválido.")
        
        # Validar hora
        try:
            time_obj = datetime.strptime(desired_time, '%H:%M').time()
            if not (settings.delivery_start_time <= time_obj <= settings.delivery_end_time):
                errors.append(f"La hora debe estar entre {settings.delivery_start_time.strftime('%H:%M')} y {settings.delivery_end_time.strftime('%H:%M')}.")
        except ValueError:
            errors.append("Formato de hora inválido.")
        
        # Campos específicos de delivery
        delivery_address = ""
        delivery_neighborhood = ""
        delivery_references = ""
        
        if delivery_type == 'delivery':
            delivery_address = request.POST.get('delivery_address', '').strip()
            delivery_neighborhood = request.POST.get('delivery_neighborhood', '').strip()
            delivery_references = request.POST.get('delivery_references', '').strip()
            
            if not delivery_address:
                errors.append("La dirección de entrega es obligatoria para delivery.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Guardar información en la sesión
            if 'order_cart' not in request.session:
                request.session['order_cart'] = {}
            
            request.session['order_cart']['order_info'] = {
                'delivery_type': delivery_type,
                'customer_name': customer_name,
                'customer_phone': customer_phone,
                'customer_email': customer_email,
                'desired_date': desired_date,
                'desired_time': desired_time,
                'delivery_address': delivery_address,
                'delivery_neighborhood': delivery_neighborhood,
                'delivery_references': delivery_references,
            }
            request.session.modified = True
            
            messages.success(request, "Información básica guardada. Ahora selecciona tus productos.")
            return redirect('orders:step2')
    
    # Generar fechas disponibles
    today = timezone.now().date()
    available_dates = []
    for i in range(settings.min_advance_days, settings.max_advance_days + 1):
        date = today + timedelta(days=i)
        available_dates.append({
            'value': date.strftime('%Y-%m-%d'),
            'display': date.strftime('%d de %B, %Y'),
            'is_weekend': date.weekday() >= 5
        })
    
    # Generar horarios disponibles
    time_slots = []
    current_time = settings.delivery_start_time
    end_time = settings.delivery_end_time
    
    while current_time <= end_time:
        time_slots.append({
            'value': current_time.strftime('%H:%M'),
            'display': current_time.strftime('%I:%M %p')
        })
        # Incrementar en 30 minutos
        current_datetime = datetime.combine(datetime.today(), current_time)
        current_datetime += timedelta(minutes=30)
        current_time = current_datetime.time()
        
        if current_time > end_time:
            break
    
    # Configuración de steps para el template base
    all_steps = [
        {'number': 1, 'title': 'Información Básica', 'short_title': 'Información'},
        {'number': 2, 'title': 'Selección de Productos', 'short_title': 'Productos'},
        {'number': 3, 'title': 'Confirmación y Pago', 'short_title': 'Confirmación'},
    ]
    
    context = {
        'settings': settings,
        'available_dates': available_dates,
        'time_slots': time_slots,
        'order_info': order_info,
        
        # Datos para el template base de steps
        'step_number': 1,
        'current_step': 1,
        'step_title': 'Información Básica',
        'step_description': 'Completa la información para tu pedido',
        'all_steps': all_steps,
        'next_step_text': 'Continuar',
        'previous_step_url': None,
    }
    
    return render(request, 'orders/step1.html', context)

@login_required
def order_step2(request):
    """Step 2: Selección de productos"""
    
    if request.method == 'POST':
        # Procesar selección de productos
        selected_products = {}
        order_notes = request.POST.get('order_notes', '')
        
        for key, value in request.POST.items():
            if key.startswith('product_'):
                try:
                    product_id = int(key.replace('product_', ''))
                    quantity = int(value)
                    if quantity > 0:
                        selected_products[product_id] = quantity
                except (ValueError, TypeError):
                    continue
        
        # Validar que se hayan seleccionado productos
        if not selected_products:
            messages.error(request, 'Debes seleccionar al menos un producto para continuar.')
            return redirect('orders:step2')
        
        # Calcular total para validar pedido mínimo
        settings = BusinessSettings.get_settings()
        total_amount = 0
        for product_id, quantity in selected_products.items():
            try:
                product = Product.objects.get(id=product_id)
                total_amount += product.price * quantity
            except Product.DoesNotExist:
                continue
        
        # Validar pedido mínimo
        if total_amount < settings.minimum_order_amount:
            messages.error(request, 
                f'El pedido mínimo es ${settings.minimum_order_amount:,.0f}. '
                f'Tu pedido actual es de ${total_amount:,.0f}. '
                f'Agrega productos por ${settings.minimum_order_amount - total_amount:,.0f} más.'
            )
            return redirect('orders:step2')
        
        # Si todo está bien, guardar y continuar
        if 'order_cart' not in request.session:
            request.session['order_cart'] = {}
        
        request.session['order_cart']['selected_products'] = selected_products
        
        # Guardar las notas del pedido también
        if order_notes.strip():
            request.session['order_cart']['order_notes'] = order_notes.strip()
        
        request.session.modified = True
        
        messages.success(request, f"Has seleccionado {len(selected_products)} productos correctamente.")
        return redirect('orders:step3')
    
    # GET request - mostrar formulario
    # Obtener productos y categorías
    categories = Category.objects.filter(
        products__is_available=True
    ).distinct().order_by('name')
    
    products = Product.objects.select_related('category').filter(
        is_available=True
    ).order_by('category__name', 'name')
    
    # Obtener configuración
    settings = BusinessSettings.get_settings()
    
    # Productos ya seleccionados (si los hay) - CORREGIDO
    cart_data = request.session.get('order_cart', {})
    selected_products = cart_data.get('selected_products', {})
    
    # Configuración de steps para el template base
    all_steps = [
        {'number': 1, 'title': 'Información Básica', 'short_title': 'Información'},
        {'number': 2, 'title': 'Selección de Productos', 'short_title': 'Productos'},
        {'number': 3, 'title': 'Confirmación y Pago', 'short_title': 'Confirmación'},
    ]
    
    context = {
        'products': products,
        'categories': categories,
        'selected_products': selected_products,
        'settings': settings,
        
        # Datos para el template base de steps
        'step_number': 2,
        'current_step': 2,
        'step_title': 'Selección de Productos',
        'step_description': 'Elige los productos que deseas pedir',
        'all_steps': all_steps,
        'next_step_text': 'Continuar a pago',
        'previous_step_url': reverse('orders:step1'),
    }
    
    return render(request, 'orders/step2.html', context)

@login_required
def order_step3(request):
    """Step 3: Confirmación y pago"""
    # Verificar que se hayan completado los pasos anteriores
    cart_data = request.session.get('order_cart', {})
    
    if 'order_info' not in cart_data or 'selected_products' not in cart_data:
        messages.warning(request, "Debes completar los pasos anteriores.")
        return redirect('orders:step1')
    
    order_info = cart_data.get('order_info', {})
    selected_products = cart_data.get('selected_products', {})
    order_notes = cart_data.get('order_notes', '')
    
    # Verificación adicional de seguridad
    if not selected_products:
        messages.error(request, "No hay productos seleccionados.")
        return redirect('orders:step2')
    
    if request.method == 'POST':
        # Crear el pedido
        payment_method = request.POST.get('payment_method', 'cash')
        final_order_notes = request.POST.get('order_notes', order_notes)       
        try:
            # Crear el pedido
            order = Order.objects.create(
                user=request.user,
                delivery_type=order_info.get('delivery_type', 'pickup'),
                customer_name=order_info.get('customer_name', ''),
                customer_phone=order_info.get('customer_phone', ''),
                customer_email=order_info.get('customer_email', ''),
                desired_date=datetime.strptime(order_info.get('desired_date'), '%Y-%m-%d').date(),
                desired_time=datetime.strptime(order_info.get('desired_time'), '%H:%M').time(),
                delivery_address=order_info.get('delivery_address', ''),
                delivery_neighborhood=order_info.get('delivery_neighborhood', ''),
                delivery_references=order_info.get('delivery_references', ''),
                payment_method=payment_method,
                notes=final_order_notes,  # CAMBIAR 'special_instructions' por 'notes'
                status='pending'
            )
            
            # Crear los items del pedido CON LAS CANTIDADES CORRECTAS
            total_amount = 0
            for product_id, quantity in selected_products.items():
                try:
                    product = Product.objects.get(id=product_id)
                    quantity = int(quantity)  # Asegurar que sea entero
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        unit_price=product.price,
                        total_price=product.price * quantity
                    )
                    
                    total_amount += product.price * quantity
                    
                except Product.DoesNotExist:
                    continue
            
            # Calcular envío
            settings = BusinessSettings.get_settings()
            shipping_cost = 0 if total_amount >= settings.free_delivery_threshold else 5000
            
            # Actualizar totales del pedido
            order.subtotal = total_amount
            order.shipping_cost = shipping_cost
            order.total_amount = total_amount + shipping_cost
            order.save()
            # Limpiar sesión
            if 'order_cart' in request.session:
                del request.session['order_cart']
            
            messages.success(request, f"¡Pedido #{order.id} creado exitosamente!")
            
            # Si el método de pago es efectivo, redirigir a la página de éxito
            if payment_method == 'cash':
                return redirect('orders:success', order_id=order.id)
            else:
                return redirect('orders:order_detail', order_id=order.id)
        
        except Exception as e:
            traceback.print_exc()
            messages.error(request, f"Error al crear el pedido: {str(e)}")
    
    # Preparar datos para el template (GET request)
    products_data = {}
    for product_id in selected_products.keys():
        try:
            product = Product.objects.get(id=product_id)
            products_data[str(product_id)] = {
                'name': product.name,
                'price': float(product.price)
            }
        except Product.DoesNotExist:
            continue
    
    # Configuración de steps para el template base
    all_steps = [
        {'number': 1, 'title': 'Información Básica', 'short_title': 'Información'},
        {'number': 2, 'title': 'Selección de Productos', 'short_title': 'Productos'},
        {'number': 3, 'title': 'Confirmación y Pago', 'short_title': 'Confirmación'},
    ]
    
    context = {
        'order_info': order_info,
        'selected_products': json.dumps(selected_products),
        'products_data': json.dumps(products_data),
        'order_notes': order_notes,
        'settings': BusinessSettings.get_settings(),
        
        # Datos para el template base de steps
        'step_number': 3,
        'current_step': 3,
        'step_title': 'Confirmación y Pago',
        'step_description': 'Revisa tu pedido y selecciona el método de pago',
        'all_steps': all_steps,
        'next_step_text': 'Confirmar Pedido',
        'previous_step_url': reverse('orders:step2'),
    }
    
    return render(request, 'orders/step3.html', context)

@login_required
def order_history(request):
    """Vista del historial de pedidos del usuario"""
    orders = Order.objects.filter(user=request.user).exclude(status='draft')
    
    context = {
        'orders': orders,
        'title': 'Historial de Pedidos'
    }
    
    return render(request, 'orders/history.html', context)

@login_required
def order_detail(request, order_id):
    """Vista de detalle de un pedido específico"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'title': f'Pedido {order.order_number}'
    }
    
    return render(request, 'orders/detail.html', context)

# Añadir esta nueva función después de order_detail
@login_required
def order_success(request, order_id):
    """Vista de éxito después de confirmar un pedido"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'title': 'Pedido Confirmado'
    }
    
    return render(request, 'orders/ordersuccess.html', context)

# Vistas AJAX para gestión del carrito
@login_required
def add_to_cart(request, product_id):
    """Agregar producto al carrito"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get('quantity', 1))
        special_instructions = request.POST.get('special_instructions', '')
        
        # Obtener o crear carrito en sesión
        if 'order_cart' not in request.session:
            request.session['order_cart'] = {'items': []}
        
        cart = request.session['order_cart']
        if 'items' not in cart:
            cart['items'] = []
        
        # Buscar si el producto ya existe en el carrito
        existing_item = None
        for item in cart['items']:
            if item['product_id'] == product_id:
                existing_item = item
                break
        
        if existing_item:
            existing_item['quantity'] += quantity
            existing_item['special_instructions'] = special_instructions
        else:
            cart['items'].append({
                'product_id': product_id,
                'product_name': product.name,
                'product_price': float(product.price),
                'quantity': quantity,
                'special_instructions': special_instructions,
                'total': float(product.price * quantity)
            })
        
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} agregado al carrito',
            'cart_count': len(cart['items'])
        })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@login_required
def remove_from_cart(request, product_id):
    """Remover producto del carrito"""
    if 'order_cart' in request.session and 'items' in request.session['order_cart']:
        cart = request.session['order_cart']
        cart['items'] = [item for item in cart['items'] if item['product_id'] != product_id]
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': 'Producto removido del carrito',
            'cart_count': len(cart['items'])
        })
    
    return JsonResponse({'success': False, 'message': 'Carrito vacío'})

@login_required
def update_cart(request):
    """Actualizar cantidades en el carrito"""
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = data.get('quantity')
        
        if 'order_cart' in request.session and 'items' in request.session['order_cart']:
            cart = request.session['order_cart']
            for item in cart['items']:
                if item['product_id'] == product_id:
                    item['quantity'] = quantity
                    item['total'] = item['product_price'] * quantity
                    break
            
            request.session.modified = True
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})

@login_required
def clear_cart(request):
    """Limpiar el carrito"""
    if 'order_cart' in request.session:
        del request.session['order_cart']
    
    return JsonResponse({'success': True, 'message': 'Carrito limpiado'})
