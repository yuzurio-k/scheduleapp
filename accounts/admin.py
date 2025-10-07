from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'department', 'is_manager', 'is_staff', 'is_active']
    list_filter = ['is_manager', 'is_staff', 'is_active', 'department']
    search_fields = ['username', 'email', 'department']
    
    fieldsets = UserAdmin.fieldsets + (
        ('追加情報', {
            'fields': ('department', 'phone', 'is_manager'),
        }),
    )
