from django.urls import path
from . import views
from . import models

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.login_view, name='login_view'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout_view'),
    path('trade/', views.trade_view, name='trade_view'),
    path('buy_order/<str:order_id>/', views.execute_buy_order, name='execute_buy_order'),
    path('sell_order/<str:order_id>/', views.execute_sell_order, name='execute_sell_order'),
    path('orders_view/', views.orders_view, name='orders_view'),
    path('profit_view/', views.profit_view, name='profit_view'),
]