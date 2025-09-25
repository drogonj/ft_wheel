from django.urls import path, re_path
from django.conf.urls.static import static
from django.conf import settings
from . import views
from . import history_views
from . import control_panel_views

urlpatterns = [
    # Control panel (admin and moderator access)
    path('adm/control-panel/', control_panel_views.control_panel_view, name='control_panel'),
    path('adm/control-panel/maintenance/toggle/', control_panel_views.toggle_maintenance_api, name='toggle_maintenance_api'),
    path('adm/control-panel/jackpot-cooldown/', control_panel_views.update_jackpot_cooldown_api, name='update_jackpot_cooldown_api'),
    path('adm/control-panel/settings/', control_panel_views.site_settings_api, name='site_settings_api'),
    
    # Admin wheel management (superusers only)
    path('adm/wheels/', views.admin_wheels, name='admin_wheels'),
    path('adm/wheels/create/', views.create_wheel, name='create_wheel'),
    path('adm/wheels/upload/', views.upload_wheel, name='upload_wheel'),
    path('adm/wheels/<str:config>/delete/', views.delete_wheel, name='delete_wheel'),
    path('adm/wheels/<str:config>/download/', views.download_wheel, name='download_wheel'),
    path('adm/wheels/<str:config>/', views.edit_wheel, name='edit_wheel'),
    
    # Admin history management (admin and moderator access)
    path('adm/history/', history_views.history_admin_view, name='history_admin'),
    path('adm/history/<int:history_id>/details/', history_views.history_detail_api, name='history_detail_api'),
    path('adm/history/<int:history_id>/mark/', history_views.add_history_mark, name='add_history_mark'),
    path('adm/history/<int:history_id>/cancel/', history_views.cancel_history_entry, name='cancel_history_entry'),
]