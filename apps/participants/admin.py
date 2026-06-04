from django.contrib import admin
from .models import Institution, Speaker, Team, Adjudicator

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "tournament", "region"]
    list_filter = ["tournament"]
    search_fields = ["name", "code"]

@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ["name", "tournament", "institution", "is_esl", "is_efl", "checked_in"]
    list_filter = ["tournament", "is_esl", "is_efl", "is_novice", "checked_in"]
    search_fields = ["name"]

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "tournament", "institution", "is_swing", "checked_in", "active"]
    list_filter = ["tournament", "is_swing", "active", "checked_in"]
    search_fields = ["name"]
    filter_horizontal = ["speakers"]

@admin.register(Adjudicator)
class AdjudicatorAdmin(admin.ModelAdmin):
    list_display = ["name", "tournament", "institution", "base_score", "independent", "checked_in"]
    list_filter = ["tournament", "independent", "checked_in"]
    search_fields = ["name"]
