from django.contrib import admin
from .models import Preset

# This makes the Preset model available in the admin site
admin.site.register(Preset)