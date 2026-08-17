from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegistrationForm, LoginForm


def _safe_next(request):
    """
    Resolve the ?next= redirect target, rejecting anything that points off-site.

    FIX #8: this used to be `redirect(request.GET.get("next", "tournament_list"))`
    with no validation, which is a textbook open redirect — a link such as
    /accounts/login/?next=https://evil.example would log a tab master in and
    then hand them straight to an attacker's copy of the site. Django ships a
    validator for exactly this; an unvalidated value is now never used.
    """
    candidate = request.POST.get('next') or request.GET.get('next')
    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host(), *settings.ALLOWED_HOSTS},
        require_https=request.is_secure(),
    ):
        return candidate
    return None


def register_view(request):
    if request.user.is_authenticated:
        return redirect("tournament_list")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f"Welcome, {user.first_name}! Your Tab Master account is ready.",
            )
            return redirect(_safe_next(request) or "tournament_list")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("tournament_list")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(_safe_next(request) or "tournament_list")
        messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")
