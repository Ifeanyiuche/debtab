from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tournaments.models import Tournament
from .models import Institution, Speaker, Team, Adjudicator


@login_required
def participant_manage(request, slug, pk):
    """
    Full management view for a single participant.
    Can change role, assign institution, assign/move teams, edit all details.
    """
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    institutions = t.institutions.all()
    teams = t.teams.filter(active=True).order_by("name")

    # Find which model this pk belongs to
    speaker = Speaker.objects.filter(pk=pk, tournament=t).first()
    adjudicator = Adjudicator.objects.filter(pk=pk, tournament=t).first()
    obj = speaker or adjudicator
    if not obj:
        messages.error(request, "Participant not found.")
        return redirect("participant_list", slug=t.slug)

    current_role = "speaker" if speaker else "adjudicator"

    if request.method == "POST":
        new_role = request.POST.get("role", current_role)
        name = request.POST.get("name", "").strip()
        inst_id = request.POST.get("institution", "")
        email = request.POST.get("email", "").strip()

        institution = None
        if inst_id:
            try:
                institution = Institution.objects.get(pk=int(inst_id), tournament=t)
            except (Institution.DoesNotExist, ValueError):
                pass

        if new_role != current_role:
            # Role change: delete old, create new
            obj.delete()
            if new_role == "adjudicator":
                base_score = float(request.POST.get("base_score", 1.5) or 1.5)
                Adjudicator.objects.create(
                    tournament=t, name=name, institution=institution,
                    email=email, base_score=base_score,
                )
                messages.success(request, f"{name} changed to Adjudicator.")
            else:
                spk = Speaker.objects.create(
                    tournament=t, name=name, institution=institution, email=email,
                    is_esl=bool(request.POST.get("is_esl")),
                    is_efl=bool(request.POST.get("is_efl")),
                    is_novice=bool(request.POST.get("is_novice")),
                    is_schools=bool(request.POST.get("is_schools")),
                )
                _assign_team(request, spk, t)
                messages.success(request, f"{name} changed to Speaker.")
            return redirect("participant_list", slug=t.slug)

        # Same role — update in place
        obj.name = name
        obj.institution = institution
        obj.email = email

        if current_role == "speaker":
            obj.is_esl = bool(request.POST.get("is_esl"))
            obj.is_efl = bool(request.POST.get("is_efl"))
            obj.is_novice = bool(request.POST.get("is_novice"))
            obj.is_schools = bool(request.POST.get("is_schools"))
            obj.save()
            _assign_team(request, obj, t)
        else:
            obj.base_score = float(request.POST.get("base_score", obj.base_score) or obj.base_score)
            obj.independent = bool(request.POST.get("independent"))
            obj.save()

        messages.success(request, f"{name} updated.")
        return redirect("participant_list", slug=t.slug)

    current_teams = obj.teams.all() if current_role == "speaker" else []

    return render(request, "participants/manage.html", {
        "tournament": t,
        "obj": obj,
        "current_role": current_role,
        "institutions": institutions,
        "teams": teams,
        "current_teams": current_teams,
    })


def _assign_team(request, speaker, tournament):
    """Handle team assignment from the manage form."""
    action = request.POST.get("team_action", "keep")
    team_id = request.POST.get("assign_team_id", "")
    new_team_name = request.POST.get("new_team_name", "").strip()

    if action == "remove_all":
        for team in speaker.teams.all():
            team.speakers.remove(speaker)

    elif action == "assign" and team_id:
        try:
            team = Team.objects.get(pk=int(team_id), tournament=tournament)
            team.speakers.add(speaker)
        except (Team.DoesNotExist, ValueError):
            pass

    elif action == "move" and team_id:
        # Remove from all current teams, add to new one
        for team in speaker.teams.all():
            team.speakers.remove(speaker)
        try:
            team = Team.objects.get(pk=int(team_id), tournament=tournament)
            team.speakers.add(speaker)
        except (Team.DoesNotExist, ValueError):
            pass

    elif action == "create_team" and new_team_name:
        team = Team.objects.create(tournament=tournament, name=new_team_name)
        team.speakers.add(speaker)
