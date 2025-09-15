from django.contrib import admin

from .models import History

# Register your models here.
class HistoryAdmin(admin.ModelAdmin):
    # All read-only
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_view_permission(self, request, obj=None):
        return True

    list_display = ('id', 'timestamp', 'wheel','details', 'user')
    ordering = ('-timestamp',)
    list_filter = ('wheel', 'details', 'user')

    readonly_fields = ('id', 'timestamp', 'wheel', 'details', 'user')
    list_per_page = 20

admin.site.register(History, HistoryAdmin)