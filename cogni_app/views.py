from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.utils import timezone
from django.http import Http404
from datetime import date

from .models import Sesion, User, PerfilPaciente, Progreso, InformeProgreso
from .forms import ProgresoForm, ReservaTerapeutaForm, PlanTratamientoForm, InformeProgresoForm

User = get_user_model()

class DashboardTerapeutaView(LoginRequiredMixin, ListView):
    model = Sesion
    template_name = 'terapeuta/dashboard.html'
    context_object_name = 'mis_citas'

    def get_queryset(self):
        ahora = timezone.now()
        # Retorna solo las reservas donde el terapeuta es el usuario actual
        return Sesion.objects.filter(
            terapeuta=self.request.user, 
            estado='PROGRAMADA',
            fecha__gte=ahora # __gte significa "Greater Than or Equal" (Mayor o igual a ahora)
        ).order_by('fecha')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtenemos usuarios únicos que han tenido reservas con este terapeuta
        context['mis_pacientes'] = User.objects.filter(
            Q(citas_paciente__terapeuta=self.request.user) | 
            Q(perfil_paciente__terapeuta=self.request.user)
        ).distinct()
        
        context['proximas_sesiones'] = Sesion.objects.filter(
            terapeuta=self.request.user,
            estado='PROGRAMADA',
            fecha__gte=date.today()
        ).order_by('fecha')

        # IDs de pacientes que YA tienen terapeuta fijo en su perfil
        con_terapeuta_fijo = PerfilPaciente.objects.filter(
            terapeuta__isnull=False
        ).values_list('usuario_id', flat=True)
        
        # IDs de pacientes que YA tienen al menos una cita (Sesion) registrada
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


def perfil_paciente(request, pk=None, paciente_id=None):
    id_buscar = pk if pk else paciente_id
    paciente = get_object_or_404(User, id=id_buscar)
    todos_los_planes = paciente.planes_tratamiento.all().order_by('-fecha_creacion')
    plan_actual = todos_los_planes.first() if todos_los_planes.exists() else None

    todos_los_informes = paciente.informes_progreso.all().order_by('-fecha_informe')
    ultimo_informe = todos_los_informes.first()

    requiere_informe_mensual = False

    if todos_los_planes.exists():
        primer_plan = todos_los_planes.last()
        dias_desde_inicio = (date.today() - primer_plan.fecha_creacion).days

        # Si ya pasaron los 30 días reglamentarios...
        if dias_desde_inicio >= 30:
            if ultimo_informe:
                # Comprobamos el mes y año del último informe. 
                # Si coincide con el mes y año actual, SIGNIFICA QUE YA CUMPLIÓ ESTE MES.
                if ultimo_informe.fecha_informe.month == date.today().month and ultimo_informe.fecha_informe.year == date.today().year:
                    requiere_informe_mensual = False  # Ya hizo el de este mes
                else:
                    requiere_informe_mensual = True   # Le toca el de un mes nuevo
            else:
                requiere_informe_mensual = True
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
        sesion__paciente=paciente
    ).order_by('-sesion__fecha')
    print("--- ENCONTRADOS EN LA BD ---")
    print(historial_progreso) 
    print("----------------------------")

    requiere_informe_mensual = False

    if plan_actual:
        dias = (date.today() - todos_los_planes.last().fecha_creacion).days
        
        if dias >= 30:
            requiere_informe_mensual = True

    ya_tiene_informe_este_mes = paciente.informes_progreso.filter(
        fecha_informe__month=date.today().month,
        fecha_informe__year=date.today().year
    ).exists()

    # Si ya tiene un informe de este mes, requiere_informe_mensual DEBE SER False
    if ya_tiene_informe_este_mes:
        requiere_informe_mensual = False
    else:
        # Si no tiene informe, evaluamos si lleva más de 30 días
        primer_plan = todos_los_planes.last()
        if primer_plan and (date.today() - primer_plan.fecha_creacion).days >= 30:
            requiere_informe_mensual = True
        else:
            requiere_informe_mensual = False

    context = {
        'paciente': paciente,
        'perfil': perfil,
        'edad': edad,
        'informe': informe,
        'patologias': patologias,
        'historial_progreso': historial_progreso,
        'plan_actual': plan_actual,
        'historial_planes': todos_los_planes,
        'informes': todos_los_informes,
        'requiere_informe_mensual': requiere_informe_mensual,
    }

    return render(request, 'terapeuta/ficha_paciente.html', context)

@login_required
@login_required
def nueva_sesion(request, paciente_id=None, pk=None):
    # Buscamos al paciente
    id_buscar = paciente_id if paciente_id else pk
    if not id_buscar:
        raise Http404("No se especificó el paciente para la sesión.")
    paciente = get_object_or_404(User, id=id_buscar)
    
    # Buscamos la última cita pendiente de este paciente con este terapeuta
    reserva = Sesion.objects.filter(
        paciente=paciente, 
        terapeuta=request.user, 
        estado='PROGRAMADA'
    ).first()

    if request.method == 'POST':
        form = ProgresoForm(request.POST)
        if form.is_valid():
            # Creamos el objeto progreso pero no lo guardamos en la BD todavía
            progreso = form.save(commit=False)
            
            # Si encontramos una reserva pendiente, la vinculamos y la marcamos como completada
            if reserva:
                progreso.paciente = paciente
                progreso.terapeuta = request.user
                progreso.sesion = reserva
                reserva.estado = 'COMPLETADA'
                reserva.save()

                print("Estado cambiado a:", reserva.estado)
            else:
                # Si por alguna razón no hay cita en el calendario, puedes manejar el error
                # o crear una reserva ficticia. Por ahora, asumiremos que existe.
                messages.error(request, "No se encontró una cita activa para vincular esta nota.")
                return redirect('dashboard')

            # Guardamos definitivamente el progreso
            progreso.save()
            
            # Enviamos un mensaje de éxito que se mostrará en el base.html
            messages.success(request, f"¡Progreso de {paciente.get_full_name()} registrado correctamente!")
            return redirect('perfil_paciente', pk=paciente.id)
    else:
        form = ProgresoForm()

    context = {
        'paciente': paciente,
        'reserva': reserva,
        'form': form,
    }
    return render(request, 'terapeuta/nueva_sesion.html', context)

@login_required
def autoasignar_paciente(request, paciente_id=None, pk=None):
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

@login_required
def crear_reserva_terapeuta(request):
    if request.method == 'POST':
        form = ReservaTerapeutaForm(data=request.POST, terapeuta=request.user)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.terapeuta = request.user # Aseguramos que el terapeuta sea el logueado
            reserva.save()
            messages.success(request, "¡Sesión programada con éxito!")
            return redirect('dashboard')

    else:
        form = ReservaTerapeutaForm(terapeuta=request.user)

    return render(request, 'terapeuta/crear_reserva.html', {'form': form})

@login_required
def crear_plan_tratamiento(request, paciente_id=None, pk=None):
    id_buscar = pk if pk else paciente_id
    paciente = get_object_or_404(User, id=id_buscar)

    if request.method == 'POST':
        form = PlanTratamientoForm(data=request.POST)

        if form.is_valid():
            plan = form.save(commit=False)
            plan.terapeuta = request.user # Asignamos al profesional logueado
            plan.save()
            messages.success(request, f"¡Plan de tratamiento individualizado creado con éxito!")
            
            return redirect('perfil_paciente', pk=id_buscar)

    else:
        form = PlanTratamientoForm(initial={'paciente': paciente})
        
    return render(request, 'terapeuta/crear_plan.html', {'form': form, 'paciente': paciente})

@login_required
def crear_informe_progreso(request, pk=None, paciente_id=None):
    # Aseguramos que el paciente exista en el sistema
    id_buscar = pk if pk else paciente_id
    paciente = get_object_or_404(User, id=id_buscar)
    
    
    if request.method == 'POST':
        form = InformeProgresoForm(data=request.POST)
        if form.is_valid():
            informe = form.save(commit=False)
            informe.paciente = paciente        # Vinculamos automáticamente al adulto mayor
            informe.terapeuta = request.user   # El profesional que inició sesión
            informe.estado = 'COMPLETADA'
            informe.save()
            
            messages.success(request, f"¡Informe mensual de {paciente.get_full_name()} guardado con éxito!")
            # Redirige de vuelta a la ficha del paciente para ver el resultado
            return redirect('perfil_paciente', pk=paciente.id) 
    else:
        form = InformeProgresoForm()
        
    context = {
        'form': form,
        'paciente': paciente
    }
    return render(request, 'terapeuta/crear_informe.html', context)

@login_required
def detalle_informe_progreso(request, pk):
    # Buscamos el informe por su ID único
    informe = get_object_or_404(InformeProgreso, id=pk)
    
    context = {
        'informe': informe,
        'paciente': informe.paciente  # Accedemos al paciente a través de la relación del informe
    }
    return render(request, 'terapeuta/detalle_informe.html', context)

@login_required
def anular_sesion(request, pk):
    sesion = get_object_or_404(Sesion, id=pk)
    
    if request.method == 'POST':
        sesion.estado = 'ANULADA'  # O sesion.delete() si las borras por completo
        sesion.save()
        messages.success(request, f"La sesión de {sesion.paciente.get_full_name()} ha sido anulada.")
    
    referer = request.META.get('HTTP_REFERER', '')
    if 'dashboard' in referer:
        return redirect('dashboard')
        
    return redirect('perfil_paciente', pk=sesion.paciente.id)