from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.tournaments.models import Tournament, Round
from apps.participants.models import Adjudicator
from .models import Debate, DebateTeam, DebateAdjudicator
from .generator import generate_bp_draw, auto_allocate_adjudicators


def get_t_and_round(slug, round_seq, user):
    t = get_object_or_404(Tournament, slug=slug, tab_master=user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    return t, r


@login_required
def draw_view(request, slug, round_seq):
    t, r = get_t_and_round(slug, round_seq, request.user)
    debates = r.debates.prefetch_related(
        "debate_teams__team__institution",
        "debate_adjudicators__adjudicator",
    ).select_related("venue").order_by("room_rank")
    all_adjs = t.adjudicators.filter(active=True).order_by("name")
    all_teams = t.teams.filter(active=True).order_by("name")
    context = {
        "tournament": t,
        "round": r,
        "debates": debates,
        "all_adjs": all_adjs,
        "all_teams": all_teams,
        "bp_positions": ["OG", "OO", "CG", "CO"],
    }
    return render(request, "draw/draw.html", context)


@login_required
@require_POST
def generate_draw(request, slug, round_seq):
    t, r = get_t_and_round(slug, round_seq, request.user)
    if r.status not in (Round.STATUS_DRAFT, Round.STATUS_CONFIRMED):
        messages.error(request, "Cannot regenerate a released draw.")
        return redirect("draw_view", slug=t.slug, round_seq=r.seq)
    try:
        if t.is_bp:
            debates = generate_bp_draw(r)
            messages.success(request, f"Draw generated: {len(debates)} rooms.")
        else:
            messages.warning(request, "Auto-draw for this format coming soon. Please build manually.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("draw_view", slug=t.slug, round_seq=r.seq)


@login_required
@require_POST
def auto_allocate(request, slug, round_seq):
    t, r = get_t_and_round(slug, round_seq, request.user)
    auto_allocate_adjudicators(r)
    messages.success(request, "Adjudicators auto-allocated.")
    return redirect("draw_view", slug=t.slug, round_seq=r.seq)


@login_required
@require_POST
def confirm_draw(request, slug, round_seq):
    t, r = get_t_and_round(slug, round_seq, request.user)
    r.status = Round.STATUS_CONFIRMED
    r.save()
    messages.success(request, "Draw confirmed.")
    return redirect("draw_view", slug=t.slug, round_seq=r.seq)


@login_required
@require_POST
def release_draw(request, slug, round_seq):
    t, r = get_t_and_round(slug, round_seq, request.user)
    r.draw_released = True
    r.status = Round.STATUS_RELEASED
    r.save()
    messages.success(request, "Draw released to the public.")
    return redirect("draw_view", slug=t.slug, round_seq=r.seq)


@login_required
@require_POST
def unrelease_draw(request, slug, round_seq):
    t, r = get_t_and_round(slug, round_seq, request.user)
    r.draw_released = False
    r.save()
    messages.success(request, "Draw hidden from public.")
    return redirect("draw_view", slug=t.slug, round_seq=r.seq)


@login_required
def edit_debate(request, slug, round_seq, debate_id):
    """Manual edit: reassign teams/positions and adjudicators in a room."""
    t, r = get_t_and_round(slug, round_seq, request.user)
    debate = get_object_or_404(Debate, pk=debate_id, round=r)
    all_teams = t.teams.filter(active=True).order_by("name")
    all_adjs = t.adjudicators.filter(active=True).order_by("name")
    debate_teams = debate.debate_teams.select_related("team").order_by("position")
    debate_adjs = debate.debate_adjudicators.select_related("adjudicator")

    if request.method == "POST":
        # Update team positions
        debate.debate_teams.all().delete()
        positions = ["OG", "OO", "CG", "CO"] if t.is_bp else ["PROP", "OPP"]
        for pos in positions:
            team_id = request.POST.get(f"team_{pos}")
            if team_id:
                DebateTeam.objects.create(
                    debate=debate,
                    team_id=int(team_id),
                    position=pos,
                )
        # Update adjudicators
        debate.debate_adjudicators.all().delete()
        chair_id = request.POST.get("chair")
        if chair_id:
            DebateAdjudicator.objects.create(
                debate=debate, adjudicator_id=int(chair_id), role=DebateAdjudicator.ROLE_CHAIR
            )
        for panel_id in request.POST.getlist("panellists"):
            DebateAdjudicator.objects.create(
                debate=debate, adjudicator_id=int(panel_id), role=DebateAdjudicator.ROLE_PANEL
            )
        for trainee_id in request.POST.getlist("trainees"):
            DebateAdjudicator.objects.create(
                debate=debate, adjudicator_id=int(trainee_id), role=DebateAdjudicator.ROLE_TRAINEE
            )
        messages.success(request, "Room updated.")
        return redirect("draw_view", slug=t.slug, round_seq=r.seq)

    context = {
        "tournament": t,
        "round": r,
        "debate": debate,
        "debate_teams": debate_teams,
        "debate_adjs": debate_adjs,
        "all_teams": all_teams,
        "all_adjs": all_adjs,
        "positions": ["OG", "OO", "CG", "CO"] if t.is_bp else ["PROP", "OPP"],
    }
    return render(request, "draw/edit_debate.html", context)


def public_draw(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug)
    r = get_object_or_404(Round, tournament=t, seq=round_seq, draw_released=True)
    debates = r.debates.prefetch_related(
        "debate_teams__team",
        "debate_adjudicators__adjudicator",
    ).select_related("venue").order_by("room_rank")
    return render(request, "public/draw.html", {"tournament": t, "round": r, "debates": debates})
