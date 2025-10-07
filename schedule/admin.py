from django.contrib import admin
from .models import Project, Schedule

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'manufacturing_number', 'created_by', 'assigned_to', 'created_at']
    list_filter = ['created_at', 'created_by', 'assigned_to']
    search_fields = ['name', 'manufacturing_number', 'created_by__username', 'assigned_to__username']

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['project', 'field', 'start_date', 'end_date', 'duration_days']
    list_filter = ['field', 'start_date', 'end_date']
    search_fields = ['project__name', 'project__manufacturing_number']
