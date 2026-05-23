from django.urls import path
from . import views

urlpatterns = [
    path('paciente/<int:pk>/', views.perfil_paciente, name='perfil_paciente'),
    path('', views.DashboardTerapeutaView.as_view(), name='dashboard'),
    path('paciente/<int:paciente_id>/nueva-sesion/', views.nueva_sesion, name='nueva_sesion'),
    path('paciente/<int:paciente_id>/asignarme/', views.autoasignar_paciente, name='autoasignar_paciente'),
    path('paciente/<int:pk>/plan/nuevo/', views.crear_plan_tratamiento, name='crear_plan_tratamiento'),
    #path('paciente/plan/nuevo/', views.crear_plan_tratamiento, name='crear_plan_tratamiento'),
    path('paciente/<int:pk>/informe/nuevo/', views.crear_informe_progreso, name='crear_informe_progreso'),
    path('sesion/nueva/', views.crear_reserva_terapeuta, name='crear_reserva_terapeuta'),
    path('sesion/<int:pk>/anular/', views.anular_sesion, name='anular_sesion'),
    path('informe/<int:pk>/', views.detalle_informe_progreso, name='detalle_informe_progreso'),
]