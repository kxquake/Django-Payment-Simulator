from django.urls import path
from . import views, api

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('payments/new/', views.make_payment, name='make_payment'),
    path('requests/new/', views.request_payment, name='request_payment'),
    path('transactions/', views.transactions_list, name='transactions'),
    path('notifications/', views.notifications, name='notifications'),
    path('requests/<int:request_id>/respond/', views.respond_to_request, name='respond_to_request'),
    path('admins/users/', views.admin_all_users, name='admin_users'),
    path('admins/transactions/', views.admin_all_transactions, name='admin_transactions'),
    path('admins/register/', views.admin_register, name='admin_register'),

    path('conversion/<str:currency1>/<str:currency2>/<str:amount_of_currency1>/',
         api.conversion, name='conversion'),
]