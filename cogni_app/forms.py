from django import forms
from .models import Progreso, Sesion, User, PlanTratamiento, InformeProgreso
from django.utils import timezone
from datetime import timedelta


class ProgresoForm(forms.ModelForm):
    class Meta:
        model = Progreso
        # Los campos que el terapeuta va a rellenar
        fields = ['desempeno_puntos', 'observaciones']
        
        widgets = {
            'desempeno_puntos': forms.NumberInput(attrs={
                'class': 'form-control form-control-lg text-center',
                'min': '1',
                'max': '10',
                'placeholder': 'Ej. 8',
                'style': 'max-width: 120px; font-size: 1.5rem; font-weight: bold; margin: 0 auto;'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '5',
                'placeholder': 'Escribe aquí los detalles de la sesión, ejercicios realizados, nivel de atención y comportamiento del paciente...'
            }),
        }
        
        labels = {
            'desempeno_puntos': 'Puntuación Cognitiva (1 al 10)',
            'observaciones': 'Notas Clínicas y Observaciones de la Sesión',
        }


class ReservaTerapeutaForm(forms.ModelForm):
    class Meta:
        model = Sesion
        fields = ['paciente', 'fecha', 'tratamiento']
        widgets = {
            'paciente': forms.Select(attrs={'class': 'form-select'}),
            'tratamiento': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }

    def __init__(self, **kwargs):
        self.terapeuta = kwargs.pop('terapeuta', None)
        super().__init__(**kwargs)

        self.fields['paciente'].queryset = User.objects.filter(
            perfil_paciente__isnull=False
        ).order_by('first_name', 'last_name')

        self.fields['paciente'].label_from_instance = lambda obj: obj.get_full_name() or obj.username
        self.fields['fecha'].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha')

        if fecha_inicio and self.terapeuta:
            if fecha_inicio < timezone.now():
                raise forms.ValidationError("No puedes programar una sesión en una fecha o hora pasada.")

            duracion_sesion = timedelta(hours=1)
            fecha_fin = fecha_inicio + duracion_sesion

            citas_conflictivas = Sesion.objects.filter(
                terapeuta=self.terapeuta,
                estado='PROGRAMADA',
                fecha__lt=fecha_fin,
            )

            for cita in citas_conflictivas:
                cita_fin = cita.fecha + duracion_sesion
                # Si la cita existente termina después de que empieza la nueva -> ¡CHOQUE!
                if cita_fin > fecha_inicio:
                    raise forms.ValidationError(
                        f"No estás disponible en esa fecha. Tienes otra sesión programada de "
                        f"{cita.fecha.strftime('%H:%M')} a {cita_fin.strftime('%H:%M')}."
                    )

        return cleaned_data


class PlanTratamientoForm(forms.ModelForm):
    class Meta:
        model = PlanTratamiento
        fields = [
            'paciente', 'area_prioritaria', 'nivel_importancia', 
            'objetivos_principales', 'actividades_recomendadas', 
            'fecha_revision', 'observaciones_clinicas'
        ]
        widgets = {
            'paciente': forms.HiddenInput(),
            'area_prioritaria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Memoria semántica o Atención sostenida'}),
            'nivel_importancia': forms.Select(attrs={'class': 'form-select'}),
            'objetivos_principales': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalla los objetivos clínicos...'}),
            'actividades_recomendadas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Ejercicios específicos, cuadernillos, dinámicas...'}),
            'observaciones_clinicas': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'fecha_revision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    '''def __init__(self, *args, **kwargs):
        terapeuta = kwargs.pop('terapeuta', None)
        super().__init__(*args, **kwargs)
        
        if terapeuta:
            self.fields['paciente'].queryset = User.objects.filter(
                perfil_paciente__terapeuta=terapeuta
            ).order_by('first_name')
            self.fields['paciente'].label_from_instance = lambda obj: obj.get_full_name() or obj.username'''


class InformeProgresoForm(forms.ModelForm):
    class Meta:
        model = InformeProgreso
        # Excluimos 'paciente' y 'terapeuta' porque los asignaremos automáticamente en la vista
        fields = [
            'evolucion_general', 
            'logros_destacados', 
            'aspectos_por_mejorar', 
            'recomendaciones_proximo_mes'
        ]
        widgets = {
            'evolucion_general': forms.Select(attrs={
                'class': 'form-select fw-bold text-primary'
            }),
            'logros_destacados': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Ej: Ha mejorado su velocidad de procesamiento. Logra recordar la secuencia de 4 pasos para los ejercicios sin frustrarse...'
            }),
            'aspectos_por_mejorar': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Ej: Muestra fatiga atencional severa pasados los 20 minutos. Todavía se confunde con la orientación del día de la semana...'
            }),
            'recomendaciones_proximo_mes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Ej: Reducir las sesiones a bloques de 15 minutos con pausas. Recomendar a la familia usar el calendario visual en casa...'
            }),
        }
        labels = {
            'evolucion_general': 'Evolución Global de este Mes',
            'logros_destacados': 'Logros Destacados (Cosas que han mejorado)',
            'aspectos_por_mejorar': 'Aspectos por Mejorar (Dificultades detectadas)',
            'recomendaciones_proximo_mes': 'Estrategia y Pautas para el Próximo Mes',
        }
