from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    # Auth
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Core
    path('', views.dashboard, name='dashboard'),
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/create/', views.trip_create, name='trip_create'),
    path('trips/<int:pk>/', views.trip_detail, name='trip_detail'),
    path('trips/<int:pk>/delete/', views.trip_delete, name='trip_delete'),

    # Members
    path('trips/<int:pk>/members/add/', views.member_add, name='member_add'),
    path('trips/<int:pk>/members/<int:member_id>/remove/', views.member_remove, name='member_remove'),

    # Expenses
    path('trips/<int:pk>/expenses/add/', views.expense_add, name='expense_add'),
    path('trips/<int:pk>/expenses/export/', views.trip_expenses_export, name='trip_expenses_export'),
    path('trips/<int:pk>/report/pdf/', views.trip_report_pdf, name='trip_report_pdf'),
    path('trips/<int:pk>/expenses/<int:expense_id>/edit/', views.expense_edit, name='expense_edit'),
    path('trips/<int:pk>/expenses/<int:expense_id>/delete/', views.expense_delete, name='expense_delete'),

    # Settlements
    path('trips/<int:pk>/settlements/record/', views.settlement_record, name='settlement_record'),
]
