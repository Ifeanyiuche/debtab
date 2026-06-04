from django.contrib import admin
from .models import Motion

@admin.register(Motion)
class MotionAdmin(admin.ModelAdmin):
    list_display = ["reference", "round", "released"]
    list_filter = ["tournament", "released"]
    search_fields = ["text", "reference"]
