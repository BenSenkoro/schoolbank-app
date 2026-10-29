from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_user, name='create_user'),
    path('users/<int:pk>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:pk>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('users/import/', views.bulk_import, name='bulk_import'),
    path('users/import/template/', views.download_template, name='download_template'),
    path('activity-log/', views.activity_log, name='activity_log'),
    path('profile/password/', views.change_password, name='change_password'),
]