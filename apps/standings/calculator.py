"""
Standings calculators for BP, WSDC, and Public Speaking formats.
All functions return lists sorted in tab order.
"""
from django.db.models import Sum, Avg, Count, Q
from apps.draw.models import DebateTeam
from apps.results.models import SpeakerScore, WSDCSpeakerScore, PSScore
from apps.participants.models import Team, Speaker


# ─── BP ──────────────────────────────────────────────────────────────────────

def bp_team_standings(tournament, include_silent=False):
    """
    Returns sorted list of dicts for the team tab.
    Tiebreaker order: total_points > total_speaker_score > wins(1st places)
    """
    qs = DebateTeam.objects.filter(
        debate__round__tournament=tournament,
        team__active=True,
        points__isnull=False,
    )
    if not include_silent:
        qs = qs.filter(debate__round__silent=False)

    # Aggregate per team
    agg = {}
    for dt in qs.select_related("team", "debate__round"):
        tid = dt.team_id
        if tid not in agg:
            agg[tid] = {
                "team": dt.team,
                "total_points": 0,
                "total_score": 0.0,
                "rounds_competed": 0,
                "first_places": 0,
                "second_places": 0,
                "rounds_by_pos": {},
            }
        agg[tid]["total_points"] += dt.points or 0
        agg[tid]["total_score"] += dt.total_score or 0.0
        agg[tid]["rounds_competed"] += 1
        if dt.rank == 1:
            agg[tid]["first_places"] += 1
        if dt.rank == 2:
            agg[tid]["second_places"] += 1
        pos = dt.position
        agg[tid]["rounds_by_pos"][pos] = agg[tid]["rounds_by_pos"].get(pos, 0) + 1

    # Sort: points desc, then total_score desc, then first_places desc
    standings = sorted(
        agg.values(),
        key=lambda x: (x["total_points"], x["total_score"], x["first_places"]),
        reverse=True,
    )
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings


def bp_speaker_standings(tournament, include_silent=False, include_ironman=False):
    """
    Returns sorted list of dicts for the speaker tab.
    Ironman scores (ironman=True) are always excluded from individual totals.
    """
    qs = SpeakerScore.objects.filter(
        ballot__debate__round__tournament=tournament,
        ballot__confirmed=True,
        ironman=False,  # never count ironman in individual tab
        speaker__isnull=False,
    )
    if not include_silent:
        qs = qs.filter(ballot__debate__round__silent=False)

    agg = {}
    for ss in qs.select_related("speaker", "ballot__debate__round"):
        sid = ss.speaker_id
        if sid not in agg:
            agg[sid] = {
                "speaker": ss.speaker,
                "total_score": 0.0,
                "num_speeches": 0,
                "scores": [],
            }
        agg[sid]["total_score"] += ss.score
        agg[sid]["num_speeches"] += 1
        agg[sid]["scores"].append(ss.score)

    for row in agg.values():
        row["average"] = row["total_score"] / row["num_speeches"] if row["num_speeches"] else 0

    standings = sorted(
        agg.values(),
        key=lambda x: (x["total_score"], x["average"]),
        reverse=True,
    )
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings


# ─── WSDC ─────────────────────────────────────────────────────────────────────

def wsdc_team_standings(tournament):
    """
    WSDC team tab: ranked by wins, then ballots, then average speaker score.
    """
    qs = DebateTeam.objects.filter(
        debate__round__tournament=tournament,
        team__active=True,
        debate__round__silent=False,
    )
    agg = {}
    for dt in qs.select_related("team"):
        tid = dt.team_id
        if tid not in agg:
            agg[tid] = {
                "team": dt.team,
                "wins": 0,
                "ballots": 0,
                "total_score": 0.0,
                "rounds": 0,
            }
        if dt.win:
            agg[tid]["wins"] += 1
        agg[tid]["ballots"] += dt.ballots_won
        agg[tid]["total_score"] += dt.total_score or 0
        agg[tid]["rounds"] += 1

    standings = sorted(
        agg.values(),
        key=lambda x: (x["wins"], x["ballots"], x["total_score"]),
        reverse=True,
    )
    for i, row in enumerate(standings, start=1):
        row["rank"] = i
    return standings


def wsdc_speaker_standings(tournament):
    """WSDC speaker tab: total score from main speeches (not reply)."""
    qs = WSDCSpeakerScore.objects.filter(
        ballot__debate__round__tournament=tournament,
        ballot__confirmed=True,
        is_reply=False,
        speaker__isnull=False,
        ballot__debate__round__silent=False,
    )
    agg = {}
    for ss in qs.select_related("speaker"):
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
    """Public Speaking: ranked by total score across all judges."""
    qs = PSScore.objects.filter(
        ballot__debate__round__tournament=tournament,
        ballot__confirmed=True,
    ).select_related("speaker")

    agg = {}
    for ps in qs:
        sid = ps.speaker_id
        if sid not in agg:
            agg[sid] = {
                "speaker": ps.speaker,
                "total": 0.0,
                "delivery": 0.0,
                "content": 0.0,
                "structure": 0.0,
                "language": 0.0,
                "judges": 0,
            }
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
