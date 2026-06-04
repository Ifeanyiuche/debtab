from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tournaments.models import Tournament
from .models import Venue


@login_required
def venue_list(request, slug):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    venues = t.venues.all()
    return render(request, "venues/list.html", {"tournament": t, "venues": venues})


@login_required
def venue_create(request, slug):
    from django import forms as dforms
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        priority = int(request.POST.get("priority", 10))
        if name:
            Venue.objects.create(tournament=t, name=name, priority=priority)
            messages.success(request, f"Venue '{name}' added.")
        return redirect("venue_list", slug=t.slug)
    return render(request, "venues/form.html", {"tournament": t, "action": "Add"})


@login_required
def venue_delete(request, slug, pk):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    venue = get_object_or_404(Venue, pk=pk, tournament=t)
    if request.method == "POST":
        venue.delete()
        messages.success(request, "Venue deleted.")
        return redirect("venue_list", slug=t.slug)
    return render(request, "venues/confirm_delete.html", {"tournament": t, "venue": venue})
