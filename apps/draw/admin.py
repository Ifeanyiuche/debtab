from django.contrib import admin
from .models import Debate, DebateTeam, DebateAdjudicator

class DebateTeamInline(admin.TabularInline):
    model = DebateTeam
    extra = 0

class DebateAdjudicatorInline(admin.TabularInline):
    model = DebateAdjudicator
    extra = 0

@admin.register(Debate)
class DebateAdmin(admin.ModelAdmin):
    list_display = ["__str__", "round", "venue", "bracket", "result_status"]
    list_filter = ["round__tournament", "round", "result_status"]
    inlines = [DebateTeamInline, DebateAdjudicatorInline]

@admin.register(DebateTeam)
class DebateTeamAdmin(admin.ModelAdmin):
    list_display = ["team", "debate", "position", "points", "rank", "total_score"]
    list_filter = ["debate__round__tournament", "position"]
    search_fields = ["team__name"]
