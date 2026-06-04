"""
BP Draw Generator
-----------------
Round 1: Random draw with random position assignment.
Round 2+: Power-paired draw — teams with equal points meet.
           Positions (OG/OO/CG/CO) assigned to minimise repetition.

Swing teams:
  If the team count is not divisible by 4, the tab master is expected
  to add swing teams first. This generator assumes divisible-by-4.
"""
import random
import itertools
from django.db import transaction
from apps.draw.models import Debate, DebateTeam, DebateAdjudicator
from apps.participants.models import Team, Adjudicator
from apps.results.models import SpeakerScore


BP_POSITIONS = ["OG", "OO", "CG", "CO"]
POINTS_MAP = {1: 3, 2: 2, 3: 1, 4: 0}  # rank → team points


def get_team_points(tournament, up_to_round_seq=None):
    """Return {team_id: total_points} for all active, non-swing teams."""
    from apps.draw.models import DebateTeam as DT
    qs = DT.objects.filter(
        debate__round__tournament=tournament,
        team__active=True,
        points__isnull=False,
    )
    if up_to_round_seq is not None:
        qs = qs.filter(debate__round__seq__lt=up_to_round_seq)
    totals = {}
    for dt in qs.select_related("team"):
        totals[dt.team_id] = totals.get(dt.team_id, 0) + (dt.points or 0)
    return totals


def get_position_history(tournament, up_to_round_seq=None):
    """Return {team_id: {position: count}} for BP position rotation."""
    from apps.draw.models import DebateTeam as DT
    qs = DT.objects.filter(debate__round__tournament=tournament, team__active=True)
    if up_to_round_seq is not None:
        qs = qs.filter(debate__round__seq__lt=up_to_round_seq)
    history = {}
    for dt in qs.select_related("team"):
        history.setdefault(dt.team_id, {})
        history[dt.team_id][dt.position] = history[dt.team_id].get(dt.position, 0) + 1
    return history


def position_cost(team_id, position, history):
    """Cost of assigning a position: how many times team has had it."""
    return history.get(team_id, {}).get(position, 0)


def best_position_assignment(teams, history):
    """
    Try all 24 permutations of BP_POSITIONS for the 4 teams.
    Return the permutation with the lowest total position-repetition cost.
    Ties are broken randomly.
    """
    best_perms = []
    best_cost = float("inf")
    perms = list(itertools.permutations(BP_POSITIONS))
    random.shuffle(perms)
    for perm in perms:
        cost = sum(position_cost(t.id, pos, history) for t, pos in zip(teams, perm))
        if cost < best_cost:
            best_cost = cost
            best_perms = [perm]
        elif cost == best_cost:
            best_perms.append(perm)
    return dict(zip(teams, random.choice(best_perms)))


def avoid_institution_clashes(rooms, max_swaps=20):
    """
    Attempt to reduce same-institution rooms by swapping teams between rooms.
    Greedy approach — not guaranteed optimal.
    """
    def institution_clash_count(room):
        insts = [t.institution_id for t in room if t.institution_id]
        return len(insts) - len(set(insts))

    improved = True
    attempts = 0
    while improved and attempts < max_swaps:
        improved = False
        attempts += 1
        for i in range(len(rooms)):
            if institution_clash_count(rooms[i]) == 0:
                continue
            for j in range(len(rooms)):
                if i == j:
                    continue
                for ti, team_i in enumerate(rooms[i]):
                    for tj, team_j in enumerate(rooms[j]):
                        # Try swap
                        rooms[i][ti], rooms[j][tj] = rooms[j][tj], rooms[i][ti]
                        new_cost = institution_clash_count(rooms[i]) + institution_clash_count(rooms[j])
                        old_cost = institution_clash_count(rooms[j]) + institution_clash_count(rooms[i])
                        # This comparison is same after swap, so check against original
                        # Revert if not better
                        orig_i_clash = institution_clash_count(rooms[i])
                        orig_j_clash = institution_clash_count(rooms[j])
                        rooms[i][ti], rooms[j][tj] = rooms[j][tj], rooms[i][ti]  # revert
                        orig_cost = institution_clash_count(rooms[i]) + institution_clash_count(rooms[j])
                        # Apply swap if it strictly reduces clashes
                        rooms[i][ti], rooms[j][tj] = rooms[j][tj], rooms[i][ti]
                        if (institution_clash_count(rooms[i]) + institution_clash_count(rooms[j])) < orig_cost:
                            improved = True
                        else:
                            rooms[i][ti], rooms[j][tj] = rooms[j][tj], rooms[i][ti]  # revert
    return rooms


@transaction.atomic
def generate_bp_draw(round_obj):
    """
    Generate a BP draw for the given Round object.
    Deletes any existing draft debates for this round first.
    Returns the list of created Debate objects.
    """
    tournament = round_obj.tournament

    # Use checked-in teams if any have been checked in; otherwise use all active teams.
    # This means check-in is optional — the draw will always work even without it.
    checked_in_teams = list(tournament.teams.filter(active=True, checked_in=True))
    all_active_teams = list(tournament.teams.filter(active=True))

    if checked_in_teams:
        teams = checked_in_teams
    else:
        teams = all_active_teams

    random.shuffle(teams)

    if len(teams) == 0:
        raise ValueError(
            "Cannot generate draw: no teams are registered in this tournament. "
            "Add teams under Participants → Teams first."
        )

    if len(teams) % 4 != 0:
        raise ValueError(
            f"Cannot generate draw: {len(teams)} team{'s' if len(teams) != 1 else ''} available. "
            f"BP requires a number divisible by 4. "
            f"You need {4 - (len(teams) % 4)} more team{'s' if 4 - (len(teams) % 4) != 1 else ''} "
            f"(or add a swing team to make up the numbers)."
        )

    # Delete existing draft debates
    round_obj.debates.all().delete()

    position_history = get_position_history(tournament, up_to_round_seq=round_obj.seq)

    if round_obj.is_first_round or round_obj.draw_type == "R":
        # Random: teams already shuffled, split into rooms of 4
        rooms = [teams[i:i+4] for i in range(0, len(teams), 4)]
    else:
        # Power-paired: sort by points desc, split into brackets
        points = get_team_points(tournament, up_to_round_seq=round_obj.seq)
        teams.sort(key=lambda t: points.get(t.id, 0), reverse=True)

        # Group into brackets by point total
        brackets = {}
        for team in teams:
            pts = points.get(team.id, 0)
            brackets.setdefault(pts, []).append(team)

        # Build rooms pulling up from lower brackets when needed
        rooms = []
        overflow = []
        for pts in sorted(brackets.keys(), reverse=True):
            bracket = overflow + brackets[pts]
            overflow = []
            while len(bracket) >= 4:
                rooms.append(bracket[:4])
                bracket = bracket[4:]
            overflow = bracket
        # Any leftover (shouldn't happen after swing team check, but safety net)
        if overflow:
            rooms[-1].extend(overflow)

        # Try to reduce institution clashes within rooms
        rooms = avoid_institution_clashes(rooms)

    # Allocate venues in priority order
    venues = list(tournament.venues.all().order_by("-priority"))

    debates = []
    for rank, room in enumerate(rooms, start=1):
        debate = Debate.objects.create(
            round=round_obj,
            venue=venues[rank - 1] if rank <= len(venues) else None,
            bracket=sum(get_team_points(tournament, round_obj.seq).get(t.id, 0) for t in room) / 4,
            room_rank=rank,
        )
        position_map = best_position_assignment(room, position_history)
        for team, position in position_map.items():
            DebateTeam.objects.create(debate=debate, team=team, position=position)
        debates.append(debate)

    return debates


@transaction.atomic
def auto_allocate_adjudicators(round_obj):
    """
    Simple auto-allocation: sort adjudicators by base_score desc,
    assign the highest-ranked available adj as chair to the top room, etc.
    Avoids institution clashes with teams in the room.
    """
    debates = list(round_obj.debates.all().order_by("room_rank"))
    adjs = list(round_obj.tournament.adjudicators.filter(active=True, checked_in=True).order_by("-base_score"))

    # Clear existing allocations
    DebateAdjudicator.objects.filter(debate__round=round_obj).delete()

    for debate in debates:
        team_institutions = set(
            dt.team.institution_id
            for dt in debate.debate_teams.select_related("team")
            if dt.team.institution_id
        )
        # Find best chair (no institution clash)
        for adj in adjs:
            if adj.institution_id not in team_institutions:
                DebateAdjudicator.objects.create(
                    debate=debate, adjudicator=adj, role=DebateAdjudicator.ROLE_CHAIR
                )
                adjs.remove(adj)
                break
        else:
            # No clash-free adj available — assign anyway
            if adjs:
                adj = adjs.pop(0)
                DebateAdjudicator.objects.create(
                    debate=debate, adjudicator=adj, role=DebateAdjudicator.ROLE_CHAIR
                )
