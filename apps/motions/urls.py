from django.urls import path
from . import views
urlpatterns = [
    path("rounds/<int:round_seq>/motions/", views.motion_list, name="motion_list"),
    path("rounds/<int:round_seq>/motions/add/", views.motion_create, name="motion_create"),
    path("rounds/<int:round_seq>/motions/<int:pk>/release/", views.release_motion, name="release_motion"),
]
