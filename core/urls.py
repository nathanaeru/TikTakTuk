from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_pengguna, name='dashboard_guest'),
    path('dashboard/<uuid:user_id>/', views.dashboard_pengguna, name='dashboard_user'),
    path('dashboard/<uuid:user_id>/<str:page>/', views.dashboard_pengguna, name='dashboard_page'),
    path('ticket/<uuid:user_id>/', views.ticket_list, name='ticket_list'),
    path('ticket/', views.ticket_list, name='ticket_list'),
    path('ticket/<uuid:user_id>/create/', views.create_ticket, name='create_ticket'),
    path('ticket/create/', views.create_ticket, name='create_ticket_no_id'), 
    path('ticket/update/<str:ticket_id>/', views.update_ticket, name='update_ticket'),
    path('ticket/delete/<str:ticket_id>/', views.delete_ticket, name='delete_ticket'),
]