from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from apps.tournaments.views import home
from apps.tournaments.urls import tournament_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("accounts/", include("apps.accounts.urls")),
    path("accounts/password-reset/",
         auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html"),
         name="password_reset"),
    path("accounts/password-reset/done/",
         auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
         name="password_reset_done"),
    path("accounts/reset/<uidb64>/<token>/",
         auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html"),
         name="password_reset_confirm"),
    path("accounts/reset/done/",
         auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
         name="password_reset_complete"),
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
