from django.urls import path
from . import views

urlpatterns = [
    path('backup/', views.backup_home, name='backup'),
    path('backup/create/', views.create_backup, name='create_backup'),
    path('backup/download/<str:filename>/', views.download_backup, name='download_backup'),
    path('backup/delete/<str:filename>/', views.delete_backup, name='delete_backup'),
]