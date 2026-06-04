import csv, io
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.tournaments.models import Tournament
from .models import Institution, Speaker, Team, Adjudicator


@login_required
def batch_upload(request, slug):
    """
    Step 1: Choose upload method (paste or CSV file).
    Step 2: Preview parsed rows in an editable table.
    Step 3: Confirm to create all participants.
    """
    t = get_object_or_404(Tournament, slug=slug, tab_master=request.user)
    institutions = t.institutions.all()
    teams = t.teams.filter(active=True).order_by("name")

    if request.method == "POST":
        action = request.POST.get("action", "parse")

        if action == "parse":
            rows = _parse_input(request, t)
            if rows is None:
                messages.error(request, "Could not parse the input. Check the format and try again.")
                return render(request, "participants/batch_upload.html", {
                    "tournament": t, "institutions": institutions, "teams": teams,
                })
            request.session[f"batch_{t.slug}"] = rows
            return render(request, "participants/batch_preview.html", {
                "tournament": t, "rows": rows,
                "institutions": institutions, "teams": teams,
            })

        elif action == "confirm":
            rows = request.session.pop(f"batch_{t.slug}", [])
            created_speakers = 0
            created_adjs = 0
            for i, _ in enumerate(rows):
                name = request.POST.get(f"name_{i}", "").strip()
                if not name:
                    continue
                role = request.POST.get(f"role_{i}", "speaker")
                inst_id = request.POST.get(f"institution_{i}")
                email = request.POST.get(f"email_{i}", "").strip()
                institution = None
                if inst_id:
                    try:
                        institution = Institution.objects.get(pk=int(inst_id), tournament=t)
                    except (Institution.DoesNotExist, ValueError):
                        pass

                if role == "adjudicator":
                    base_score = float(request.POST.get(f"base_score_{i}", 1.5) or 1.5)
                    Adjudicator.objects.create(
                        tournament=t, name=name, institution=institution,
                        email=email, base_score=base_score,
                    )
                    created_adjs += 1
                else:
                    is_esl = bool(request.POST.get(f"is_esl_{i}"))
                    is_efl = bool(request.POST.get(f"is_efl_{i}"))
                    is_novice = bool(request.POST.get(f"is_novice_{i}"))
                    is_schools = bool(request.POST.get(f"is_schools_{i}"))
                    spk = Speaker.objects.create(
                        tournament=t, name=name, institution=institution,
                        email=email, is_esl=is_esl, is_efl=is_efl,
                        is_novice=is_novice, is_schools=is_schools,
                    )
                    # Assign to team if specified
                    team_id = request.POST.get(f"team_{i}")
                    if team_id:
                        try:
                            team = Team.objects.get(pk=int(team_id), tournament=t)
                            team.speakers.add(spk)
                        except (Team.DoesNotExist, ValueError):
                            pass
                    created_speakers += 1

            parts = []
            if created_speakers:
                parts.append(f"{created_speakers} speaker{'s' if created_speakers != 1 else ''}")
            if created_adjs:
                parts.append(f"{created_adjs} adjudicator{'s' if created_adjs != 1 else ''}")
            messages.success(request, f"Registered {' and '.join(parts)}.")
            return redirect("participant_list", slug=t.slug)

    return render(request, "participants/batch_upload.html", {
        "tournament": t, "institutions": institutions, "teams": teams,
    })


def _parse_input(request, tournament):
    """Parse either a CSV file or pasted text into a list of row dicts."""
    rows = []

    # CSV file upload
    csv_file = request.FILES.get("csv_file")
    if csv_file:
        try:
            text = csv_file.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            for r in reader:
                rows.append(_normalise_row(r, tournament))
        except Exception:
            return None
        return rows

    # Pasted text: one person per line
    # Formats accepted:
    #   Name
    #   Name, Institution
    #   Name, Institution, Email
    #   Name, Institution, Email, Role
    #   Name, Institution, Email, Role, Categories (ESL/EFL/Novice/Schools)
    paste = request.POST.get("paste_text", "").strip()
    if paste:
        for line in paste.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            row = {
                "name": parts[0] if len(parts) > 0 else "",
                "institution": parts[1] if len(parts) > 1 else "",
                "email": parts[2] if len(parts) > 2 else "",
                "role": parts[3].lower() if len(parts) > 3 else "speaker",
                "categories": parts[4].upper() if len(parts) > 4 else "",
            }
            rows.append(_normalise_row(row, tournament))
        return rows

    return None


def _normalise_row(row, tournament):
    """Normalise a raw parsed row into a standard dict."""
    name = (row.get("name") or row.get("Name") or "").strip()
    role_raw = (row.get("role") or row.get("Role") or "speaker").strip().lower()
    role = "adjudicator" if "adj" in role_raw or "judge" in role_raw else "speaker"
    inst_name = (row.get("institution") or row.get("Institution") or "").strip()
    categories = (row.get("categories") or row.get("Categories") or "").upper()

    # Try to match institution by name
    institution = None
    if inst_name:
        institution = tournament.institutions.filter(name__icontains=inst_name).first()
        if not institution:
            institution = tournament.institutions.filter(code__iexact=inst_name).first()

    return {
        "name": name,
        "role": role,
        "institution": institution,
        "institution_raw": inst_name,
        "email": (row.get("email") or row.get("Email") or "").strip(),
        "is_esl": "ESL" in categories,
        "is_efl": "EFL" in categories,
        "is_novice": "NOVICE" in categories,
        "is_schools": "SCHOOLS" in categories,
        "base_score": row.get("base_score") or row.get("Score") or "1.5",
    }
