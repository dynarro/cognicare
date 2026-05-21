from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.utils import timezone
from .models import Reserva, User, PerfilPaciente, Progreso
from .forms import ProgresoForm

User = get_user_model()

class DashboardTerapeutaView(LoginRequiredMixin, ListView):
    model = Reserva
    template_name = 'terapeuta/dashboard.html'
    context_object_name = 'mis_citas'

    def get_queryset(self):
        ahora = timezone.now()
        # Retorna solo las reservas donde el terapeuta es el usuario actual
        return Reserva.objects.filter(
            terapeuta=self.request.user, 
            completada=False,
            fecha__gte=ahora # __gte significa "Greater Than or Equal" (Mayor o igual a ahora)
        ).order_by('fecha')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtenemos usuarios únicos que han tenido reservas con este terapeuta
        context['mis_pacientes'] = User.objects.filter(
            Q(citas_paciente__terapeuta=self.request.user) | 
            Q(perfil_paciente__terapeuta=self.request.user)
        ).distinct()
        
        # IDs de pacientes que YA tienen terapeuta fijo en su perfil
        con_terapeuta_fijo = PerfilPaciente.objects.filter(
            terapeuta__isnull=False
        ).values_list('usuario_id', flat=True)
        
        # IDs de pacientes que YA tienen al menos una cita (Reserva) registrada
        con_citas_existentes = User.objects.filter(
            citas_paciente__isnull=False
        ).values_list('id', flat=True)
        
        # pacientes libres excluyendo los dos grupos anteriores
        context['pacientes_sin_asignar'] = User.objects.filter(
            perfil_paciente__isnull=False # Asegura que tengan un perfil creado
        ).exclude(
            id__in=con_terapeuta_fijo       # Excluye si ya tienen terapeuta en el perfil
        ).exclude(
            id__in=con_citas_existentes    # Excluye si ya tienen citas en el sistema
        ).exclude(
            id=self.request.user.id        # Evita mostrar al propio terapeuta
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

@login_required
def autoasignar_paciente(request, paciente_id):
    if request.method == 'POST':
        # Buscamos el perfil del paciente que se quiere asignar
        # NOTA: Asegúrate de que el campo en tu modelo se llame 'terapeuta' 
        perfil = get_object_or_404(PerfilPaciente, usuario_id=paciente_id)
    
        # Validamos que realmente no tenga a nadie asignado aún (por seguridad)
        if perfil.terapeuta is None:
            perfil.terapeuta = request.user  # El terapeuta actual
            perfil.save()
            messages.success(request, f"¡Te has asignado correctamente a {perfil.usuario.get_full_name()}!")
        else:
            messages.error(request, "Este paciente ya fue asignado a otro profesional.")
        
    return redirect('dashboard')