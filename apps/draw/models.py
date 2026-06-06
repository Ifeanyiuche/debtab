from django.db import models
from apps.tournaments.models import Round
from apps.participants.models import Team, Adjudicator
from apps.venues.models import Venue


class Debate(models.Model):
    """A single room in a round — contains teams, adjudicators, and results."""

    STATUS_NONE = 'none'
    STATUS_BALLOT_IN = 'ballot_in'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CHOICES = [
        (STATUS_NONE, 'No ballot'),
        (STATUS_BALLOT_IN, 'Ballot entered'),
        (STATUS_CONFIRMED, 'Confirmed'),
    ]

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='debates')
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True, related_name='debates')
    bracket = models.FloatField(default=0, help_text="Points bracket for power-pairing")
    room_rank = models.PositiveIntegerField(default=0, help_text="1 = top room in bracket")
    result_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NONE)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-bracket', 'room_rank']

    def __str__(self):
        venue = self.venue.name if self.venue else f"Room {self.pk}"
        return f"{self.round.name} — {venue}"

    @property
    def confirmed(self):
        return self.result_status == self.STATUS_CONFIRMED


class DebateTeam(models.Model):
    """A team's assignment to a debate, including their position and result."""

    # BP positions
    POSITION_OG = 'OG'
    POSITION_OO = 'OO'
    POSITION_CG = 'CG'
    POSITION_CO = 'CO'
    # WSDC positions
    POSITION_PROP = 'PROP'
    POSITION_OPP = 'OPP'

    POSITION_CHOICES = [
        (POSITION_OG, 'Opening Government'),
        (POSITION_OO, 'Opening Opposition'),
        (POSITION_CG, 'Closing Government'),
        (POSITION_CO, 'Closing Opposition'),
        (POSITION_PROP, 'Proposition'),
        (POSITION_OPP, 'Opposition'),
    ]

    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name='debate_teams')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='debate_teams')
    position = models.CharField(max_length=10, choices=POSITION_CHOICES)

    # BP result: 1st=3pts, 2nd=2pts, 3rd=1pt, 4th=0pts
    points = models.PositiveIntegerField(null=True, blank=True)
    rank = models.PositiveIntegerField(null=True, blank=True, help_text="1=1st, 2=2nd, 3=3rd, 4=4th")

    # WSDC result
    win = models.BooleanField(null=True, blank=True)
    ballots_won = models.PositiveIntegerField(default=0)

    # Total speaker score for this team in this debate (auto-calculated)
    total_score = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = [('debate', 'team'), ('debate', 'position')]

    def __str__(self):
        return f"{self.team.name} ({self.position}) in {self.debate}"

    @property
    def position_label(self):
        return dict(self.POSITION_CHOICES).get(self.position, self.position)


class JudgeBreak(models.Model):
    """Records which adjudicators are selected to break in an elimination round."""
    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name="judge_breaks")
    adjudicator = models.ForeignKey(Adjudicator, on_delete=models.CASCADE, related_name="judge_breaks")

    class Meta:
        unique_together = [("round", "adjudicator")]
        ordering = ["round", "adjudicator__name"]

    def __str__(self):
        return f"{self.adjudicator.name} breaking in {self.round.name}"


class DebateAdjudicator(models.Model):
    ROLE_CHAIR = 'C'
    ROLE_PANEL = 'P'
    ROLE_TRAINEE = 'T'
    ROLE_CHOICES = [
        (ROLE_CHAIR, 'Chair'),
        (ROLE_PANEL, 'Panellist'),
        (ROLE_TRAINEE, 'Trainee'),
    ]

    debate = models.ForeignKey(Debate, on_delete=models.CASCADE, related_name='debate_adjudicators')
    adjudicator = models.ForeignKey(Adjudicator, on_delete=models.CASCADE, related_name='debate_adjudicators')
    role = models.CharField(max_length=1, choices=ROLE_CHOICES, default=ROLE_CHAIR)

    class Meta:
        unique_together = [('debate', 'adjudicator')]

    def __str__(self):
        return f"{self.adjudicator.name} ({self.get_role_display()}) in {self.debate}"
