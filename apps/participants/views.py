from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tournaments.models import Tournament
from .models import Institution, Speaker, Team, Adjudicator
from .forms import InstitutionForm, SpeakerForm, TeamForm, AdjudicatorForm, CheckInForm


def get_tournament(slug, user):
    return get_object_or_404(Tournament, slug=slug, tab_master=user)


# ---------- Institutions ----------
@login_required
def institution_list(request, slug):
    t = get_tournament(slug, request.user)
    institutions = t.institutions.all()
    return render(request, "participants/institutions.html", {"tournament": t, "institutions": institutions})


@login_required
def institution_create(request, slug):
    t = get_tournament(slug, request.user)
    form = InstitutionForm(request.POST or None)
    if form.is_valid():
        inst = form.save(commit=False)
        inst.tournament = t
        inst.save()
        messages.success(request, f"Institution '{inst.name}' added.")
        return redirect("institution_list", slug=t.slug)
    return render(request, "participants/institution_form.html", {"tournament": t, "form": form, "action": "Add"})


@login_required
def institution_edit(request, slug, pk):
    t = get_tournament(slug, request.user)
    inst = get_object_or_404(Institution, pk=pk, tournament=t)
    form = InstitutionForm(request.POST or None, instance=inst)
    if form.is_valid():
        form.save()
        messages.success(request, "Institution updated.")
        return redirect("institution_list", slug=t.slug)
    return render(request, "participants/institution_form.html", {"tournament": t, "form": form, "action": "Edit"})


@login_required
def institution_delete(request, slug, pk):
    t = get_tournament(slug, request.user)
    inst = get_object_or_404(Institution, pk=pk, tournament=t)
    if request.method == "POST":
        inst.delete()
        messages.success(request, "Institution deleted.")
        return redirect("institution_list", slug=t.slug)
    return render(request, "participants/confirm_delete.html", {"tournament": t, "object": inst, "type": "Institution"})


# ---------- Speakers ----------
@login_required
def speaker_list(request, slug):
    t = get_tournament(slug, request.user)
    speakers = t.speakers.select_related("institution").order_by("name")
    return render(request, "participants/speakers.html", {"tournament": t, "speakers": speakers})


@login_required
def speaker_create(request, slug):
    t = get_tournament(slug, request.user)
    form = SpeakerForm(t, request.POST or None)
    if form.is_valid():
        s = form.save(commit=False)
        s.tournament = t
        s.save()
        messages.success(request, f"Speaker '{s.name}' added.")
        return redirect("speaker_list", slug=t.slug)
    return render(request, "participants/speaker_form.html", {"tournament": t, "form": form, "action": "Add"})


@login_required
def speaker_edit(request, slug, pk):
    t = get_tournament(slug, request.user)
    speaker = get_object_or_404(Speaker, pk=pk, tournament=t)
    form = SpeakerForm(t, request.POST or None, instance=speaker)
    if form.is_valid():
        form.save()
        messages.success(request, "Speaker updated.")
        return redirect("speaker_list", slug=t.slug)
    return render(request, "participants/speaker_form.html", {"tournament": t, "form": form, "action": "Edit"})


@login_required
def speaker_delete(request, slug, pk):
    t = get_tournament(slug, request.user)
    speaker = get_object_or_404(Speaker, pk=pk, tournament=t)
    if request.method == "POST":
        speaker.delete()
        messages.success(request, "Speaker deleted.")
        return redirect("speaker_list", slug=t.slug)
    return render(request, "participants/confirm_delete.html", {"tournament": t, "object": speaker, "type": "Speaker"})


# ---------- Teams ----------
@login_required
def team_list(request, slug):
    t = get_tournament(slug, request.user)
    teams = t.teams.prefetch_related("speakers").select_related("institution").order_by("name")
    return render(request, "participants/teams.html", {"tournament": t, "teams": teams})


@login_required
def team_create(request, slug):
    t = get_tournament(slug, request.user)
    form = TeamForm(t, request.POST or None)
    if form.is_valid():
        team = form.save(commit=False)
        team.tournament = t
        team.save()
        form.save_m2m()
        messages.success(request, f"Team '{team.name}' added.")
        return redirect("team_list", slug=t.slug)
    return render(request, "participants/team_form.html", {"tournament": t, "form": form, "action": "Add"})


@login_required
def team_edit(request, slug, pk):
    t = get_tournament(slug, request.user)
    team = get_object_or_404(Team, pk=pk, tournament=t)
    form = TeamForm(t, request.POST or None, instance=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Team updated.")
        return redirect("team_list", slug=t.slug)
    return render(request, "participants/team_form.html", {"tournament": t, "form": form, "action": "Edit"})


@login_required
def team_delete(request, slug, pk):
    t = get_tournament(slug, request.user)
    team = get_object_or_404(Team, pk=pk, tournament=t)
    if request.method == "POST":
        team.delete()
        messages.success(request, "Team deleted.")
        return redirect("team_list", slug=t.slug)
    return render(request, "participants/confirm_delete.html", {"tournament": t, "object": team, "type": "Team"})


# ---------- Adjudicators ----------
@login_required
def adjudicator_list(request, slug):
    t = get_tournament(slug, request.user)
    adjs = t.adjudicators.select_related("institution").order_by("name")
    return render(request, "participants/adjudicators.html", {"tournament": t, "adjudicators": adjs})


@login_required
def adjudicator_create(request, slug):
    t = get_tournament(slug, request.user)
    form = AdjudicatorForm(t, request.POST or None)
    if form.is_valid():
        adj = form.save(commit=False)
        adj.tournament = t
        adj.save()
        messages.success(request, f"Adjudicator '{adj.name}' added.")
        return redirect("adjudicator_list", slug=t.slug)
    return render(request, "participants/adjudicator_form.html", {"tournament": t, "form": form, "action": "Add"})


@login_required
def adjudicator_edit(request, slug, pk):
    t = get_tournament(slug, request.user)
    adj = get_object_or_404(Adjudicator, pk=pk, tournament=t)
    form = AdjudicatorForm(t, request.POST or None, instance=adj)
    if form.is_valid():
        form.save()
        messages.success(request, "Adjudicator updated.")
        return redirect("adjudicator_list", slug=t.slug)
    return render(request, "participants/adjudicator_form.html", {"tournament": t, "form": form, "action": "Edit"})


@login_required
def adjudicator_delete(request, slug, pk):
    t = get_tournament(slug, request.user)
    adj = get_object_or_404(Adjudicator, pk=pk, tournament=t)
    if request.method == "POST":
        adj.delete()
        messages.success(request, "Adjudicator deleted.")
        return redirect("adjudicator_list", slug=t.slug)
    return render(request, "participants/confirm_delete.html", {"tournament": t, "object": adj, "type": "Adjudicator"})


# ---------- Check-in ----------
@login_required
def check_in(request, slug):
    t = get_tournament(slug, request.user)
    if request.method == "POST":
        form = CheckInForm(t, request.POST)
        if form.is_valid():
            t.teams.filter(active=True).update(checked_in=False)
            t.adjudicators.filter(active=True).update(checked_in=False)
            form.cleaned_data["teams"].update(checked_in=True)
            form.cleaned_data["adjudicators"].update(checked_in=True)
            messages.success(request, "Check-in saved.")
            return redirect("tournament_overview", slug=t.slug)
    else:
        initial_teams = t.teams.filter(checked_in=True)
        initial_adjs = t.adjudicators.filter(checked_in=True)
        form = CheckInForm(t, initial={"teams": initial_teams, "adjudicators": initial_adjs})
    return render(request, "participants/check_in.html", {"tournament": t, "form": form})
