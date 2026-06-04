from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count
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


@login_required
def round_create(request, slug):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    if request.method == "POST":
        form = RoundForm(request.POST)
        if form.is_valid():
            r = form.save(commit=False)
            r.tournament = t
            r.save()
            messages.success(request, f"Round '{r.name}' added.")
            return redirect("tournament_overview", slug=t.slug)
    else:
        next_seq = (t.rounds.count() or 0) + 1
        form = RoundForm(initial={"seq": next_seq, "name": f"Round {next_seq}"})
    return render(request, "tournaments/round_create.html", {"form": form, "tournament": t})


@login_required
def round_edit(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    if request.method == "POST":
        form = RoundForm(request.POST, instance=r)
        if form.is_valid():
            form.save()
            messages.success(request, "Round updated.")
            return redirect("tournament_overview", slug=t.slug)
    else:
        form = RoundForm(instance=r)
    return render(request, "tournaments/round_edit.html", {"form": form, "tournament": t, "round": r})


@login_required
def round_delete(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    if request.method == "POST":
        r.delete()
        messages.success(request, f"Round '{r.name}' deleted.")
        return redirect("tournament_overview", slug=t.slug)
    return render(request, "tournaments/round_delete_confirm.html", {"tournament": t, "round": r})


def public_overview(request, slug):
    """Public-facing tournament page — no login required."""
    t = get_object_or_404(Tournament, slug=slug, active=True)
    released_rounds = t.rounds.filter(results_released=True).order_by("seq")
    return render(request, "public/overview.html", {"tournament": t, "rounds": released_rounds})
