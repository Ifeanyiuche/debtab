from django.db import models
from apps.tournaments.models import Tournament


class Venue(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='venues')
    name = models.CharField(max_length=100)
    priority = models.PositiveIntegerField(default=10)
    display_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority', 'name']

    def __str__(self):
        return self.display_name or self.name
