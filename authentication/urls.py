from django.urls import path
from . import views

app_name = "auth"

urlpatterns = [
    path("choose-role/", views.choose_role_view, name="choose_role"),
    path("register/customer/", views.register_customer_view, name="register_customer"),
    path(
        "register/organizer/", views.register_organizer_view, name="register_organizer"
    ),
    path("register/admin/", views.register_admin_view, name="register_admin"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Legacy URLs (kept for backward compatibility, redirects to choose_role)
    path("register/", views.choose_role_view, name="register"),
    path(
        "select-role/", views.logout_view, name="select_role"
    ),  # Deprecated, kept for safety
]
