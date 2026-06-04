from django.urls import path
from . import views

urlpatterns = [
    path("tab/teams/", views.team_tab, name="team_tab"),
    path("tab/speakers/", views.speaker_tab, name="speaker_tab"),
    path("public/tab/teams/", views.public_team_tab, name="public_team_tab"),
    path("public/tab/speakers/", views.public_speaker_tab, name="public_speaker_tab"),
]
