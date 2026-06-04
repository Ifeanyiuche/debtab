from django.db import models
from apps.tournaments.models import Tournament, Round


class Motion(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='motions')
    round = models.ForeignKey(Round, on_delete=models.SET_NULL, null=True, blank=True, related_name='motions')
    text = models.TextField()
    reference = models.CharField(max_length=200, blank=True)
    info_slide = models.TextField(blank=True)
    released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['round__seq', 'id']

    def __str__(self):
        label = self.reference or self.text[:60]
        round_name = self.round.name if self.round else "Unassigned"
        return f"{round_name}: {label}"
