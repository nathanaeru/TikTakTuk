from django.urls import path
from . import views

app_name = "auth"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("select-role/", views.select_role_view, name="select_role"),
    path("logout/", views.logout_view, name="logout"),
]
