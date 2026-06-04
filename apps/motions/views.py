from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.tournaments.models import Tournament, Round
from .models import Motion


@login_required
def motion_list(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    motions = r.motions.all()
    return render(request, "motions/list.html", {"tournament": t, "round": r, "motions": motions})


@login_required
def motion_create(request, slug, round_seq):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        reference = request.POST.get("reference", "").strip()
        info_slide = request.POST.get("info_slide", "").strip()
        if text:
            Motion.objects.create(tournament=t, round=r, text=text, reference=reference, info_slide=info_slide)
            messages.success(request, "Motion added.")
        return redirect("motion_list", slug=t.slug, round_seq=r.seq)
    return render(request, "motions/form.html", {"tournament": t, "round": r})


@login_required
@require_POST
def release_motion(request, slug, round_seq, pk):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    m = get_object_or_404(Motion, pk=pk, tournament=t)
    m.released = not m.released
    m.save()
    r = get_object_or_404(Round, tournament=t, seq=round_seq)
    r.motions_released = m.released
    r.save()
    messages.success(request, "Motion release status updated.")
    return redirect("motion_list", slug=t.slug, round_seq=round_seq)
