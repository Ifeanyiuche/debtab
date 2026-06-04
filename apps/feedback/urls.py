from django.urls import path
from . import views

urlpatterns = [
    path("feedback/", views.feedback_overview, name="feedback_overview"),
    path("debates/<int:debate_id>/feedback/", views.submit_feedback, name="submit_feedback"),
]
