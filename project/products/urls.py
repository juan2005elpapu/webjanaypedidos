from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Cambia esta línea - usa la clase en vez de la función
    path('', views.ProductListView.as_view(), name='list'),
    # Y también esta línea si existe
    path('<int:product_id>/', views.ProductDetailView.as_view(), name='detail'),
]