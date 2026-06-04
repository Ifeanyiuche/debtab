from django import forms
from .models import Tournament, Round


class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = [
            "name", "short_name", "format",
            "num_prelim_rounds",
            "speaker_score_min", "speaker_score_max",
            # WSDC-only
            "reply_score_min", "reply_score_max",
            "wsdc_content_weight", "wsdc_style_weight", "wsdc_strategy_weight",
            # PS-only
            "ps_score_min", "ps_score_max",
            "ps_delivery_weight", "ps_content_weight",
            "ps_structure_weight", "ps_language_weight",
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
            "ps_score_min": forms.NumberInput(attrs={"class": "ps-only-field"}),
            "ps_score_max": forms.NumberInput(attrs={"class": "ps-only-field"}),
            "ps_delivery_weight": forms.NumberInput(attrs={"class": "ps-only-field"}),
            "ps_content_weight": forms.NumberInput(attrs={"class": "ps-only-field"}),
            "ps_structure_weight": forms.NumberInput(attrs={"class": "ps-only-field"}),
            "ps_language_weight": forms.NumberInput(attrs={"class": "ps-only-field"}),
        }
        help_texts = {
            "num_prelim_rounds": "Optional — you can set or change this at any time.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional = [
            "reply_score_min", "reply_score_max",
            "wsdc_content_weight", "wsdc_style_weight", "wsdc_strategy_weight",
            "ps_score_min", "ps_score_max",
            "ps_delivery_weight", "ps_content_weight", "ps_structure_weight", "ps_language_weight",
        ]
        for field in optional:
            self.fields[field].required = False


class RoundForm(forms.ModelForm):
    class Meta:
        model = Round
        fields = ["name", "seq", "abbreviation", "draw_type", "is_break_round", "silent"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Round 1 or Semifinals"}),
            "abbreviation": forms.TextInput(attrs={"placeholder": "e.g. R1, SF"}),
        }
