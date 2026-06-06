"""
Standings calculators for BP, WSDC, and Public Speaking formats.
All functions return lists sorted in tab order, with per-round breakdown.
"""
import statistics
from apps.draw.models import DebateTeam
from apps.results.models import SpeakerScore, WSDCSpeakerScore, PSScore
from apps.participants.models import Team, Speaker


# ─── BP ──────────────────────────────────────────────────────────────────────

def bp_team_standings(tournament, include_silent=False, public_only=False):
    """
    Returns sorted list of dicts for the team tab.
    include_silent=True  → include rounds marked as silent (backend/admin view).
    public_only=True     → restrict to rounds where public_tab_visible=True.
    Tiebreaker: total_points > total_speaker_score > first_places
    """
    qs = DebateTeam.objects.filter(
        debate__round__tournament=tournament,
        debate__round__is_break_round=False,  # out-rounds excluded from team tab
        team__active=True,
        points__isnull=False,
    ).select_related("team__institution", "debate__round").order_by("debate__round__seq")

    if not include_silent:
        qs = qs.filter(debate__round__silent=False)
    if public_only:
        qs = qs.filter(debate__round__public_tab_visible=True)

    agg = {}
    for dt in qs:
        tid = dt.team_id
        if tid not in agg:
            agg[tid] = {
                "team": dt.team,
                "total_points": 0,
                "total_score": 0.0,
                "rounds_competed": 0,
                "first_places": 0,
                "second_places": 0,
                "rounds": {},  # round_seq -> {rank, points, score, position}
            }
        agg[tid]["total_points"] += dt.points or 0
        agg[tid]["total_score"] += dt.total_score or 0.0
        agg[tid]["rounds_competed"] += 1
        if dt.rank == 1:
            agg[tid]["first_places"] += 1
        if dt.rank == 2:
            agg[tid]["second_places"] += 1
        agg[tid]["rounds"][dt.debate.round.seq] = {
            "rank": dt.rank,
            "points": dt.points,
            "score": dt.total_score,
            "position": dt.position,
        }

    standings = sorted(
        agg.values(),
        key=lambda x: (x["total_points"], x["total_score"], x["first_places"]),
        reverse=True,
    )
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings


def bp_speaker_standings(tournament, include_silent=False, public_only=False):
    """
    Returns sorted list of dicts for the speaker tab.
    include_silent=True  → include silent rounds (backend/admin view).
    public_only=True     → restrict to rounds where public_tab_visible=True.
    Ironman scores are always excluded.
    """
    qs = SpeakerScore.objects.filter(
        ballot__debate__round__tournament=tournament,
        ballot__debate__round__is_break_round=False,  # out-rounds excluded from speaker tab
        ballot__confirmed=True,
        ironman=False,
        speaker__isnull=False,
    ).select_related("speaker__institution", "ballot__debate__round").order_by("ballot__debate__round__seq")

    if not include_silent:
        qs = qs.filter(ballot__debate__round__silent=False)
    if public_only:
        qs = qs.filter(ballot__debate__round__public_tab_visible=True)

    agg = {}
    for ss in qs:
        sid = ss.speaker_id
        if sid not in agg:
            agg[sid] = {
                "speaker": ss.speaker,
                "total_score": 0.0,
                "num_speeches": 0,
                "scores_by_round": {},  # round_seq -> score
                "scores": [],
            }
        rseq = ss.ballot.debate.round.seq
        # Keep highest score per round if multiple ballots
        existing = agg[sid]["scores_by_round"].get(rseq)
        if existing is None or ss.score > existing:
            if existing is not None:
                agg[sid]["total_score"] -= existing
                agg[sid]["scores"] = [s for s in agg[sid]["scores"] if s != existing]
            agg[sid]["scores_by_round"][rseq] = ss.score
            agg[sid]["total_score"] += ss.score
            agg[sid]["scores"].append(ss.score)
            agg[sid]["num_speeches"] = len(agg[sid]["scores_by_round"])

    for row in agg.values():
        scores = sorted(row["scores"])
        n = len(scores)
        row["average"] = row["total_score"] / n if n else 0
        row["stdev"] = round(statistics.stdev(scores), 2) if n > 1 else 0.0
        # Trimmed mean: drop highest + lowest, average the rest
        if n >= 4:
            trimmed = scores[1:-1]
            row["trimmed"] = round(sum(trimmed) / len(trimmed), 2)
        else:
            row["trimmed"] = round(row["average"], 2)

    standings = sorted(
        agg.values(),
        key=lambda x: (x["total_score"], x["average"]),
        reverse=True,
    )
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings


def get_completed_rounds(tournament, include_silent=False, public_only=False):
    """
    Returns rounds with confirmed ballots, ordered by seq.
    include_silent=True → include silent rounds (backend view).
    public_only=True    → only rounds where public_tab_visible=True.
    """
    round_ids = DebateTeam.objects.filter(
        debate__round__tournament=tournament,
        debate__round__is_break_round=False,  # out-rounds excluded from column headers
        points__isnull=False,
    ).values_list("debate__round_id", flat=True).distinct()
    qs = tournament.rounds.filter(id__in=round_ids).order_by("seq")
    if not include_silent:
        qs = qs.filter(silent=False)
    if public_only:
        qs = qs.filter(public_tab_visible=True)
    return list(qs)


# ─── WSDC ─────────────────────────────────────────────────────────────────────

def wsdc_team_standings(tournament):
    qs = DebateTeam.objects.filter(
        debate__round__tournament=tournament,
        team__active=True,
        debate__round__silent=False,
    ).select_related("team")
    agg = {}
    for dt in qs:
        tid = dt.team_id
        if tid not in agg:
            agg[tid] = {"team": dt.team, "wins": 0, "ballots": 0, "total_score": 0.0, "rounds": 0}
        if dt.win:
            agg[tid]["wins"] += 1
        agg[tid]["ballots"] += dt.ballots_won
        agg[tid]["total_score"] += dt.total_score or 0
        agg[tid]["rounds"] += 1

    standings = sorted(agg.values(), key=lambda x: (x["wins"], x["ballots"], x["total_score"]), reverse=True)
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings


def wsdc_speaker_standings(tournament):
    qs = WSDCSpeakerScore.objects.filter(
        ballot__debate__round__tournament=tournament,
        ballot__confirmed=True,
        is_reply=False,
        speaker__isnull=False,
        ballot__debate__round__silent=False,
    ).select_related("speaker")
    agg = {}
    for ss in qs:
        sid = ss.speaker_id
        if sid not in agg:
            agg[sid] = {"speaker": ss.speaker, "total": 0.0, "speeches": 0}
        agg[sid]["total"] += ss.total
        agg[sid]["speeches"] += 1

    for row in agg.values():
        row["average"] = row["total"] / row["speeches"] if row["speeches"] else 0

    standings = sorted(agg.values(), key=lambda x: x["total"], reverse=True)
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings


# ─── Public Speaking ──────────────────────────────────────────────────────────

def ps_standings(tournament):
    qs = PSScore.objects.filter(
        ballot__debate__round__tournament=tournament,
        ballot__confirmed=True,
    ).select_related("speaker")
    agg = {}
    for ps in qs:
        sid = ps.speaker_id
        if sid not in agg:
            agg[sid] = {"speaker": ps.speaker, "total": 0.0, "delivery": 0.0,
                        "content": 0.0, "structure": 0.0, "language": 0.0, "judges": 0}
        agg[sid]["total"] += ps.total
        agg[sid]["delivery"] += ps.delivery
        agg[sid]["content"] += ps.content
        agg[sid]["structure"] += ps.structure
        agg[sid]["language"] += ps.language
        agg[sid]["judges"] += 1

    standings = sorted(agg.values(), key=lambda x: x["total"], reverse=True)
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings
