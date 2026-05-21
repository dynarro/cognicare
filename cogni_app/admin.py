from django.contrib import admin
from .models import User, Tratamiento, Reserva, Progreso

admin.site.register(User)
admin.site.register(Tratamiento)
admin.site.register(Reserva)
admin.site.register(Progreso)
