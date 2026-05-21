from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils import timezone

# 1. Usuario extendido
class User(AbstractUser):
    is_terapeuta = models.BooleanField(default=False)
    telefono = models.CharField(max_length=15, blank=True)

    custom_groups = models.ManyToManyField(
        Group,
        related_name='custom_users',
        blank=True,
    )
class PerfilPaciente(models.Model):
    # Vinculamos el perfil al usuario creado anteriormente
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_paciente')
    
    # Datos básicos
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    contacto_emergencia = models.CharField(max_length=100, help_text="Nombre del familiar responsable")
    telefono_emergencia = models.CharField(max_length=15)
    
    # Datos médicos
    informe_medico_inicial = models.FileField(upload_to='informes_medicos/', null=True, blank=True)
    patologias_previas = models.TextField(blank=True, help_text="Ej: Alzheimer precoz, Parkinson, etc.")
    observaciones_familiares = models.TextField(blank=True, help_text="Datos que la familia considere relevantes")
    terapeuta = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # Si el terapeuta se borra, el paciente NO se borra
        related_name='pacientes_asignados',
        null=True,                  # Permite estar vacío (sin asignar)
        blank=True
    )

    @property
    def edad(self):
        import datetime
        return (datetime.date.today() - self.fecha_nacimiento).days // 365

    def __str__(self):
        return f"Perfil de {self.usuario.get_full_name()}"
        
# 2. Catálogo de tratamientos
class Tratamiento(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()

# 3. Reservas
class Reserva(models.Model):
    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas_paciente')
    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas_terapeuta')
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.PROTECT)
    fecha = models.DateTimeField()
    completada = models.BooleanField(default=False)

# 4. Notas de progreso
class Progreso(models.Model):
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE)
    desempeno_puntos = models.IntegerField() # Para las gráficas
    observaciones = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)