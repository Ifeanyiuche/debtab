from django.urls import path
from . import views

urlpatterns = [
    path("", views.tournament_list, name="tournament_list"),
    path("create/", views.tournament_create, name="tournament_create"),
]

tournament_urls = [
    path("", views.tournament_overview, name="tournament_overview"),
    path("edit/", views.tournament_edit, name="tournament_edit"),
    path("rounds/create/", views.round_create, name="round_create"),
    path("rounds/<int:round_seq>/edit/", views.round_edit, name="round_edit"),
    path("rounds/<int:round_seq>/rename/", views.round_rename, name="round_rename"),
    path("rounds/<int:round_seq>/delete/", views.round_delete, name="round_delete"),
    path("rounds/<int:round_seq>/toggle-tab-visibility/", views.toggle_round_tab_visibility, name="toggle_round_tab_visibility"),
    path("release-tab/", views.release_full_tab, name="release_full_tab"),
    path("hide-tab/", views.hide_full_tab, name="hide_full_tab"),
    path("public/", views.public_overview, name="public_overview"),
    path("breaks/", views.break_setup, name="break_setup"),
]
