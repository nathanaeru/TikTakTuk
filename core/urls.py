from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_pengguna, name='dashboard_guest'),
    path('dashboard/<uuid:user_id>/', views.dashboard_pengguna, name='dashboard_user'),
    path('dashboard/<uuid:user_id>/<str:page>/', views.dashboard_pengguna, name='dashboard_page'),
]