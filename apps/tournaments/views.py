from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Max
from django.views.decorators.http import require_POST
from .models import Tournament, Round
from .forms import TournamentForm, RoundForm


def home(request):
    return render(request, "home.html")


@login_required
def tournament_list(request):
    tournaments = Tournament.objects.filter(tab_master=request.user).order_by("-created_at")
    return render(request, "tournaments/list.html", {"tournaments": tournaments})


@login_required
def tournament_create(request):
    if request.method == "POST":
        form = TournamentForm(request.POST)
        if form.is_valid():
            t = form.save(commit=False)
            t.tab_master = request.user
            t.save()
            messages.success(request, f"Tournament '{t.name}' created.")
            return redirect("tournament_overview", slug=t.slug)
    else:
        form = TournamentForm()
    return render(request, "tournaments/create.html", {"form": form})


@login_required
def tournament_overview(request, slug):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    rounds = t.rounds.all().order_by("seq")
    teams_count = t.teams.filter(active=True).count()
    adj_count = t.adjudicators.filter(active=True).count()
    speakers_count = t.speakers.count()
    context = {
        "tournament": t,
        "rounds": rounds,
        "teams_count": teams_count,
        "adj_count": adj_count,
        "speakers_count": speakers_count,
    }
    return render(request, "tournaments/overview.html", context)


@login_required
def tournament_edit(request, slug):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    if request.method == "POST":
        form = TournamentForm(request.POST, instance=t)
        if form.is_valid():
            form.save()
            messages.success(request, "Tournament settings updated.")
            return redirect("tournament_overview", slug=t.slug)
    else:
        form = TournamentForm(instance=t)
    return render(request, "tournaments/edit.html", {"form": form, "tournament": t})


def _safe_redirect(next_view, slug):
    from django.urls import NoReverseMatch
    try:
        return redirect(next_view, slug=slug)
    except NoReverseMatch:
        return redirect("tournament_overview", slug=slug)


@login_required
def round_create(request, slug):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    next_view = request.GET.get("next") or request.POST.get("next", "tournament_overview")
    if request.method == "POST":
        form = RoundForm(request.POST)
        if form.is_valid():
            r = form.save(commit=False)
            r.tournament = t
            r.save()
            messages.success(request, f"Round '{r.name}' added.")
            return _safe_redirect(next_view, t.slug)
    else:
        next_seq = (t.rounds.aggregate(Max("seq"))["seq__max"] or 0) + 1
        form = RoundForm(initial={"seq": next_seq, "name": f"Round {next_seq}"})
    next_seq = (t.rounds.aggregate(Max("seq"))["seq__max"] or 0) + 1
    return render(request, "tournaments/round_create.html", {"form": form, "tournament": t, "next": next_view, "next_seq": next_seq})


@login_required
def round_rename(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    if request.method == "POST":
        new_name = request.POST.get("name", "").strip()
        if new_name:
            r.name = new_name
            r.save(update_fields=["name"])
            messages.success(request, f"Round renamed to '{new_name}'.")
        else:
            messages.error(request, "Round name cannot be empty.")
    next_view = request.POST.get("next", "tournament_overview")
    return _safe_redirect(next_view, t.slug)


@login_required
def round_edit(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    next_view = request.GET.get("next") or request.POST.get("next", "tournament_overview")
    if request.method == "POST":
        form = RoundForm(request.POST, instance=r)
        if form.is_valid():
            form.save()
            messages.success(request, "Round updated.")
            return _safe_redirect(next_view, t.slug)
    else:
        form = RoundForm(instance=r)
    return render(request, "tournaments/round_edit.html", {"form": form, "tournament": t, "round": r, "next": next_view})


@login_required
def round_delete(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    if request.method == "POST":
        name = r.name
        r.delete()
        messages.success(request, f"Round '{name}' deleted.")
        next_view = request.POST.get("next", "tournament_overview")
        return _safe_redirect(next_view, t.slug)
    return render(request, "tournaments/round_delete_confirm.html", {"tournament": t, "round": r})


def public_overview(request, slug):
    """Public-facing tournament page — no login required."""
    t = get_object_or_404(Tournament, slug=slug, active=True)
    released_rounds = t.rounds.filter(results_released=True).order_by("seq")
    return render(request, "public/overview.html", {"tournament": t, "rounds": released_rounds})


@login_required
@require_POST
def toggle_round_tab_visibility(request, slug, round_seq):
    """Toggle whether a round appears in the public tab."""
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    r.public_tab_visible = not r.public_tab_visible
    r.save()
    status = "visible" if r.public_tab_visible else "hidden"
    messages.success(request, f"{r.name} is now {status} in the public tab.")
    return redirect("tournament_overview", slug=t.slug)


@login_required
@require_POST
def release_full_tab(request, slug):
    """Release the complete tab publicly: mark all rounds visible and set public_tab_released."""
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    t.rounds.all().update(public_tab_visible=True, results_released=True)
    t.public_tab_released = True
    t.save()
    messages.success(request, "Full tab released. All rounds are now visible to the public.")
    return redirect("tournament_overview", slug=t.slug)


@login_required
@require_POST
def hide_full_tab(request, slug):
    """Hide the full public tab (revert public_tab_released)."""
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    t.public_tab_released = False
    t.save()
    messages.success(request, "Public tab hidden. Results are still saved — re-release when ready.")
    return redirect("tournament_overview", slug=t.slug)


def _judge_rankings_for_tournament(t):
    """Return all active adjudicators sorted by feedback power ranking."""
    from apps.feedback.models import AdjudicatorFeedback
    from collections import defaultdict

    active_fb = list(
        AdjudicatorFeedback.objects
        .filter(adjudicator__tournament=t, ignored=False, source_adjudicator__isnull=True)
        .values("adjudicator_id", "score")
    )
    scores_by_adj = defaultdict(list)
    for fb in active_fb:
        scores_by_adj[fb["adjudicator_id"]].append(fb["score"])

    all_adjs = list(
        t.adjudicators.filter(active=True)
        .select_related("institution")
        .order_by("name")
    )

    rows = []
    for adj in all_adjs:
        scores = scores_by_adj[adj.pk]
        avg = round(sum(scores) / len(scores), 2) if scores else None
        rows.append({"adj": adj, "avg": avg, "count": len(scores)})

    ranked = sorted([r for r in rows if r["avg"] is not None],
                    key=lambda x: (-x["avg"], -x["count"], x["adj"].name))
    unranked = sorted([r for r in rows if r["avg"] is None],
                      key=lambda x: (-x["adj"].base_score, x["adj"].name))

    current_rank = 1
    for i, row in enumerate(ranked):
        if i > 0 and row["avg"] == ranked[i - 1]["avg"]:
            row["rank"] = ranked[i - 1]["rank"]
        else:
            row["rank"] = current_rank
        current_rank = i + 2
    for row in unranked:
        row["rank"] = None

    return ranked + unranked


@login_required
def break_setup(request, slug):
    """Generate and manage elimination/break rounds."""
    from apps.standings.calculator import bp_team_standings, get_completed_rounds
    from apps.draw.models import Debate, DebateTeam, JudgeBreak
    from apps.participants.models import Team

    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)

    BREAK_OPTIONS = [
        # (key, label, fixed_size, partial_info)
        # partial_info = (min, max, step, allowed) — None for non-partial
        ("octos_partial",    "Partial Octofinals",    None, {"min": 18, "max": 30, "step": 2, "hint": "18–30 (even number, e.g. 18, 20, 22 … 30)"}),
        ("octofinals",       "Octofinals",            32,   None),
        ("quarters_partial", "Partial Quarterfinals", None, {"min": 10, "max": 14, "step": 2, "hint": "10, 12 or 14 teams"}),
        ("quarters",         "Quarterfinals",         16,   None),
        ("semis_partial",    "Partial Semifinals",    6,    None),
        ("semis",            "Semifinals",            8,    None),
        ("finals",           "Grand Final",           4,    None),
        ("custom",           "Custom",                None, None),
    ]

    prelim_rounds = get_completed_rounds(t, include_silent=True)
    if t.is_bp:
        standings = bp_team_standings(t, include_silent=True)
    else:
        standings = []

    if request.method == "POST" and "save_judge_break" in request.POST:
        from apps.participants.models import Adjudicator as AdjModel
        round_pk = request.POST.get("judge_break_round")
        br = get_object_or_404(Round, pk=round_pk, tournament=t, is_break_round=True)
        selected_pks = set()
        for v in request.POST.getlist("breaking_adj"):
            try:
                selected_pks.add(int(v))
            except (ValueError, TypeError):
                pass
        JudgeBreak.objects.filter(round=br).delete()
        valid_adjs = t.adjudicators.filter(pk__in=selected_pks, active=True)
        JudgeBreak.objects.bulk_create([
            JudgeBreak(round=br, adjudicator=adj) for adj in valid_adjs
        ])
        messages.success(request, f"{valid_adjs.count()} breaking judge(s) saved for {br.name}.")
        return redirect("break_setup", slug=t.slug)

    if request.method == "POST":
        break_type = request.POST.get("break_type")
        custom_size = request.POST.get("custom_size", "").strip()
        round_name = request.POST.get("round_name", "").strip()
        next_seq = (t.rounds.aggregate(Max("seq"))["seq__max"] or 0) + 1

        # Determine break size
        size = None
        partial_info = None
        for key, label, fixed_size, pinfo in BREAK_OPTIONS:
            if key == break_type:
                size = fixed_size
                partial_info = pinfo
                break

        if partial_info is not None:
            # Partial break — size comes from a per-type input field
            raw = request.POST.get(f"partial_size_{break_type}", "").strip()
            try:
                size = int(raw)
            except (ValueError, TypeError):
                messages.error(request, "Enter the number of breaking teams for this partial break.")
                return redirect("break_setup", slug=t.slug)
            if size % 4 != 0:
                messages.error(request, f"Break size {size} must be a multiple of 4.")
                return redirect("break_setup", slug=t.slug)

        if break_type == "custom":
            try:
                size = int(custom_size)
                assert size >= 4 and size % 4 == 0
            except (ValueError, AssertionError):
                messages.error(request, "Custom break size must be a multiple of 4 and at least 4.")
                return redirect("break_setup", slug=t.slug)

        if not size and break_type != "custom":
            messages.error(request, "Invalid break type selected.")
            return redirect("break_setup", slug=t.slug)

        # If a previous break round has confirmed results, seed advancing teams from it.
        # Otherwise (first break round) seed from prelim standings.
        from apps.draw.models import DebateTeam as _DT
        prev_break_rounds = list(t.rounds.filter(is_break_round=True).order_by("seq"))
        last_completed_break = None
        for _br in reversed(prev_break_rounds):
            if _DT.objects.filter(debate__round=_br, rank__isnull=False).exists():
                last_completed_break = _br
                break

        if last_completed_break:
            _advancing = list(
                _DT.objects.filter(
                    debate__round=last_completed_break, rank__in=[1, 2]
                ).select_related("team", "debate").order_by("debate__room_rank", "rank")
            )
            breaking_teams = [dt.team for dt in _advancing]
            size = len(breaking_teams)
            if size < 4:
                messages.error(
                    request,
                    f"Only {size} team(s) advanced from {last_completed_break.name}. Need at least 4.",
                )
                return redirect("break_setup", slug=t.slug)
            if size % 4 != 0:
                messages.error(
                    request,
                    f"{size} teams advanced from {last_completed_break.name}, which is not a multiple of 4.",
                )
                return redirect("break_setup", slug=t.slug)
        else:
            breaking_teams = [row["team"] for row in standings[:size] if not row["team"].is_swing]
            if len(breaking_teams) < 4:
                messages.error(request, "Not enough teams to generate a break round (need at least 4).")
                return redirect("break_setup", slug=t.slug)

        if not round_name:
            round_name = dict((k, l) for k, l, s, p in BREAK_OPTIONS).get(break_type, "Break Round")

        # Create the break round
        break_round = Round.objects.create(
            tournament=t,
            seq=next_seq,
            name=round_name,
            draw_type=Round.DRAW_ELIMINATION,
            is_break_round=True,
            break_size=size,
            silent=False,
            public_tab_visible=True,
        )

        # Seed teams into debates: for each group of 4, create a debate
        # Seeding: 1v4v5v8, 2v3v6v7 etc. (standard BP seeding)
        num_debates = len(breaking_teams) // 4
        positions = ["OG", "OO", "CG", "CO"]
        for room_num in range(num_debates):
            debate = Debate.objects.create(round=break_round, room_rank=room_num + 1, bracket=0)
            # Standard BP seeding within each room
            if num_debates == 1:
                room_teams = breaking_teams[:4]
            else:
                # Interleave seeds: room 0 gets seeds 1,4,5,8 (indices 0,3,4,7 etc.)
                room_teams = []
                for i in range(4):
                    idx = room_num + (i * num_debates)
                    if idx < len(breaking_teams):
                        room_teams.append(breaking_teams[idx])
            for i, team in enumerate(room_teams[:4]):
                DebateTeam.objects.create(debate=debate, team=team, position=positions[i])

        messages.success(request, f"Break round '{round_name}' created with {num_debates} debate(s). Go to the Draw tab to manage it.")
        return redirect("draw_view", slug=t.slug, round_seq=break_round.seq)

    # Build per-elimination-round data: judge break + results
    all_adj_ranked = _judge_rankings_for_tournament(t)
    break_rounds = list(t.rounds.filter(is_break_round=True).order_by("seq"))
    break_round_data = []

    for i, br in enumerate(break_rounds):
        num_rooms = br.debates.count()
        recommended = num_rooms * 3
        breaking_pks = set(br.judge_breaks.values_list("adjudicator_id", flat=True))

        # Pool: first break round = full ranked list.
        # Subsequent rounds = only judges who broke to the previous round.
        if i == 0:
            pool = all_adj_ranked
            prev_round = None
        else:
            prev_br = break_rounds[i - 1]
            prev_breaking_pks = set(prev_br.judge_breaks.values_list("adjudicator_id", flat=True))
            pool = [row for row in all_adj_ranked if row["adj"].pk in prev_breaking_pks]
            prev_round = prev_br

        judge_rows = [
            {**row, "is_breaking": row["adj"].pk in breaking_pks}
            for row in pool
        ]

        # Collect results for each debate in this round
        debates_qs = list(
            br.debates
            .prefetch_related(
                "debate_teams__team__institution",
                "debate_adjudicators__adjudicator",
            )
            .select_related("venue")
            .order_by("room_rank")
        )
        result_debates = []
        has_any_results = False
        for debate in debates_qs:
            dts = sorted(
                debate.debate_teams.select_related("team__institution").all(),
                key=lambda x: (x.rank or 99),
            )
            confirmed = any(dt.rank is not None for dt in dts)
            if confirmed:
                has_any_results = True
            result_debates.append({
                "debate": debate,
                "teams": dts,
                "confirmed": confirmed,
            })

        # Teams advancing (rank 1 or 2) vs eliminated (rank 3 or 4) — only relevant if >1 room
        is_finals = (num_rooms == 1)
        advancing_teams = []
        eliminated_teams = []
        if has_any_results and not is_finals:
            from apps.draw.models import DebateTeam as DT
            for dt in DT.objects.filter(debate__round=br).select_related("team"):
                if dt.rank in (1, 2):
                    advancing_teams.append(dt.team)
                elif dt.rank in (3, 4):
                    eliminated_teams.append(dt.team)

        # Teams currently in this break round (from debate room assignments)
        from apps.draw.models import DebateTeam as _DT2
        teams_in_round = list(
            _DT2.objects.filter(debate__round=br)
            .select_related("team", "team__institution", "debate")
            .order_by("debate__room_rank", "position")
        )

        # Judge advancement: who advances to the next break round vs who stops here
        from apps.participants.models import Adjudicator as AdjModel
        advancing_judges = []
        eliminated_judges = []
        next_round = None
        if i < len(break_rounds) - 1:
            next_round = break_rounds[i + 1]
            next_breaking_pks = set(next_round.judge_breaks.values_list("adjudicator_id", flat=True))
            if breaking_pks:
                for adj in AdjModel.objects.filter(pk__in=breaking_pks).select_related("institution").order_by("name"):
                    if adj.pk in next_breaking_pks:
                        advancing_judges.append(adj)
                    else:
                        eliminated_judges.append(adj)

        break_round_data.append({
            "round": br,
            "num_rooms": num_rooms,
            "recommended": recommended,
            "judge_rows": judge_rows,
            "breaking_count": len(breaking_pks),
            "pool_size": len(pool),
            "prev_round": prev_round,
            "result_debates": result_debates,
            "has_any_results": has_any_results,
            "is_finals": is_finals,
            "advancing_teams": advancing_teams,
            "eliminated_teams": eliminated_teams,
            "next_round": next_round,
            "advancing_judges": advancing_judges,
            "eliminated_judges": eliminated_judges,
            "teams_in_round": teams_in_round,
        })

    context = {
        "tournament": t,
        "standings": standings,
        "break_options": BREAK_OPTIONS,
        "prelim_rounds": prelim_rounds,
        "break_round_data": break_round_data,
    }
    return render(request, "tournaments/break_setup.html", context)
