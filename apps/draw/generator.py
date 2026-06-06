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
    Primary objective: minimise the number of teams that repeat a position.
    Secondary objective: minimise total accumulated position count.
    Ties at both levels broken randomly.
    """
    best_perms = []
    best_repeats = float("inf")
    best_cost = float("inf")
    perms = list(itertools.permutations(BP_POSITIONS))
    random.shuffle(perms)
    for perm in perms:
        repeats = sum(1 for t, pos in zip(teams, perm) if position_cost(t.id, pos, history) > 0)
        cost = sum(position_cost(t.id, pos, history) for t, pos in zip(teams, perm))
        if repeats < best_repeats or (repeats == best_repeats and cost < best_cost):
            best_repeats = repeats
            best_cost = cost
            best_perms = [perm]
        elif repeats == best_repeats and cost == best_cost:
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
    Enhanced auto-allocation:
    - Power ranking: feedback avg score (normalised) preferred over base_score
    - Fills chair + up to 2 panelists per room; trainees distributed last
    - Avoids institution clashes with teams in the room
    - Avoids judges who have already judged the same teams in prior rounds
    - Break rounds: pool is restricted to judges on the JudgeBreak list
    """
    from collections import defaultdict
    from apps.feedback.models import AdjudicatorFeedback
    from apps.draw.models import JudgeBreak

    tournament = round_obj.tournament

    # ── Build judge pool ────────────────────────────────────────────────────
    if round_obj.is_break_round:
        breaking_pks = set(
            round_obj.judge_breaks.values_list("adjudicator_id", flat=True)
        )
        pool = list(
            Adjudicator.objects.filter(
                tournament=tournament, active=True, pk__in=breaking_pks
            ).select_related("institution")
        )
    else:
        checked_in = list(
            tournament.adjudicators.filter(active=True, checked_in=True)
            .select_related("institution")
        )
        pool = checked_in if checked_in else list(
            tournament.adjudicators.filter(active=True).select_related("institution")
        )

    # ── Power score: feedback avg (normalised 0-5) else base_score ──────────
    fb_rows = (
        AdjudicatorFeedback.objects
        .filter(adjudicator__in=pool, ignored=False)
        .values("adjudicator_id", "score")
    )
    scores_map = defaultdict(list)
    for row in fb_rows:
        scores_map[row["adjudicator_id"]].append(row["score"])

    def power_score(adj):
        scores = scores_map.get(adj.pk, [])
        return (sum(scores) / len(scores) / 2) if scores else adj.base_score

    # ── Separate trainees from regular judges ────────────────────────────────
    trainees = [a for a in pool if a.adj_type == Adjudicator.TYPE_NEW]
    regulars = sorted(
        [a for a in pool if a.adj_type != Adjudicator.TYPE_NEW],
        key=power_score, reverse=True
    )

    # ── Judge–team history (who has judged whom in prior rounds) ────────────
    past_da = list(
        DebateAdjudicator.objects.filter(
            debate__round__tournament=tournament,
            debate__round__seq__lt=round_obj.seq,
        ).values("adjudicator_id", "debate_id")
    )
    past_dt = list(
        DebateTeam.objects.filter(
            debate__round__tournament=tournament,
            debate__round__seq__lt=round_obj.seq,
        ).values("debate_id", "team_id")
    )
    teams_per_debate = defaultdict(set)
    for dt in past_dt:
        teams_per_debate[dt["debate_id"]].add(dt["team_id"])
    adj_seen_teams = defaultdict(set)
    for da in past_da:
        adj_seen_teams[da["adjudicator_id"]] |= teams_per_debate[da["debate_id"]]

    # ── Clear existing allocations ───────────────────────────────────────────
    DebateAdjudicator.objects.filter(debate__round=round_obj).delete()

    def pick(pool_list, room_teams, room_insts, skip_ids):
        """Best available judge: prefer no repeat teams AND no institution clash."""
        for adj in pool_list:
            if adj.pk in skip_ids:
                continue
            if adj.institution_id and adj.institution_id in room_insts:
                continue
            if adj_seen_teams[adj.pk] & room_teams:
                continue
            return adj
        # Relax: allow team repeat, still avoid institution clash
        for adj in pool_list:
            if adj.pk in skip_ids:
                continue
            if adj.institution_id and adj.institution_id in room_insts:
                continue
            return adj
        # Last resort: take anyone
        for adj in pool_list:
            if adj.pk not in skip_ids:
                return adj
        return None

    debates = list(round_obj.debates.prefetch_related("debate_teams__team").order_by("room_rank"))

    if round_obj.is_break_round and debates:
        # ── Break round: ALL breaking judges must be allocated ───────────────
        # Sort entire pool best-first (trainees included — they broke too)
        all_breaking = sorted(pool, key=power_score, reverse=True)
        remaining = list(all_breaking)

        # Step 1: assign best available judge as chair for each room
        for debate in debates:
            room_teams = {dt.team_id for dt in debate.debate_teams.all()}
            room_insts = {dt.team.institution_id for dt in debate.debate_teams.all() if dt.team.institution_id}
            chair = pick(remaining, room_teams, room_insts, set())
            if chair:
                DebateAdjudicator.objects.create(
                    debate=debate, adjudicator=chair, role=DebateAdjudicator.ROLE_CHAIR
                )
                remaining.remove(chair)

        # Step 2: distribute every remaining breaking judge round-robin as panelists
        for idx, adj in enumerate(remaining):
            debate = debates[idx % len(debates)]
            DebateAdjudicator.objects.create(
                debate=debate, adjudicator=adj, role=DebateAdjudicator.ROLE_PANEL
            )
        return

    # ── Prelim round: chair + 2 panelists per room, trainees distributed last ─
    available = list(regulars)  # sorted best-first; consumed as we assign

    for debate in debates:
        room_teams = {dt.team_id for dt in debate.debate_teams.all()}
        room_insts = {dt.team.institution_id for dt in debate.debate_teams.all() if dt.team.institution_id}
        used = set()

        # Chair (1)
        chair = pick(available, room_teams, room_insts, used)
        if chair:
            DebateAdjudicator.objects.create(
                debate=debate, adjudicator=chair, role=DebateAdjudicator.ROLE_CHAIR
            )
            available.remove(chair)
            used.add(chair.pk)

        # Panelists (up to 2)
        for _ in range(2):
            panelist = pick(available, room_teams, room_insts, used)
            if panelist:
                DebateAdjudicator.objects.create(
                    debate=debate, adjudicator=panelist, role=DebateAdjudicator.ROLE_PANEL
                )
                available.remove(panelist)
                used.add(panelist.pk)

    # Distribute trainees (1 per room, cycling if more rooms than trainees)
    for i, debate in enumerate(debates):
        if not trainees:
            break
        trainee = trainees[i % len(trainees)]
        DebateAdjudicator.objects.create(
            debate=debate, adjudicator=trainee, role=DebateAdjudicator.ROLE_TRAINEE
        )
