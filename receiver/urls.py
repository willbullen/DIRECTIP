from django.urls import path
from . import views

app_name = 'receiver'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/packets/', views.get_packets, name='get_packets'),
    path('api/stats/', views.get_stats, name='get_stats'),
]
