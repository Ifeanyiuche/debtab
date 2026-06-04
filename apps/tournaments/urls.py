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
    path("rounds/<int:round_seq>/delete/", views.round_delete, name="round_delete"),
    path("public/", views.public_overview, name="public_overview"),
]
