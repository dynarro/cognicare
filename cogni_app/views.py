from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Reserva, User, PerfilPaciente, Progreso
from .forms import ProgresoForm

User = get_user_model()

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
    
    try:
        # Intentamos obtener el perfil clínico del paciente
        perfil = paciente.perfil_paciente
        edad = perfil.edad
        informe = perfil.informe_medico_inicial
        patologias = perfil.patologias_previas
    
    except PerfilPaciente.DoesNotExist:
        # Si el paciente NO tiene perfil creado todavía, evitamos que la app falle
        perfil = None
        edad = "No registrada"
        informe = None
        patologias = "Sin historial médico cargado aún."
    
    historial_progreso = Progreso.objects.filter(
        reserva__paciente=paciente
    ).order_by('-reserva__fecha')

    context = {
        'paciente': paciente,
        'perfil': perfil,
        'edad': edad,
        'informe': informe,
        'patologias': patologias,
        'historial_progreso': historial_progreso,
    }

    return render(request, 'terapeuta/ficha_paciente.html', context)

@login_required
@login_required
def nueva_sesion(request, paciente_id):
    # Buscamos al paciente
    paciente = get_object_or_404(User, id=paciente_id)
    
    # Buscamos la última cita pendiente de este paciente con este terapeuta
    reserva = Reserva.objects.filter(
        paciente=paciente, 
        terapeuta=request.user, 
        completada=False
    ).first()

    if request.method == 'POST':
        form = ProgresoForm(request.POST)
        if form.is_valid():
            # Creamos el objeto progreso pero no lo guardamos en la BD todavía
            progreso = form.save(commit=False)
            
            # Si encontramos una reserva pendiente, la vinculamos y la marcamos como completada
            if reserva:
                progreso.reserva = reserva
                reserva.completada = True
                reserva.save()
            else:
                # Si por alguna razón no hay cita en el calendario, puedes manejar el error
                # o crear una reserva ficticia. Por ahora, asumiremos que existe.
                messages.error(request, "No se encontró una cita activa para vincular esta nota.")
                return redirect('dashboard')

            # Guardamos definitivamente el progreso
            progreso.save()
            
            # Enviamos un mensaje de éxito que se mostrará en el base.html
            messages.success(request, f"¡Progreso de {paciente.get_full_name()} registrado correctamente!")
            return redirect('perfil_paciente', paciente_id=paciente.id)
    else:
        form = ProgresoForm()

    context = {
        'paciente': paciente,
        'reserva': reserva,
        'form': form,
    }
    return render(request, 'terapeuta/nueva_sesion.html', context)