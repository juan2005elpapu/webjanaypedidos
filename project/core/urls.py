from django.urls import path
from .views import HomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    # Quitamos la ruta welcome/ porque ahora está en la raíz del sitio
]