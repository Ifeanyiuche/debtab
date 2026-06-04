from django.contrib import admin
from .models import Venue

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ["name", "tournament", "priority"]
    list_filter = ["tournament"]
