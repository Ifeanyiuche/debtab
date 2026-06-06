from django.urls import path
from . import views

urlpatterns = [
    path("feedback/", views.feedback_overview, name="feedback_overview"),
    path("feedback/debates/<int:debate_id>/", views.feedback_form, name="feedback_form"),
    path("feedback/<int:feedback_id>/toggle-ignore/", views.toggle_ignore_feedback, name="toggle_ignore_feedback"),
    path("debates/<int:debate_id>/feedback/", views.submit_feedback, name="submit_feedback"),
]
