from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Interest, Event, Ticket, Payment, Notification, AdminLog

admin.site.register(User, UserAdmin)
admin.site.register(Interest)
admin.site.register(Event)
admin.site.register(Ticket)
admin.site.register(Payment)
admin.site.register(Notification)
admin.site.register(AdminLog)
