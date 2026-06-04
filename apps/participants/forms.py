from django import forms
from .models import Institution, Speaker, Team, Adjudicator


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = ["name", "code", "region"]


class SpeakerForm(forms.ModelForm):
    class Meta:
        model = Speaker
        fields = ["name", "institution", "email", "is_esl", "is_efl", "is_novice", "is_schools"]

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.filter(tournament=tournament)
        self.fields["institution"].required = False


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "institution", "speakers", "break_category", "is_swing", "emoji"]
        widgets = {
            "speakers": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.filter(tournament=tournament)
        self.fields["institution"].required = False
        self.fields["speakers"].queryset = Speaker.objects.filter(tournament=tournament)


class AdjudicatorForm(forms.ModelForm):
    class Meta:
        model = Adjudicator
        fields = ["name", "institution", "email", "base_score", "independent"]

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.filter(tournament=tournament)
        self.fields["institution"].required = False


class CheckInForm(forms.Form):
    """Bulk check-in form — tab master marks who is present."""
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Teams present"
    )
    adjudicators = forms.ModelMultipleChoiceField(
        queryset=Adjudicator.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Adjudicators present"
    )

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["teams"].queryset = Team.objects.filter(tournament=tournament, active=True)
        self.fields["adjudicators"].queryset = Adjudicator.objects.filter(tournament=tournament, active=True)
