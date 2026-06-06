from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tournaments.models import Tournament, Round
from apps.draw.models import Debate, DebateAdjudicator
from apps.participants.models import Speaker, Adjudicator
from .models import AdjudicatorFeedback


def feedback_form(request, slug, debate_id):
    """Public-facing feedback submission form (GET + POST)."""
    t = get_object_or_404(Tournament, slug=slug)
    debate = get_object_or_404(Debate, pk=debate_id, round__tournament=t)

    if debate.round.is_break_round:
        messages.error(request, "Feedback is closed — speaker feedback is only collected during preliminary rounds.")
        return redirect("public_overview", slug=t.slug)

    debate_adjs = debate.debate_adjudicators.select_related("adjudicator").all()
    debate_teams = debate.debate_teams.select_related("team").prefetch_related("team__speakers").all()

    if request.method == "POST":
        adj_id = request.POST.get("adjudicator")
        score_raw = request.POST.get("score", "").strip()
        comments = request.POST.get("comments", "").strip()
        source_type = request.POST.get("source_type", "speaker")
        source_id = request.POST.get("source_id", "").strip()

        try:
            adj = Adjudicator.objects.get(pk=int(adj_id), tournament=t)
            score = float(score_raw)
            assert 1 <= score <= 10
        except Exception:
            messages.error(request, "Invalid submission — check adjudicator and score (1–5).")
            return redirect("feedback_form", slug=t.slug, debate_id=debate.pk)

        fb = AdjudicatorFeedback(debate=debate, adjudicator=adj, score=score, comments=comments)
        if source_type == "speaker" and source_id:
            try:
                fb.source_speaker = Speaker.objects.get(pk=int(source_id), tournament=t)
            except (Speaker.DoesNotExist, ValueError):
                pass
        elif source_type == "adjudicator" and source_id:
            try:
                fb.source_adjudicator = Adjudicator.objects.get(pk=int(source_id), tournament=t)
            except (Adjudicator.DoesNotExist, ValueError):
                pass
        fb.save()
        messages.success(request, "Feedback submitted. Thank you!")
        return redirect("public_overview", slug=t.slug)

    all_speakers = [spk for dt in debate_teams for spk in dt.team.speakers.all()]
    context = {
        "tournament": t,
        "debate": debate,
        "debate_adjs": debate_adjs,
        "all_speakers": all_speakers,
        "all_adjs_in_debate": [da.adjudicator for da in debate_adjs],
    }
    return render(request, "feedback/form.html", context)


@login_required
def feedback_overview(request, slug):
    """Tab master view: all feedback received, with per-debate shareable links."""
    from collections import defaultdict
    from apps.draw.models import Debate
    from apps.tournaments.models import Round

    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)

    # Prelim-only: debates with at least one adjudicator assigned, grouped by round
    rounds_with_debates = []
    for r in t.rounds.filter(is_break_round=False).order_by("seq"):
        debates = list(
            r.debates
            .prefetch_related("debate_adjudicators__adjudicator", "debate_teams__team")
            .select_related("venue")
            .order_by("room_rank")
        )
        debates_with_adjs = [d for d in debates if d.debate_adjudicators.exists()]
        if debates_with_adjs:
            rounds_with_debates.append({"round": r, "debates": debates_with_adjs})

    # All prelim-round feedback (out-round feedback is for CAP panels, not public log)
    feedback = (
        AdjudicatorFeedback.objects
        .filter(adjudicator__tournament=t, debate__round__is_break_round=False)
        .select_related("adjudicator", "source_speaker", "source_adjudicator", "debate__round")
        .order_by("adjudicator__name", "-submitted_at")
    )

    # Group by adjudicator; avg uses only speaker-sourced, non-ignored feedback
    adj_data = defaultdict(lambda: {"feedback": [], "count": 0, "avg": 0})
    for fb in feedback:
        adj_data[fb.adjudicator.pk]["adj"] = fb.adjudicator
        adj_data[fb.adjudicator.pk]["feedback"].append(fb)
        adj_data[fb.adjudicator.pk]["count"] += 1

    for pk, data in adj_data.items():
        ranking_scores = [
            fb.score for fb in data["feedback"]
            if not fb.ignored and not fb.source_adjudicator_id
        ]
        data["avg"] = round(sum(ranking_scores) / len(ranking_scores), 2) if ranking_scores else 0

    adj_summary = sorted(adj_data.values(), key=lambda x: -x["avg"])

    return render(request, "feedback/overview.html", {
        "tournament": t,
        "feedback": feedback,
        "adj_summary": adj_summary,
        "rounds_with_debates": rounds_with_debates,
    })


@login_required
def toggle_ignore_feedback(request, slug, feedback_id):
    """Tab master toggles whether a feedback response is ignored in rankings."""
    from django.views.decorators.http import require_POST
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    fb = get_object_or_404(AdjudicatorFeedback, pk=feedback_id, adjudicator__tournament=t)
    fb.ignored = not fb.ignored
    fb.save(update_fields=["ignored"])
    status = "ignored" if fb.ignored else "included"
    messages.success(request, f"Feedback from '{fb.source_speaker or fb.source_adjudicator or 'Anonymous'}' is now {status} in rankings.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "feedback_overview"
    if next_url.startswith("/"):
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(next_url)
    return redirect("feedback_overview", slug=t.slug)


def submit_feedback(request, slug, debate_id):
    """Legacy POST-only endpoint — redirect to new form."""
    return redirect("feedback_form", slug=slug, debate_id=debate_id)
