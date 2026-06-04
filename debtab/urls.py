from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.tournaments.views import home
from apps.tournaments.urls import tournament_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("accounts/", include("apps.accounts.urls")),
    path("tournaments/", include("apps.tournaments.urls")),
    path("t/<slug:slug>/", include(tournament_urls)),
    path("t/<slug:slug>/", include("apps.participants.urls")),
    path("t/<slug:slug>/", include("apps.venues.urls")),
    path("t/<slug:slug>/", include("apps.motions.urls")),
    path("t/<slug:slug>/", include("apps.draw.urls")),
    path("t/<slug:slug>/", include("apps.results.urls")),
    path("t/<slug:slug>/", include("apps.standings.urls")),
    path("t/<slug:slug>/", include("apps.feedback.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
