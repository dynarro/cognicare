from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from datetime import date


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

    def __str__(self):
        return self.nombre

# 3. Sesion
class Sesion(models.Model):
    ESTADO_CHOICES = [
        ('PROGRAMADA', 'Programada'),
        ('COMPLETADA', 'Completada'),
        ('ANULADA', 'Anulada'),
    ]

    paciente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas_paciente')
    terapeuta = models.ForeignKey(User, on_delete=models.CASCADE, related_name='citas_terapeuta')
    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.PROTECT)
    fecha = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PROGRAMADA')

    def __str__(self):
        return f"Sesión con {self.paciente.get_full_name()} - {self.fecha} ({self.get_estado_display()})"

# 4. Notas de progreso
class Progreso(models.Model):
    sesion = models.OneToOneField('Sesion', on_delete=models.SET_NULL, null=True, blank=True)
    desempeno_puntos = models.IntegerField() # Para las gráficas
    observaciones = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

class PlanTratamiento(models.Model):
    # Opciones de prioridad clínica
    NIVEL_PRIORIDAD = [
        ('ALTA', 'Prioridad Alta (Urgente / Estimulación Diaria)'),
        ('MEDIA', 'Prioridad Media (Mantenimiento Semanal)'),
        ('BAJA', 'Prioridad Baja (Seguimiento General)'),
    ]

    paciente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='planes_tratamiento'
    )
    terapeuta = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='planes_creados'
    )
    
    # Áreas de enfoque y valoraciones de importancia
    objetivos_principales = models.TextField(
        help_text="¿Qué metas buscamos alcanzar a corto y mediano plazo?"
    )
    area_prioritaria = models.CharField(
        max_length=200, 
        help_text="Ej: Memoria a corto plazo, Funciones ejecutivas, Motricidad fina..."
    )
    nivel_importancia = models.CharField(
        max_length=10, 
        choices=NIVEL_PRIORIDAD, 
        default='MEDIA'
    )
    
    actividades_recomendadas = models.TextField(
        help_text="Herramientas, ejercicios o talleres específicos para este paciente."
    )
    observaciones_clinicas = models.TextField(blank=True, null=True)
    
    fecha_creacion = models.DateField(auto_now_add=True)
    fecha_revision = models.DateField(
        help_text="Fecha sugerida para evaluar los avances del adulto mayor."
    )

    def __str__(self):
        return f"Plan para {self.paciente.get_full_name()} ({self.area_prioritaria})"


class InformeProgreso(models.Model):
    ESCALA_PROGRESO = [
        ('MEJORA_S', 'Mejora Significativa'),
        ('MEJORA_L', 'Mejora Leve / Estabilización'),
        ('SIN_CAMBIOS', 'Sin Cambios Evidentes'),
        ('REGRESION', 'Regresión / Requiere Intervención Médica'),
    ]

    paciente = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='informes_progreso'
    )
    terapeuta = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='informes_redactados'
    )
    
    fecha_informe = models.DateField(auto_now_add=True)
    
    # Valoración del mes
    logros_destacados = models.TextField(
        help_text="¿En qué actividades o conductas se han observado avances?"
    )
    aspectos_por_mejorar = models.TextField(
        help_text="Dificultades detectadas, frustraciones o áreas que se han resistido."
    )
    
    # Métrica de evolución global
    evolucion_general = models.CharField(
        max_length=15, 
        choices=ESCALA_PROGRESO, 
        default='SIN_CAMBIOS'
    )
    
    # Ajustes en la estrategia
    recomendaciones_proximo_mes = models.TextField(
        help_text="Modificaciones en los talleres, tareas para el hogar o pautas familiares."
    )

    def __str__(self):
        fecha_formateada = self.fecha_informe.strftime('%b %Y') if self.fecha_informe else "Sin fecha"
        return f"Informe Mensual de {self.paciente.get_full_name()} ({fecha_formateada})"