from django.urls import path
from . import views

urlpatterns = [
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('deposit/', views.deposit, name='deposit'),
    path('withdrawal/', views.withdrawal, name='withdrawal'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/<int:pk>/edit/', views.edit_transaction, name='edit_transaction'),
    path('transactions/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    path('transfer/', views.transfer, name='transfer'),
    path('accounts/<int:pk>/statement/', views.account_statement, name='account_statement'),
    path('transactions/<int:pk>/receipt/', views.transaction_receipt, name='transaction_receipt'),
]