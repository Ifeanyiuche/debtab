from django.db import models
from apps.draw.models import Debate, DebateTeam
from apps.participants.models import Adjudicator, Speaker


class Ballot(models.Model):
    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name="ballots")
    adjudicator = models.ForeignKey(
        Adjudicator, on_delete=models.SET_NULL, null=True, blank=True, related_name="ballots"
    )
    confirmed = models.BooleanField(default=False)
    discarded = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        adj = self.adjudicator.name if self.adjudicator else "Tab Master"
        return f"Ballot by {adj} for {self.debate}"


class SpeakerScore(models.Model):
    """
    Score for one speech slot in one debate on one ballot.
    ironman=True: counts toward team total only, excluded from speaker individual tab.
    ironman=False: counts toward both team total and speaker individual tab.
    """
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="speaker_scores")
    debate_team = models.ForeignKey(DebateTeam, on_delete=models.CASCADE, related_name="speaker_scores")
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True, related_name="speaker_scores"
    )
    score = models.FloatField()
    position = models.PositiveSmallIntegerField(choices=[(1, "First Speech"), (2, "Second Speech")])
    ironman = models.BooleanField(default=False)

    class Meta:
        unique_together = [("ballot", "debate_team", "position")]
        ordering = ["debate_team__position", "position"]

    def __str__(self):
        tag = " [IRONMAN]" if self.ironman else ""
        spk = self.speaker.name if self.speaker else "Unknown"
        return f"{spk}: {self.score}{tag}"


class WSDCSpeakerScore(models.Model):
    """WSDC scores broken into Content, Style, Strategy. position=4 is reply speech."""
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="wsdc_scores")
    debate_team = models.ForeignKey(DebateTeam, on_delete=models.CASCADE, related_name="wsdc_scores")
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True, related_name="wsdc_scores"
    )
    position = models.PositiveSmallIntegerField(
        choices=[(1, "1st Speaker"), (2, "2nd Speaker"), (3, "3rd Speaker"), (4, "Reply Speech")]
    )
    is_reply = models.BooleanField(default=False)
    content = models.FloatField(default=0)
    style = models.FloatField(default=0)
    strategy = models.FloatField(default=0)

    @property
    def total(self):
        return self.content + self.style + self.strategy

    class Meta:
        unique_together = [("ballot", "debate_team", "position")]

    def __str__(self):
        spk = self.speaker.name if self.speaker else "Unknown"
        tag = " (Reply)" if self.is_reply else ""
        return f"{spk}{tag}: {self.total}"


class PSScore(models.Model):
    """Public Speaking: per-judge scores for an individual speaker."""
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="ps_scores")
    speaker = models.ForeignKey(Speaker, on_delete=models.CASCADE, related_name="ps_scores")
    delivery = models.FloatField(default=0)
    content = models.FloatField(default=0)
    structure = models.FloatField(default=0)
    language = models.FloatField(default=0)
    notes = models.TextField(blank=True)

    @property
    def total(self):
        return self.delivery + self.content + self.structure + self.language

    class Meta:
        unique_together = [("ballot", "speaker")]

    def __str__(self):
        return f"{self.speaker.name}: {self.total}"
