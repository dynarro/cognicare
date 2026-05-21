from django.urls import path
from . import views

urlpatterns = [
    path('', views.perfil_paciente, name='perfil_paciente'),
    path('', views.DashboardTerapeutaView.as_view(), name='dashboard'),
]