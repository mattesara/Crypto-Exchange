from django.urls import path
from . import views
from . import models

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.login_view, name='login_view'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout_view'),
    path('trade/', views.trade_view, name='trade_view'),
    path('orders_view/', views.orders_view, name='orders_view'),
    path('profit_view/', views.profit_view, name='profit_view'),
]