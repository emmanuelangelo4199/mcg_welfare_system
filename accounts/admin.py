from django.contrib import admin
from .models import UserProfile, Role, Module, RolePermission


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number', 'title', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email', 'phone_number')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_system_protected', 'is_active', 'user_count', 'updated_at')
    list_filter = ('is_system_protected', 'is_active')
    search_fields = ('code', 'name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'description', 'order', 'is_sensitive', 'created_at')
    list_filter = ('is_sensitive',)
    search_fields = ('code', 'name')
    ordering = ('order', 'name')


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'module', 'can_view', 'can_create', 'can_edit', 'can_delete', 'can_approve', 'updated_at')
    list_filter = ('role', 'module', 'can_view', 'can_approve')
    search_fields = ('role__name', 'module__name')