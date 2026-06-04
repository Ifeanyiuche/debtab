from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.tournaments.models import Tournament, Round
from apps.draw.models import Debate, DebateTeam
from apps.participants.models import Speaker
from .models import Ballot, SpeakerScore, WSDCSpeakerScore


def get_tournament(slug, user):
    return get_object_or_404(Tournament, slug=slug, tab_master=user)


@login_required
def results_overview(request, slug, round_seq):
    t = get_tournament(slug, request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    debates = r.debates.prefetch_related(
        "debate_teams__team",
        "debate_adjudicators__adjudicator",
        "ballots",
    ).select_related("venue").order_by("room_rank")
    context = {"tournament": t, "round": r, "debates": debates}
    return render(request, "results/overview.html", context)


@login_required
def ballot_entry(request, slug, round_seq, debate_id):
    """Main ballot entry view for BP format."""
    t = get_tournament(slug, request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    debate = get_object_or_404(Debate, pk=debate_id, round=r)
    debate_teams = debate.debate_teams.select_related("team").prefetch_related(
        "team__speakers"
    ).order_by("position")

    # Get existing confirmed ballot if any
    existing_ballot = debate.ballots.filter(confirmed=True).first()

    if request.method == "POST":
        _save_bp_ballot(request, t, debate, debate_teams)
        return redirect("results_overview", slug=t.slug, round_seq=r.seq)

    # Build context: for each debate_team, include their speakers and existing scores
    teams_data = []
    for dt in debate_teams:
        speakers = list(dt.team.speakers.all())
        existing_scores = {}
        if existing_ballot:
            for ss in existing_ballot.speaker_scores.filter(debate_team=dt):
                existing_scores[ss.position] = ss
        teams_data.append({
            "debate_team": dt,
            "speakers": speakers,
            "score_1": existing_scores.get(1),
            "score_2": existing_scores.get(2),
        })

    context = {
        "tournament": t,
        "round": r,
        "debate": debate,
        "teams_data": teams_data,
        "existing_ballot": existing_ballot,
    }
    return render(request, "results/ballot.html", context)


def _save_bp_ballot(request, tournament, debate, debate_teams):
    """
    Parse and save a BP ballot from POST data.

    POST field naming convention per debate_team (by position e.g. OG):
      score_<pos>_1       float  — speech 1 score
      score_<pos>_2       float  — speech 2 score
      speaker_<pos>_1     int    — speaker pk (or "ironman")
      speaker_<pos>_2     int    — speaker pk (or "ironman")
      ironman_<pos>_1     "on"   — checkbox: speech 1 is ironman
      ironman_<pos>_2     "on"   — checkbox: speech 2 is ironman
      rank_<pos>          int    — team rank (1-4), auto-calculated client-side but editable
    """
    # Discard any old unconfirmed ballot
    debate.ballots.filter(confirmed=False).delete()
    ballot = Ballot.objects.create(debate=debate, adjudicator=None, confirmed=False)

    ranks = {}
    for dt in debate_teams:
        pos = dt.position
        rank_val = request.POST.get(f"rank_{pos}", "").strip()
        try:
            rank = int(rank_val)
        except (ValueError, TypeError):
            rank = None

        score_1_raw = request.POST.get(f"score_{pos}_1", "").strip()
        score_2_raw = request.POST.get(f"score_{pos}_2", "").strip()
        speaker_1_raw = request.POST.get(f"speaker_{pos}_1", "").strip()
        speaker_2_raw = request.POST.get(f"speaker_{pos}_2", "").strip()
        ironman_1 = request.POST.get(f"ironman_{pos}_1") == "on"
        ironman_2 = request.POST.get(f"ironman_{pos}_2") == "on"

        try:
            score_1 = float(score_1_raw)
        except ValueError:
            score_1 = None

        try:
            score_2 = float(score_2_raw)
        except ValueError:
            score_2 = None

        speaker_1 = None
        if speaker_1_raw and speaker_1_raw != "ironman":
            try:
                speaker_1 = Speaker.objects.get(pk=int(speaker_1_raw))
            except (Speaker.DoesNotExist, ValueError):
                pass

        speaker_2 = None
        if speaker_2_raw and speaker_2_raw != "ironman":
            try:
                speaker_2 = Speaker.objects.get(pk=int(speaker_2_raw))
            except (Speaker.DoesNotExist, ValueError):
                pass

        # If "ironman" selected in dropdown, force ironman flag
        if speaker_1_raw == "ironman":
            ironman_1 = True
        if speaker_2_raw == "ironman":
            ironman_2 = True

        if score_1 is not None:
            SpeakerScore.objects.create(
                ballot=ballot,
                debate_team=dt,
                speaker=speaker_1,
                score=score_1,
                position=1,
                ironman=ironman_1,
            )
        if score_2 is not None:
            SpeakerScore.objects.create(
                ballot=ballot,
                debate_team=dt,
                speaker=speaker_2,
                score=score_2,
                position=2,
                ironman=ironman_2,
            )

        total = (score_1 or 0) + (score_2 or 0)
        ranks[dt.id] = (rank, total)

    # Auto-rank: if ranks not provided, sort by total score
    if all(r[0] is None for r in ranks.values()):
        sorted_dts = sorted(debate_teams, key=lambda dt: ranks[dt.id][1], reverse=True)
        for i, dt in enumerate(sorted_dts, start=1):
            ranks[dt.id] = (i, ranks[dt.id][1])

    for dt in debate_teams:
        rank, total = ranks[dt.id]
        points = {1: 3, 2: 2, 3: 1, 4: 0}.get(rank, None)
        dt.rank = rank
        dt.points = points
        dt.total_score = ranks[dt.id][1]
        dt.save()

    ballot.confirmed = True
    ballot.save()

    # Update debate result status
    debate.result_status = Debate.STATUS_CONFIRMED
    debate.save()

    messages.success(request, "Ballot saved and results confirmed.")


@login_required
@require_POST
def release_results(request, slug, round_seq):
    t = get_tournament(slug, request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    r.results_released = True
    r.status = Round.STATUS_COMPLETED
    r.save()
    # Advance tournament current round
    if tournament := t:
        tournament.current_round_seq = r.seq + 1
        tournament.save()
    messages.success(request, "Results released to the public.")
    return redirect("results_overview", slug=t.slug, round_seq=r.seq)


@login_required
@require_POST
def unrelease_results(request, slug, round_seq):
    t = get_tournament(slug, request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    r.results_released = False
    r.status = Round.STATUS_RELEASED
    r.save()
    messages.success(request, "Results hidden from public.")
    return redirect("results_overview", slug=t.slug, round_seq=r.seq)


def public_results(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug)
    r = get_object_or_404(Round, tournament=t, seq=round_seq, results_released=True)
    debates = r.debates.prefetch_related(
        "debate_teams__team",
        "debate_teams__speaker_scores__speaker",
    ).select_related("venue").order_by("room_rank")
    return render(request, "public/results.html", {"tournament": t, "round": r, "debates": debates})
