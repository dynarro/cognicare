from django.shortcuts import render
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Reserva


class DashboardTerapeutaView(LoginRequiredMixin, ListView):
    model = Reserva
    template_name = 'terapeuta/dashboard.html'
    context_object_name = 'mis_citas'

    def get_queryset(self):
        # Retorna solo las reservas donde el terapeuta es el usuario actual
        return Reserva.objects.filter(
            terapeuta=self.request.user, 
            completada=False
        ).order_by('fecha')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtenemos usuarios únicos que han tenido reservas con este terapeuta
        context['mis_pacientes'] = User.objects.filter(
            citas_paciente__terapeuta=self.request.user
        ).distinct()
        return context


class SoloTerapeutaMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_terapeuta # Usando el campo que definimos en el modelo


def perfil_paciente(request, paciente_id):
    paciente = get_object_or_404(User, id=paciente_id)
    perfil = paciente.perfil_paciente # Acceso directo gracias al related_name
    
    context = {
        'paciente': paciente,
        'edad': perfil.edad,
        'informe': perfil.informe_medico_inicial,
        'patologias': perfil.patologias_previas,
    }
    return render(request, 'terapeuta/ficha_paciente.html', context)