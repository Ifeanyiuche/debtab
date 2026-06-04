from django.db import models
from apps.draw.models import Debate, DebateAdjudicator
from apps.participants.models import Adjudicator, Speaker


class AdjudicatorFeedback(models.Model):
    """Feedback submitted about an adjudicator after a debate."""
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name="feedback")
    adjudicator = models.ForeignKey(Adjudicator, on_delete=models.CASCADE, related_name="feedback_received")

    # Source: either a speaker or another adjudicator submitted this
    source_speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True, related_name="feedback_given"
    )
    source_adjudicator = models.ForeignKey(
        Adjudicator, on_delete=models.SET_NULL, null=True, blank=True, related_name="feedback_given"
    )

    score = models.FloatField(help_text="1=poor, 5=excellent")
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    ignored = models.BooleanField(default=False, help_text="Tab master can ignore outlier feedback")

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        source = self.source_speaker or self.source_adjudicator or "Anonymous"
        return f"Feedback for {self.adjudicator.name} from {source}"
