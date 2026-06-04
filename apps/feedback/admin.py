from django.contrib import admin
from .models import AdjudicatorFeedback

@admin.register(AdjudicatorFeedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["adjudicator", "score", "source_speaker", "source_adjudicator", "ignored", "submitted_at"]
    list_filter = ["ignored", "adjudicator__tournament"]
    search_fields = ["adjudicator__name"]
