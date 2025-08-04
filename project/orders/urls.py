from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Crear nuevo pedido
    path('create/', views.create_order, name='create'),
    path('create/step1/', views.order_step1, name='step1'),
    path('create/step2/', views.order_step2, name='step2'),
    path('create/step3/', views.order_step3, name='step3'),
    
    # Éxito de pedido
    path('success/<int:order_id>/', views.order_success, name='success'),
    
    # Gestión del carrito
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    
]