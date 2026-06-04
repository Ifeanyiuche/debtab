from django import forms
from .models import Tournament, Round


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "name", "short_name", "format",
            "num_prelim_rounds",
            "speaker_score_min", "speaker_score_max",
            # WSDC-only fields — hidden for BP/PS via JavaScript
            "reply_score_min", "reply_score_max",
            "wsdc_content_weight", "wsdc_style_weight", "wsdc_strategy_weight",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Uhuru IV 2026"}),
            "short_name": forms.TextInput(attrs={"placeholder": "e.g. Uhuru 2026"}),
            "num_prelim_rounds": forms.NumberInput(attrs={"placeholder": "Leave blank to decide later"}),
            "reply_score_min": forms.NumberInput(attrs={"class": "wsdc-only-field"}),
            "reply_score_max": forms.NumberInput(attrs={"class": "wsdc-only-field"}),
            "wsdc_content_weight": forms.NumberInput(attrs={"class": "wsdc-only-field"}),
            "wsdc_style_weight": forms.NumberInput(attrs={"class": "wsdc-only-field"}),
            "wsdc_strategy_weight": forms.NumberInput(attrs={"class": "wsdc-only-field"}),
        }
        help_texts = {
            "num_prelim_rounds": "Optional — you can set or change this at any time.",
            "reply_score_min": "WSDC only — reply speech minimum score.",
            "reply_score_max": "WSDC only — reply speech maximum score.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mark WSDC-only fields so the template can wrap them in a toggle section
        wsdc_only = ["reply_score_min", "reply_score_max",
                     "wsdc_content_weight", "wsdc_style_weight", "wsdc_strategy_weight"]
        for field in wsdc_only:
            self.fields[field].required = False


class RoundForm(forms.ModelForm):
    class Meta:
        model = Round
        fields = ["name", "seq", "abbreviation", "draw_type", "is_break_round", "silent"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Round 1 or Semifinals"}),
            "abbreviation": forms.TextInput(attrs={"placeholder": "e.g. R1, SF"}),
        }
