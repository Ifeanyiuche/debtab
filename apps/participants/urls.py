from django.urls import path
from . import views

urlpatterns = [
    path("participants/institutions/", views.institution_list, name="institution_list"),
    path("participants/institutions/add/", views.institution_create, name="institution_create"),
    path("participants/institutions/<int:pk>/edit/", views.institution_edit, name="institution_edit"),
    path("participants/institutions/<int:pk>/delete/", views.institution_delete, name="institution_delete"),

    path("participants/speakers/", views.speaker_list, name="speaker_list"),
    path("participants/speakers/add/", views.speaker_create, name="speaker_create"),
    path("participants/speakers/<int:pk>/edit/", views.speaker_edit, name="speaker_edit"),
    path("participants/speakers/<int:pk>/delete/", views.speaker_delete, name="speaker_delete"),

    path("participants/teams/", views.team_list, name="team_list"),
    path("participants/teams/add/", views.team_create, name="team_create"),
    path("participants/teams/<int:pk>/edit/", views.team_edit, name="team_edit"),
    path("participants/teams/<int:pk>/delete/", views.team_delete, name="team_delete"),

    path("participants/adjudicators/", views.adjudicator_list, name="adjudicator_list"),
    path("participants/adjudicators/add/", views.adjudicator_create, name="adjudicator_create"),
    path("participants/adjudicators/<int:pk>/edit/", views.adjudicator_edit, name="adjudicator_edit"),
    path("participants/adjudicators/<int:pk>/delete/", views.adjudicator_delete, name="adjudicator_delete"),

    path("participants/check-in/", views.check_in, name="check_in"),
]
