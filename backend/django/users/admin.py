from django.contrib import admin
from django.contrib.auth import get_user_model
from wheel.models import Ticket

User = get_user_model()

class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'login',
        'has_consent',
        'role',
        'test_mode',
        'last_spin',
        'date_joined',
        'last_login'
        )

    
    search_fields = ('login',)
    ordering = ('id',)
    readonly_fields = ('date_joined', 'last_login', 'login', 'id')
    exclude = ('password',)
    list_per_page = 20

class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'wheel_slug',
        'created_at',
        'used_at',
        'granted_by'
    )
    search_fields = ('user__login', 'wheel_slug', 'granted_by__login')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'used_at', 'user', 'wheel_slug', 'granted_by')
    list_per_page = 20

admin.site.register(User, AccountAdmin)
admin.site.register(Ticket, TicketAdmin)