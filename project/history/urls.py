from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.order_history_list, name='orders'),  # /history/
    path('<int:order_id>/', views.order_detail_history, name='order_detail'),  # /history/3/
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),  # /history/3/cancel/
]