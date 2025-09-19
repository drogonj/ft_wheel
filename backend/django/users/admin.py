from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()

class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'login',
        'has_consent',
        'is_superuser',
        'is_staff',
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


admin.site.register(User, AccountAdmin)