from django.contrib import admin
from .models import Ballot, SpeakerScore, WSDCSpeakerScore, PSScore

class SpeakerScoreInline(admin.TabularInline):
    model = SpeakerScore
    extra = 0

class WSDCScoreInline(admin.TabularInline):
    model = WSDCSpeakerScore
    extra = 0

@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display = ["debate", "adjudicator", "confirmed", "discarded", "timestamp"]
    list_filter = ["confirmed", "discarded", "debate__round__tournament"]
    inlines = [SpeakerScoreInline, WSDCScoreInline]

@admin.register(SpeakerScore)
class SpeakerScoreAdmin(admin.ModelAdmin):
    list_display = ["speaker", "score", "position", "ironman", "debate_team"]
    list_filter = ["ironman", "ballot__debate__round__tournament"]
    search_fields = ["speaker__name"]
