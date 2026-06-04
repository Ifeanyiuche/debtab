from django.contrib import admin
from .models import Tournament, Round

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["name", "format", "tab_master", "num_prelim_rounds", "active", "created_at"]
    list_filter = ["format", "active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ["tournament", "seq", "name", "draw_type", "status", "draw_released", "results_released"]
    list_filter = ["tournament", "status", "draw_type"]
    ordering = ["tournament", "seq"]
