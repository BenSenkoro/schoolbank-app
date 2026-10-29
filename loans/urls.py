from django.urls import path
from . import views

urlpatterns = [
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/create/', views.create_loan, name='create_loan'),
    path('loans/<int:pk>/', views.loan_detail, name='loan_detail'),
    path('loans/<int:pk>/status/', views.update_loan_status, name='update_loan_status'),
    path('loans/<int:pk>/delete/', views.delete_loan, name='delete_loan'),
]