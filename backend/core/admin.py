from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'organization_code', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('organization_name', 'organization_code')


@admin.register(User)
class TagadUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('TAGAD', {
            'fields': ('organization', 'middle_name', 'contact_no', 'role', 'status'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('TAGAD', {
            'fields': ('email', 'first_name', 'last_name', 'organization', 'role', 'status'),
        }),
    )
    list_display = UserAdmin.list_display + ('role', 'organization', 'status')
    list_filter = UserAdmin.list_filter + ('role', 'status', 'organization')
