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
    """
    Team creation with explicit first/second speaker dropdowns.
    Institution auto-populates from speaker selection via JavaScript.
    """
    speaker_1 = forms.ModelChoiceField(
        queryset=Speaker.objects.none(),
        label="First Speaker",
        required=True,
    )
    speaker_2 = forms.ModelChoiceField(
        queryset=Speaker.objects.none(),
        label="Second Speaker",
        required=False,
        help_text="Optional for single-speaker formats or incomplete teams.",
    )

    class Meta:
        model = Team
        fields = ["name", "institution", "break_category", "is_swing", "emoji"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. The Jokers, Team Alpha, UCL A"}),
            "emoji": forms.TextInput(attrs={"placeholder": "e.g. 🔥 (optional)"}),
        }

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tournament = tournament
        self.fields["institution"].queryset = Institution.objects.filter(tournament=tournament)
        self.fields["institution"].required = False

        # Speakers already assigned to any team in this tournament
        assigned_pks = set(
            Speaker.objects.filter(tournament=tournament, teams__isnull=False)
            .values_list("pk", flat=True)
        )

        # When editing, keep this team's own speakers visible in the dropdowns
        own_speaker_pks = set()
        if self.instance.pk:
            own_speaker_pks = set(self.instance.speakers.values_list("pk", flat=True))

        # Available = unassigned + already on THIS team
        available = Speaker.objects.filter(
            tournament=tournament
        ).exclude(
            pk__in=assigned_pks - own_speaker_pks
        ).order_by("name")

        self.fields["speaker_1"].queryset = available
        self.fields["speaker_2"].queryset = available

        # Pre-fill dropdowns when editing
        if self.instance.pk:
            existing = list(self.instance.speakers.all())
            if len(existing) >= 1:
                self.fields["speaker_1"].initial = existing[0]
            if len(existing) >= 2:
                self.fields["speaker_2"].initial = existing[1]

    def save(self, commit=True):
        team = super().save(commit=False)
        if commit:
            team.save()
            team.speakers.clear()
            s1 = self.cleaned_data.get("speaker_1")
            s2 = self.cleaned_data.get("speaker_2")
            if s1:
                team.speakers.add(s1)
            if s2 and s2 != s1:
                team.speakers.add(s2)
        return team


class AdjudicatorForm(forms.ModelForm):
    class Meta:
        model = Adjudicator
        fields = ["name", "institution", "email", "base_score", "adj_type", "independent"]

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["institution"].queryset = Institution.objects.filter(tournament=tournament)
        self.fields["institution"].required = False


class ParticipantForm(forms.Form):
    """
    General participant registration — creates a Speaker or Adjudicator
    depending on the selected role.
    """
    ROLE_SPEAKER = "speaker"
    ROLE_ADJUDICATOR = "adjudicator"
    ROLE_CHOICES = [
        (ROLE_SPEAKER, "Speaker / Debater"),
        (ROLE_ADJUDICATOR, "Adjudicator / Judge"),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"id": "id_role"}),
        label="Registering as",
    )
    name = forms.CharField(
        max_length=100,
        label="Full Name",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Godswill Ifeanyichukwu"}),
    )
    institution = forms.ModelChoiceField(
        queryset=Institution.objects.none(),
        required=False,
        label="Institution / School",
        help_text="Select an existing institution or leave blank.",
    )
    email = forms.EmailField(
        required=False,
        label="Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "Optional"}),
    )
    # Speaker-specific eligibility categories
    is_esl = forms.BooleanField(required=False, label="ESL (English as a Second Language)")
    is_efl = forms.BooleanField(required=False, label="EFL (English as a Foreign Language)")
    is_novice = forms.BooleanField(required=False, label="Novice")
    is_schools = forms.BooleanField(required=False, label="Schools category")
    # Adjudicator-specific
    base_score = forms.FloatField(
        required=False,
        initial=1.5,
        label="Judge Score",
        help_text="Ranking: 0=trainee, 1=panellist, 2=chair, 3=senior chair",
    )
    adj_type = forms.ChoiceField(
        choices=Adjudicator.TYPE_CHOICES,
        required=False,
        initial=Adjudicator.TYPE_INDEPENDENT,
        label="Judge type",
    )
    independent = forms.BooleanField(required=False, label="Independent adjudicator")

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tournament = tournament
        self.fields["institution"].queryset = Institution.objects.filter(tournament=tournament)


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
