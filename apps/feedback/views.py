from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.tournaments.models import Tournament
from apps.draw.models import Debate, DebateAdjudicator
from apps.participants.models import Speaker, Adjudicator
from .models import AdjudicatorFeedback


@require_POST
def submit_feedback(request, slug, debate_id):
    """Any participant can submit feedback via POST."""
    t = get_object_or_404(Tournament, slug=slug)
    debate = get_object_or_404(Debate, pk=debate_id, round__tournament=t)

    adj_id = request.POST.get("adjudicator")
    score_raw = request.POST.get("score", "").strip()
    comments = request.POST.get("comments", "").strip()
    source_speaker_id = request.POST.get("source_speaker")
    source_adj_id = request.POST.get("source_adjudicator")

    try:
        adj = Adjudicator.objects.get(pk=int(adj_id), tournament=t)
        score = float(score_raw)
    except (Adjudicator.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid feedback submission.")
        return redirect("public_overview", slug=t.slug)

    fb = AdjudicatorFeedback(debate=debate, adjudicator=adj, score=score, comments=comments)
    if source_speaker_id:
        try:
            fb.source_speaker = Speaker.objects.get(pk=int(source_speaker_id), tournament=t)
        except (Speaker.DoesNotExist, ValueError):
            pass
    if source_adj_id:
        try:
            fb.source_adjudicator = Adjudicator.objects.get(pk=int(source_adj_id), tournament=t)
        except (Adjudicator.DoesNotExist, ValueError):
            pass
    fb.save()
    messages.success(request, "Feedback submitted. Thank you.")
    return redirect("public_overview", slug=t.slug)


def feedback_overview(request, slug):
    """Tab master view: all feedback received."""
    from django.contrib.auth.decorators import login_required
    from functools import wraps
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    feedback = AdjudicatorFeedback.objects.filter(
        adjudicator__tournament=t
    ).select_related("adjudicator", "source_speaker", "source_adjudicator", "debate__round").order_by("-submitted_at")
    return render(request, "feedback/overview.html", {"tournament": t, "feedback": feedback})
