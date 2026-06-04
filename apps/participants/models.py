from django.db import models
from apps.tournaments.models import Tournament


class Institution(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='institutions')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    region = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Speaker(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='speakers')
    name = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='speakers'
    )
    email = models.EmailField(blank=True)
    is_esl = models.BooleanField(default=False, verbose_name="ESL")
    is_efl = models.BooleanField(default=False, verbose_name="EFL")
    is_novice = models.BooleanField(default=False, verbose_name="Novice")
    is_schools = models.BooleanField(default=False, verbose_name="Schools")
    checked_in = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Team(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams'
    )
    speakers = models.ManyToManyField(Speaker, related_name='teams', blank=True)
    break_category = models.CharField(max_length=50, blank=True)
    is_swing = models.BooleanField(default=False)
    emoji = models.CharField(max_length=10, blank=True)
    checked_in = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def speaker_list(self):
        return ", ".join(s.name for s in self.speakers.all())


class Adjudicator(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='adjudicators')
    name = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution, on_delete=models.SET_NULL, null=True, blank=True, related_name='adjudicators'
    )
    email = models.EmailField(blank=True)
    base_score = models.FloatField(default=1.5)
    independent = models.BooleanField(default=False)
    checked_in = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
