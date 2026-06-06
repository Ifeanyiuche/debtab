from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
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
    is_break_round = r.is_break_round
    _BP_ORDER = {"OG": 0, "OO": 1, "CG": 2, "CO": 3}
    debate_teams = sorted(
        debate.debate_teams.select_related("team").prefetch_related("team__speakers"),
        key=lambda dt: _BP_ORDER.get(dt.position, 99),
    )

    existing_ballot = debate.ballots.filter(confirmed=True).first()

    if request.method == "POST":
        try:
            if is_break_round:
                _save_bp_outround_ballot(request, debate, debate_teams)
            else:
                _save_bp_ballot(request, t, debate, debate_teams)
            return redirect("results_overview", slug=t.slug, round_seq=r.seq)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("ballot_entry", slug=t.slug, round_seq=r.seq, debate_id=debate.pk)

    teams_data = []
    for dt in debate_teams:
        speakers = list(dt.team.speakers.all())
        existing_scores = {}
        if existing_ballot and not is_break_round:
            for ss in existing_ballot.speaker_scores.filter(debate_team=dt):
                existing_scores[ss.position] = ss
        teams_data.append({
            "debate_team": dt,
            "pos": dt.position,
            "speakers": speakers,
            "score_1": existing_scores.get(1),
            "score_2": existing_scores.get(2),
            "has_saved_scores": bool(existing_scores) if not is_break_round else bool(dt.rank),
        })

    is_finals = is_break_round and (r.debates.count() == 1)
    context = {
        "tournament": t,
        "round": r,
        "debate": debate,
        "teams_data": teams_data,
        "existing_ballot": existing_ballot,
        "is_break_round": is_break_round,
        "is_finals": is_finals,
    }
    return render(request, "results/ballot.html", context)


def _save_bp_outround_ballot(request, debate, debate_teams):
    """Break-round ballot: collect only ranks (1st–4th), no speaker scores."""
    _RANK_LABELS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
    ranks = {}
    for dt in debate_teams:
        pos = dt.position
        rank_raw = request.POST.get(f"rank_{pos}", "").strip()
        try:
            rank = int(rank_raw)
            assert 1 <= rank <= 4
        except (ValueError, TypeError, AssertionError):
            raise ValueError(
                f"Select a rank for {dt.position_label} ({dt.team.name})."
            )
        if rank in ranks.values():
            dup_pos = next(k for k, v in ranks.items() if v == rank)
            raise ValueError(
                f"{_RANK_LABELS[rank]} assigned to both {dup_pos} and {pos}. Each rank must be unique."
            )
        ranks[pos] = rank

    if set(ranks.values()) != {1, 2, 3, 4}:
        raise ValueError("Assign exactly one team to each rank (1st through 4th).")

    debate.ballots.all().delete()
    Ballot.objects.create(debate=debate, adjudicator=None, confirmed=True)

    for dt in debate_teams:
        rank = ranks[dt.position]
        dt.rank = rank
        dt.points = {1: 3, 2: 2, 3: 1, 4: 0}[rank]
        dt.total_score = 0
        dt.save()

    debate.result_status = Debate.STATUS_CONFIRMED
    debate.save()

    messages.success(request, "Break round results saved.")


def _save_bp_ballot(request, tournament, debate, debate_teams):
    # ── Validate ALL scores before touching the database ──────────────
    parsed = {}
    for dt in debate_teams:
        pos = dt.position
        s1_raw = request.POST.get(f"score_{pos}_1", "").strip()
        s2_raw = request.POST.get(f"score_{pos}_2", "").strip()
        try:
            s1 = float(s1_raw)
            assert s1 > 0
        except (ValueError, TypeError, AssertionError):
            raise ValueError(
                f"Score missing or zero for {pos} 1st speaker. "
                "Enter a score for every speaker before saving."
            )
        try:
            s2 = float(s2_raw)
            assert s2 > 0
        except (ValueError, TypeError, AssertionError):
            raise ValueError(
                f"Score missing or zero for {pos} 2nd speaker. "
                "Enter a score for every speaker before saving."
            )
        parsed[pos] = (s1, s2)

    # ── All scores present — safe to write ───────────────────────────
    debate.ballots.all().delete()  # wipes old confirmed + unconfirmed; SpeakerScores cascade
    ballot = Ballot.objects.create(debate=debate, adjudicator=None, confirmed=False)

    ranks = {}
    for dt in debate_teams:
        pos = dt.position
        rank_val = request.POST.get(f"rank_{pos}", "").strip()
        try:
            rank = int(rank_val)
        except (ValueError, TypeError):
            rank = None

        score_1, score_2 = parsed[pos]
        speaker_1_raw = request.POST.get(f"speaker_{pos}_1", "").strip()
        speaker_2_raw = request.POST.get(f"speaker_{pos}_2", "").strip()
        ironman_1 = speaker_1_raw == "ironman" or request.POST.get(f"ironman_{pos}_1") == "on"
        ironman_2 = speaker_2_raw == "ironman" or request.POST.get(f"ironman_{pos}_2") == "on"

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

        SpeakerScore.objects.create(
            ballot=ballot,
            debate_team=dt,
            speaker=speaker_1,
            score=score_1,
            position=1,
            ironman=ironman_1,
        )
        SpeakerScore.objects.create(
            ballot=ballot,
            debate_team=dt,
            speaker=speaker_2,
            score=score_2,
            position=2,
            ironman=ironman_2,
        )

        total = score_1 + score_2
        ranks[dt.id] = (rank, total)

    # Auto-rank: ensure ranks form a complete, unique set {1, 2, 3, 4}.
    # If the submitted ranks are already valid, use them; otherwise rank by total score.
    submitted_rank_values = {v[0] for v in ranks.values() if v[0] is not None}
    valid_manual = submitted_rank_values == {1, 2, 3, 4}
    if not valid_manual:
        sorted_dts = sorted(
            debate_teams,
            key=lambda dt: (ranks[dt.id][1], dt.position),
            reverse=True,
        )
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


@login_required
def ballots_overview(request, slug):
    """Tournament-wide ballot management — all rounds and their debates."""
    t = get_tournament(slug, request.user)
    rounds = t.rounds.prefetch_related(
        "debates__debate_teams__team",
        "debates__debate_adjudicators__adjudicator",
        "debates__ballots",
    ).order_by("seq")

    rounds_data = []
    for r in rounds:
        debates = list(r.debates.all().order_by("room_rank"))
        confirmed = sum(1 for d in debates if d.result_status == Debate.STATUS_CONFIRMED)
        rounds_data.append({
            "round": r,
            "debates": debates,
            "confirmed": confirmed,
            "total": len(debates),
        })

    context = {"tournament": t, "rounds_data": rounds_data}
    return render(request, "results/ballots_overview.html", context)


@login_required
@require_POST
def ballot_save_ajax(request, slug, round_seq, debate_id):
    """AJAX endpoint — saves ballot and returns JSON (no redirect)."""
    t = get_tournament(slug, request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    debate = get_object_or_404(Debate, pk=debate_id, round=r)
    _BP_ORDER = {"OG": 0, "OO": 1, "CG": 2, "CO": 3}
    debate_teams = sorted(
        debate.debate_teams.select_related("team").prefetch_related("team__speakers"),
        key=lambda dt: _BP_ORDER.get(dt.position, 99),
    )
    try:
        if r.is_break_round:
            _save_bp_outround_ballot(request, debate, debate_teams)
        else:
            _save_bp_ballot(request, t, debate, debate_teams)
        return JsonResponse({"status": "ok"})
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=400)
