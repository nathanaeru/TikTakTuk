from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("venue/", views.venue_list, name="venue_list"),
    path("event/", views.event_list, name="event_list"),
    path("my-event/", views.my_event_list, name="my_event_list"),
    path("admin-event/", views.admin_event_list, name="admin_event_list"),
]