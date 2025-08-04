from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    path('', views.order_history_list, name='orders'),
    path('<int:order_id>/', views.order_detail_history, name='order_detail'),
]