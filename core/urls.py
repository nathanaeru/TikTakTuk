from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path(
        "dashboard/<uuid:user_id>/seat/", views.seat_management, name="seat_management"
    ),
    path(
        "dashboard/<uuid:user_id>/seat/create/", views.create_seat, name="create_seat"
    ),
    path(
        "dashboard/<uuid:user_id>/seat/update/<uuid:seat_id>/",
        views.update_seat,
        name="update_seat",
    ),
    path(
        "dashboard/<uuid:user_id>/seat/delete/<uuid:seat_id>/",
        views.delete_seat,
        name="delete_seat",
    ),
    path("dashboard/<uuid:user_id>/ticket/", views.ticket_list, name="ticket_list"),
    path(
        "dashboard/<uuid:user_id>/ticket/create/",
        views.create_ticket,
        name="create_ticket",
    ),
    path(
        "dashboard/<uuid:user_id>/ticket/update/<str:ticket_id>/",
        views.update_ticket,
        name="update_ticket",
    ),
    path(
        "dashboard/<uuid:user_id>/ticket/delete/<str:ticket_id>/",
        views.delete_ticket,
        name="delete_ticket",
    ),
    path("dashboard/", views.dashboard_pengguna, name="dashboard_guest"),
    path("dashboard/<uuid:user_id>/", views.dashboard_pengguna, name="dashboard_user"),
    path(
        "dashboard/<uuid:user_id>/<str:page>/",
        views.dashboard_pengguna,
        name="dashboard_page",
    ),
    path("seat/", views.seat_management, name="seat_management"),
    path("ticket/", views.ticket_list, name="ticket_list_no_id"),
    path("venue/", views.venue_list, name="venue_list"),
    path("event/", views.event_list, name="event_list"),
    path("my-event/", views.my_event_list, name="my_event_list"),
    path("admin-event/", views.admin_event_list, name="admin_event_list"),
    path("", views.home_view, name="home"),
    # Manajemen Seat
    path("seats/", views.seat_management, name="seat_management_public"),
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
    path(
        "kategori-tiket/",
        RedirectView.as_view(pattern_name="ticket_category_list", permanent=False),
        name="kategori_tiket",
    ),
    # Artist management (create/update/delete)
    path("artist/create/", views.create_artist, name="create_artist"),
    path("artist/update/<uuid:artist_id>/", views.update_artist, name="update_artist"),
    path("artist/delete/<uuid:artist_id>/", views.delete_artist, name="delete_artist"),
    # Backwards-compatible reverse names (aliases)
    path(
        "manajemen-artis/",
        RedirectView.as_view(pattern_name="artist_list", permanent=False),
        name="manajemen_artis",
    ),
    # Ticket category management (create/update/delete)
    path(
        "ticket-category/create/",
        views.create_ticket_category,
        name="create_ticket_category",
    ),
    path(
        "ticket-category/update/<uuid:category_id>/",
        views.update_ticket_category,
        name="update_ticket_category",
    ),
    path(
        "ticket-category/delete/<uuid:category_id>/",
        views.delete_ticket_category,
        name="delete_ticket_category",
    ),
    # ORDER
    path("order/checkout/", views.checkout_view, name="checkout"),
    path("order/", views.daftar_order_view, name="daftar_order"),
    path(
        "order/update/<str:order_id>/", views.update_order_status, name="update_order"
    ),
    path("order/delete/<str:order_id>/", views.delete_order, name="delete_order"),
    # PROMOTION
    path("promotion/", views.promotion_list_view, name="promotion_list"),
    path("promotion/create/", views.create_promotion, name="create_promotion"),
    path(
        "promotion/update/<uuid:promo_id>/",
        views.update_promotion,
        name="update_promotion",
    ),
    path(
        "promotion/delete/<uuid:promo_id>/",
        views.delete_promotion,
        name="delete_promotion",
    ),
]
