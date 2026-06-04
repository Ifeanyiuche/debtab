from django.urls import path
from . import views
urlpatterns = [
    path("venues/", views.venue_list, name="venue_list"),
    path("venues/add/", views.venue_create, name="venue_create"),
    path("venues/<int:pk>/delete/", views.venue_delete, name="venue_delete"),
]
