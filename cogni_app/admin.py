from django.contrib import admin
from .models import User, Tratamiento, Sesion, Progreso, PerfilPaciente,PlanTratamiento, InformeProgreso

admin.site.register(User)
admin.site.register(PerfilPaciente)
admin.site.register(Tratamiento)
#admin.site.register(PlanTratamiento)
admin.site.register(Sesion)
admin.site.register(Progreso)
admin.site.register(InformeProgreso)

@admin.register(PlanTratamiento)
class PlanTratamientoAdmin(admin.ModelAdmin):
    # Esto te permite ver y editar la fecha de creación aunque tenga auto_now_add=True
    readonly_fields = ('id','fecha_creacion',) 
    fields = ['paciente', 'terapeuta', 'area_prioritaria', 'nivel_importancia', 'fecha_creacion', 'fecha_revision', 'objetivos_principales', 'actividades_recomendadas', 'observaciones_clinicas']
