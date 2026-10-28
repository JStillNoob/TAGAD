from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('organization_name', 'organization_code', 'status', 'archived_at', 'created_at')
    list_filter = ('status', 'archived_at')
    search_fields = ('organization_name', 'organization_code')
    readonly_fields = ('archived_at', 'archived_by')

    def save_model(self, request, obj, form, change):
        if obj.status == Organization.Status.INACTIVE and obj.archived_at is None:
            obj.archived_at = timezone.now()
            obj.archived_by = request.user
        elif obj.status == Organization.Status.ACTIVE:
            obj.archived_at = None
            obj.archived_by = None
        super().save_model(request, obj, form, change)


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

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=User.Role.ORG_ADMIN)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'role':
            kwargs['choices'] = [(User.Role.ORG_ADMIN, User.Role.ORG_ADMIN.label)]
        return super().formfield_for_choice_field(db_field, request, **kwargs)
