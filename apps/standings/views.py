from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.tournaments.models import Tournament
from .calculator import (
    bp_team_standings, bp_speaker_standings, get_completed_rounds,
    wsdc_team_standings, wsdc_speaker_standings,
    ps_standings,
)


@login_required
def team_tab(request, slug):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    rounds = get_completed_rounds(t)
    if t.is_bp:
        standings = bp_team_standings(t)
    elif t.is_wsdc:
        standings = wsdc_team_standings(t)
    else:
        standings = []
    return render(request, "standings/team_tab.html", {
        "tournament": t, "standings": standings, "rounds": rounds,
    })


@login_required
def speaker_tab(request, slug):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    rounds = get_completed_rounds(t)
    if t.is_bp:
        standings = bp_speaker_standings(t)
    elif t.is_wsdc:
        standings = wsdc_speaker_standings(t)
    elif t.is_ps:
        standings = ps_standings(t)
    else:
        standings = []
    return render(request, "standings/speaker_tab.html", {
        "tournament": t, "standings": standings, "rounds": rounds,
    })


def public_team_tab(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    if not t.public_tab_released:
        return render(request, "public/tab_hidden.html", {"tournament": t})
    rounds = get_completed_rounds(t)
    standings = bp_team_standings(t) if t.is_bp else (wsdc_team_standings(t) if t.is_wsdc else [])
    return render(request, "public/team_tab.html", {
        "tournament": t, "standings": standings, "rounds": rounds,
    })


def public_speaker_tab(request, slug):
    t = get_object_or_404(Tournament, slug=slug)
    if not t.public_tab_released:
        return render(request, "public/tab_hidden.html", {"tournament": t})
    rounds = get_completed_rounds(t)
    if t.is_bp:
        standings = bp_speaker_standings(t)
    elif t.is_wsdc:
        standings = wsdc_speaker_standings(t)
    elif t.is_ps:
        standings = ps_standings(t)
    else:
        standings = []
    return render(request, "public/speaker_tab.html", {
        "tournament": t, "standings": standings, "rounds": rounds,
    })
