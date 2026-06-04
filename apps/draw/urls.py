from django.urls import path
from . import views

urlpatterns = [
    path("rounds/<int:round_seq>/draw/", views.draw_view, name="draw_view"),
    path("rounds/<int:round_seq>/draw/generate/", views.generate_draw, name="generate_draw"),
    path("rounds/<int:round_seq>/draw/auto-allocate/", views.auto_allocate, name="auto_allocate"),
    path("rounds/<int:round_seq>/draw/confirm/", views.confirm_draw, name="confirm_draw"),
    path("rounds/<int:round_seq>/draw/release/", views.release_draw, name="release_draw"),
    path("rounds/<int:round_seq>/draw/unrelease/", views.unrelease_draw, name="unrelease_draw"),
    path("rounds/<int:round_seq>/draw/<int:debate_id>/edit/", views.edit_debate, name="edit_debate"),
    path("rounds/<int:round_seq>/public-draw/", views.public_draw, name="public_draw"),
]
