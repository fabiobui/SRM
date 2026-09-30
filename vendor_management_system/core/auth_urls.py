# vendor_management_system/core/auth_urls.py

from django.urls import path

from vendor_management_system.core.auth_views import (
    CustomLoginView,
    CustomLogoutView,
    PortalInviteSetPasswordView,
    PortalPasswordResetDoneView,
    PortalPasswordResetView,
    PortalPasswordSetDoneView,
    PortalSetPasswordView,
)

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
    # Impostazione / reset password
    path(
        "password-dimenticata/",
        PortalPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password-dimenticata/inviata/",
        PortalPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "imposta-password/<uidb64>/<token>/",
        PortalInviteSetPasswordView.as_view(),
        name="portal_invite_confirm",
    ),
    path(
        "reset/<uidb64>/<token>/",
        PortalSetPasswordView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-impostata/",
        PortalPasswordSetDoneView.as_view(),
        name="password_reset_complete",
    ),
]
