from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Interest, Event, Ticket, Payment, Notification, AdminLog


class CustomUserAdmin(BaseUserAdmin):
    # ── Columns shown in the User list page ──────────────────────────────────
    list_display = ('email', 'username', 'full_name', 'role', 'department', 'faculty', 'fcm_token', 'is_staff')
    list_filter  = ('role', 'is_staff', 'is_superuser', 'faculty')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'department', 'faculty', 'fcm_token')
    ordering = ('email',)

    def full_name(self, obj):
        return obj.get_full_name() or '—'
    full_name.short_description = 'Full Name'

    # ── Fieldsets shown on the User EDIT page ────────────────────────────────
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Campus Profile', {
            'fields': ('role', 'department', 'faculty', 'fcm_token'),
        }),
    )

    # ── Fieldsets shown on the Add User page ─────────────────────────────────
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Campus Profile', {
            'classes': ('wide',),
            'fields': ('email', 'role', 'department', 'faculty'),
        }),
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'event_type',
        'status', 'date_time', 'venue',
        'capacity', 'organiser'
    ]
    list_filter = ['category', 'event_type', 'status']
    search_fields = ['title', 'venue']
    ordering = ['-date_time']
    # category, event_type, and status automatically render as
    # dropdowns because the model fields have choices= defined.


admin.site.register(User, CustomUserAdmin)
admin.site.register(Interest)
admin.site.register(Ticket)
admin.site.register(Payment)
admin.site.register(Notification)
admin.site.register(AdminLog)
