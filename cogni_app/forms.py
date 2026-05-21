from django import forms
from .models import Progreso

class ProgresoForm(forms.ModelForm):
    class Meta:
        model = Progreso
        # Los campos que el terapeuta va a rellenar
        fields = ['desempeno_puntos', 'observaciones']
        
        # Añadimos estilos de Bootstrap directamente a los campos
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