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

    score = models.FloatField(help_text="1=poor, 10=excellent")
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    ignored = models.BooleanField(default=False, help_text="Tab master can ignore outlier feedback")

    class Meta:
        ordering = ["-submitted_at"]

    @property
    def source_display(self):
        if self.source_speaker_id and self.source_speaker:
            return self.source_speaker.name
        if self.source_adjudicator_id and self.source_adjudicator:
            return self.source_adjudicator.name
        return "Anonymous"

    def __str__(self):
        return f"Feedback for {self.adjudicator.name} from {self.source_display}"
