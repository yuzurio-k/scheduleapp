from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'schedule'

urlpatterns = [
    path('', RedirectView.as_view(url='projects/', permanent=True)),
    path('projects/', views.project_list, name='project_list'),
    path('projects/create/', views.project_create, name='project_create'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('projects/<int:pk>/complete/', views.project_complete_view, name='project_complete'),
    path('schedules/create/', views.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/', views.schedule_detail, name='schedule_detail'),
    path('schedules/<int:pk>/edit/', views.schedule_edit, name='schedule_edit'),
    path('schedules/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
    path('schedules/<int:schedule_id>/complete/', views.schedule_complete_view, name='schedule_complete'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('api/schedules/', views.schedule_api, name='schedule_api'),
    # 分野管理
    path('fields/', views.field_list_view, name='field_list'),
    path('fields/create/', views.field_create_view, name='field_create'),
    path('fields/<int:field_id>/delete/', views.field_delete_view, name='field_delete'),
]