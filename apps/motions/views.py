from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.tournaments.models import Tournament, Round
from .models import Motion


@login_required
def motions_overview(request, slug):
    """Tournament-level motions management: all rounds listed with inline add."""
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    rounds = t.rounds.prefetch_related("motions").order_by("seq")

    if request.method == "POST":
        action = request.POST.get("action", "add")

        if action == "delete":
            m = get_object_or_404(Motion, pk=request.POST.get("motion_id"), tournament=t)
            round_seq = m.round.seq if m.round else None
            m.delete()
            messages.success(request, "Motion deleted.")
            return redirect("motions_overview", slug=t.slug)

        if action == "edit":
            m = get_object_or_404(Motion, pk=request.POST.get("motion_id"), tournament=t)
            m.text = request.POST.get("text", m.text).strip()
            m.reference = request.POST.get("reference", m.reference).strip()
            m.info_slide = request.POST.get("info_slide", m.info_slide).strip()
            m.save()
            messages.success(request, "Motion updated.")
            return redirect("motions_overview", slug=t.slug)

        # Default: add new motion
        round_seq = request.POST.get("round_seq", "").strip()
        text = request.POST.get("text", "").strip()
        reference = request.POST.get("reference", "").strip()
        info_slide = request.POST.get("info_slide", "").strip()
        if text and round_seq:
            r = get_object_or_404(Round, tournament=t, seq=int(round_seq))
            Motion.objects.create(tournament=t, round=r, text=text, reference=reference, info_slide=info_slide)
            messages.success(request, f"Motion added to {r.name}.")
        return redirect("motions_overview", slug=t.slug)

    return render(request, "motions/overview.html", {"tournament": t, "rounds": rounds})


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


@login_required
@require_POST
def motion_delete(request, slug, round_seq, pk):
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    m = get_object_or_404(Motion, pk=pk, tournament=t)
    m.delete()
    messages.success(request, "Motion deleted.")
    return redirect("motions_overview", slug=t.slug)
