from django.urls import path
from . import views

urlpatterns = [
    path('reports/', views.reports_home, name='reports_home'),
    path('reports/daily-transactions/', views.daily_transactions, name='report_daily_transactions'),
    path('reports/account-balances/', views.account_balances, name='report_account_balances'),
    path('reports/loan-status/', views.loan_status_report, name='report_loan_status'),
    path('reports/deposit-withdrawal-history/', views.deposit_withdrawal_history, name='report_deposit_withdrawal'),
    path('reports/account-list/', views.account_list_report, name='report_account_list'),
]