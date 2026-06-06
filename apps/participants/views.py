from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tournaments.models import Tournament
from .models import Institution, Speaker, Team, Adjudicator
from .forms import InstitutionForm, SpeakerForm, TeamForm, AdjudicatorForm, CheckInForm, ParticipantForm


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
        form.save()  # handles speaker M2M via overridden save()
        messages.success(request, f"Team '{team.name}' added.")
        return redirect("team_list", slug=t.slug)
    speakers = Speaker.objects.filter(tournament=t).order_by("name")
    institutions = t.institutions.all()
    return render(request, "participants/team_form.html", {
        "tournament": t, "form": form, "action": "Add",
        "speakers": speakers, "institutions": institutions,
    })


@login_required
def team_edit(request, slug, pk):
    t = get_tournament(slug, request.user)
    team = get_object_or_404(Team, pk=pk, tournament=t)
    form = TeamForm(t, request.POST or None, instance=team)
    if form.is_valid():
        form.save()
        messages.success(request, "Team updated.")
        return redirect("team_list", slug=t.slug)
    speakers = Speaker.objects.filter(tournament=t).order_by("name")
    institutions = t.institutions.all()
    return render(request, "participants/team_form.html", {
        "tournament": t, "form": form, "action": "Edit",
        "speakers": speakers, "institutions": institutions,
        "team": team,
    })


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
    from apps.feedback.models import AdjudicatorFeedback
    from collections import defaultdict

    t = get_tournament(slug, request.user)
    adjs = list(t.adjudicators.select_related("institution").order_by("name"))

    active_fb = list(
        AdjudicatorFeedback.objects
        .filter(adjudicator__tournament=t, ignored=False, source_adjudicator__isnull=True)
        .values("adjudicator_id", "score")
    )
    scores_by_adj = defaultdict(list)
    for fb in active_fb:
        scores_by_adj[fb["adjudicator_id"]].append(fb["score"])

    adj_rows = []
    for adj in adjs:
        scores = scores_by_adj[adj.pk]
        avg = round(sum(scores) / len(scores), 2) if scores else None
        adj_rows.append({"adj": adj, "avg_feedback": avg, "feedback_count": len(scores)})

    # Assign ranks to those with feedback
    ranked = sorted([r for r in adj_rows if r["avg_feedback"] is not None],
                    key=lambda x: (-x["avg_feedback"], -x["feedback_count"]))
    rank = 1
    for i, row in enumerate(ranked):
        if i > 0 and row["avg_feedback"] == ranked[i - 1]["avg_feedback"]:
            row["rank"] = ranked[i - 1]["rank"]
        else:
            row["rank"] = rank
        rank = i + 2
    for row in adj_rows:
        if "rank" not in row:
            row["rank"] = None

    return render(request, "participants/adjudicators.html", {"tournament": t, "adj_rows": adj_rows})


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


# ---------- General Participant Registration ----------
@login_required
def participant_register(request, slug):
    """
    Unified registration form. Registers a person as either a Speaker or Adjudicator
    depending on their selected role. This is the recommended way to add people.
    """
    t = get_tournament(slug, request.user)
    form = ParticipantForm(t, request.POST or None)
    if form.is_valid():
        d = form.cleaned_data
        role = d["role"]
        if role == ParticipantForm.ROLE_SPEAKER:
            obj = Speaker.objects.create(
                tournament=t,
                name=d["name"],
                institution=d.get("institution"),
                email=d.get("email", ""),
                is_esl=d.get("is_esl", False),
                is_efl=d.get("is_efl", False),
                is_novice=d.get("is_novice", False),
                is_schools=d.get("is_schools", False),
            )
            messages.success(request, f"Speaker '{obj.name}' registered successfully.")
        else:
            obj = Adjudicator.objects.create(
                tournament=t,
                name=d["name"],
                institution=d.get("institution"),
                email=d.get("email", ""),
                base_score=d.get("base_score") or 1.5,
                independent=d.get("independent", False),
                adj_type=d.get("adj_type", Adjudicator.TYPE_INDEPENDENT),
            )
            messages.success(request, f"Adjudicator '{obj.name}' registered successfully.")

        # Stay on the form to register more participants
        if "add_another" in request.POST:
            return redirect("participant_register", slug=t.slug)
        return redirect("participant_list", slug=t.slug)

    return render(request, "participants/register.html", {"tournament": t, "form": form})


@login_required
def participant_list(request, slug):
    """All participants (speakers + adjudicators) in one view."""
    t = get_tournament(slug, request.user)
    speakers = t.speakers.select_related("institution").order_by("name")
    adjudicators = t.adjudicators.select_related("institution").order_by("name")
    teams = t.teams.prefetch_related("speakers").select_related("institution").order_by("name")
    return render(request, "participants/participant_list.html", {
        "tournament": t,
        "speakers": speakers,
        "adjudicators": adjudicators,
        "teams": teams,
    })


@login_required
def team_detail(request, slug, team_pk):
    """Team activity log — per-round history for one team."""
    from apps.draw.models import DebateTeam
    t = get_tournament(slug, request.user)
    team = get_object_or_404(Team, pk=team_pk, tournament=t)
    debate_teams = (
        DebateTeam.objects.filter(team=team)
        .select_related("debate__round", "debate__venue")
        .prefetch_related("speaker_scores__speaker", "debate__debate_adjudicators__adjudicator")
        .order_by("debate__round__seq")
    )
    history = []
    for dt in debate_teams:
        scores = list(dt.speaker_scores.filter(ballot__confirmed=True).select_related("speaker"))
        history.append({
            "round": dt.debate.round,
            "debate": dt.debate,
            "position": dt.position,
            "position_label": dt.position_label,
            "rank": dt.rank,
            "points": dt.points,
            "total_score": dt.total_score,
            "scores": scores,
        })
    return render(request, "participants/team_detail.html", {
        "tournament": t,
        "team": team,
        "history": history,
    })


@login_required
def promote_adjudicator(request, slug, pk):
    """Tab Master only: promote trainee → panellist, or panellist → independent chair-eligible."""
    from django.views.decorators.http import require_POST
    t = get_tournament(slug, request.user)
    adj = get_object_or_404(Adjudicator, pk=pk, tournament=t)

    if request.method != "POST":
        return redirect("adjudicator_list", slug=t.slug)

    target = request.POST.get("promote_to", "")
    label_map = {
        Adjudicator.TYPE_CAP: "CAP",
        Adjudicator.TYPE_INDEPENDENT: "Independent (IA)",
        Adjudicator.TYPE_SCHOOL: "School Judge",
        Adjudicator.TYPE_NEW: "Trainee",
    }
    valid_promotions = {
        Adjudicator.TYPE_NEW: [Adjudicator.TYPE_SCHOOL, Adjudicator.TYPE_INDEPENDENT, Adjudicator.TYPE_CAP],
        Adjudicator.TYPE_SCHOOL: [Adjudicator.TYPE_INDEPENDENT, Adjudicator.TYPE_CAP, Adjudicator.TYPE_NEW],
        Adjudicator.TYPE_INDEPENDENT: [Adjudicator.TYPE_CAP, Adjudicator.TYPE_SCHOOL, Adjudicator.TYPE_NEW],
        Adjudicator.TYPE_CAP: [Adjudicator.TYPE_INDEPENDENT, Adjudicator.TYPE_SCHOOL, Adjudicator.TYPE_NEW],
    }
    if target not in valid_promotions.get(adj.adj_type, []):
        messages.error(request, "Invalid promotion target.")
        return redirect("adjudicator_list", slug=t.slug)

    old_label = label_map.get(adj.adj_type, adj.adj_type)
    adj.adj_type = target
    adj.save(update_fields=["adj_type"])
    new_label = label_map.get(target, target)
    messages.success(request, f"{adj.name} changed from {old_label} → {new_label}.")
    return redirect("adjudicator_list", slug=t.slug)


@login_required
def judge_tab(request, slug):
    """Power ranking of adjudicators based on non-ignored feedback scores."""
    from apps.feedback.models import AdjudicatorFeedback
    from collections import defaultdict

    t = get_tournament(slug, request.user)

    adjs = list(
        t.adjudicators.filter(active=True)
        .select_related("institution")
        .prefetch_related("debate_adjudicators")
        .order_by("name")
    )

    # All feedback for this tournament (both ignored and not — tab master sees all)
    all_feedback = list(
        AdjudicatorFeedback.objects
        .filter(adjudicator__tournament=t)
        .select_related("adjudicator", "source_speaker", "source_adjudicator", "debate__round")
        .order_by("debate__round__seq", "-submitted_at")
    )

    fb_by_adj = defaultdict(list)
    for fb in all_feedback:
        fb_by_adj[fb.adjudicator.pk].append(fb)

    rows = []
    for adj in adjs:
        all_fbs = fb_by_adj[adj.pk]
        # Judge-on-judge feedback shown in log (for CAP) but excluded from power ranking
        active_fbs = [f for f in all_fbs if not f.ignored and not f.source_adjudicator_id]
        count = len(active_fbs)
        avg = round(sum(f.score for f in active_fbs) / count, 2) if count > 0 else None
        high = max(f.score for f in active_fbs) if active_fbs else None
        low = min(f.score for f in active_fbs) if active_fbs else None
        rounds_judged = adj.debate_adjudicators.count()
        rows.append({
            "adj": adj,
            "all_feedback": all_fbs,
            "count": count,
            "avg": avg,
            "high": high,
            "low": low,
            "rounds_judged": rounds_judged,
        })

    ranked = sorted(
        [r for r in rows if r["avg"] is not None],
        key=lambda x: (-x["avg"], -x["count"], x["adj"].name),
    )
    unranked = sorted(
        [r for r in rows if r["avg"] is None],
        key=lambda x: x["adj"].name,
    )

    # Competition-style ranks: ties share a rank, next rank skips
    current_rank = 1
    for i, row in enumerate(ranked):
        if i > 0 and row["avg"] == ranked[i - 1]["avg"]:
            row["rank"] = ranked[i - 1]["rank"]
        else:
            row["rank"] = current_rank
        current_rank = i + 2

    for row in unranked:
        row["rank"] = None

    return render(request, "participants/judge_tab.html", {
        "tournament": t,
        "rows": ranked + unranked,
        "total_feedback": len(all_feedback),
    })


def public_participant_list(request, slug):
    """Public participant list — teams and their speakers."""
    t = get_object_or_404(Tournament, slug=slug)
    teams = t.teams.filter(active=True, is_swing=False).prefetch_related("speakers").select_related("institution").order_by("name")
    adjudicators = t.adjudicators.filter(active=True).select_related("institution").order_by("name")
    return render(request, "public/participants.html", {
        "tournament": t,
        "teams": teams,
        "adjudicators": adjudicators,
    })
