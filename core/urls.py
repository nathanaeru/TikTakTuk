from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/<uuid:user_id>/seat/', views.seat_management, name='seat_management'),
    path('dashboard/<uuid:user_id>/seat/create/', views.create_seat, name='create_seat'),
    path('dashboard/<uuid:user_id>/seat/update/<uuid:seat_id>/', views.update_seat, name='update_seat'),
    path('dashboard/<uuid:user_id>/seat/delete/<uuid:seat_id>/', views.delete_seat, name='delete_seat'),
    path('dashboard/<uuid:user_id>/ticket/', views.ticket_list, name='ticket_list'),
    path('dashboard/<uuid:user_id>/ticket/create/', views.create_ticket, name='create_ticket'),
    path('dashboard/<uuid:user_id>/ticket/update/<str:ticket_id>/', views.update_ticket, name='update_ticket'),
    path('dashboard/<uuid:user_id>/ticket/delete/<str:ticket_id>/', views.delete_ticket, name='delete_ticket'),
    path('dashboard/', views.dashboard_pengguna, name='dashboard_guest'),
    path('dashboard/<uuid:user_id>/', views.dashboard_pengguna, name='dashboard_user'),
    path('dashboard/<uuid:user_id>/<str:page>/', views.dashboard_pengguna, name='dashboard_page'),
    path('ticket/', views.ticket_list, name='ticket_list_no_id'),
    path('venue/', views.venue_list, name='venue_list'),
    path('event/', views.event_list, name='event_list'),
    path('my-event/', views.my_event_list, name='my_event_list'),
    path('admin-event/', views.admin_event_list, name='admin_event_list'),
]
    path("", views.home_view, name="home"),
    # Manajemen Seat
    path("dashboard/seat/", views.seat_management, name="seat_management"),
    path("dashboard/seat/create/", views.create_seat, name="create_seat"),
    path(
        "dashboard/seat/update/<uuid:seat_id>/", views.update_seat, name="update_seat"
    ),
    path(
        "dashboard/seat/delete/<uuid:seat_id>/", views.delete_seat, name="delete_seat"
    ),
    # Manajemen Tiket
    path("dashboard/ticket/", views.ticket_list, name="ticket_list"),
    path("dashboard/ticket/create/", views.create_ticket, name="create_ticket"),
    path(
        "dashboard/ticket/update/<str:ticket_id>/",
        views.update_ticket,
        name="update_ticket",
    ),
    path(
        "dashboard/ticket/delete/<str:ticket_id>/",
        views.delete_ticket,
        name="delete_ticket",
    ),
    # Dashboard Utama & Halaman Lainnya (Letakkan di bawah agar tidak konflik)
    path("dashboard/", views.dashboard_pengguna, name="dashboard"),
    path("dashboard/<str:page>/", views.dashboard_pengguna, name="dashboard_page"),
    # URL Publik
    path("ticket/", views.ticket_list, name="ticket_list_no_id"),
    path("artists/", views.artist_list_view, name="artist_list"),
    path(
        "ticket-categories/",
        views.ticket_category_list_view,
        name="ticket_category_list",
    ),
]
