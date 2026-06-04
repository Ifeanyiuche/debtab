from django import forms
from .models import Tournament, Round


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "name", "short_name", "format",
            "num_prelim_rounds",
            "speaker_score_min", "speaker_score_max",
            "reply_score_min", "reply_score_max",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Uhuru IV 2026"}),
            "short_name": forms.TextInput(attrs={"placeholder": "e.g. Uhuru 2026"}),
            "num_prelim_rounds": forms.NumberInput(attrs={"placeholder": "Leave blank to decide later"}),
        }
        help_texts = {
            "num_prelim_rounds": "Optional — you can set or change this at any time.",
        }


class RoundForm(forms.ModelForm):
    class Meta:
        model = Round
        fields = ["name", "seq", "abbreviation", "draw_type", "is_break_round", "silent"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Round 1 or Semifinals"}),
            "abbreviation": forms.TextInput(attrs={"placeholder": "e.g. R1, SF"}),
        }
