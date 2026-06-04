from django.urls import path
from . import views

urlpatterns = [
    path("rounds/<int:round_seq>/results/", views.results_overview, name="results_overview"),
    path("rounds/<int:round_seq>/results/<int:debate_id>/ballot/", views.ballot_entry, name="ballot_entry"),
    path("rounds/<int:round_seq>/results/release/", views.release_results, name="release_results"),
    path("rounds/<int:round_seq>/results/unrelease/", views.unrelease_results, name="unrelease_results"),
    path("rounds/<int:round_seq>/public-results/", views.public_results, name="public_results"),
]
