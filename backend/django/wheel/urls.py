from django.urls import path, re_path
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.wheel_view, name='wheel'),
    path('spin/', views.spin_view, name='spin'),
    path('time_to_spin/', views.time_to_spin_view, name='time_to_spin'),
    path('change_wheel_config/', views.change_wheel_config, name='change_wheel_config'),
    path('history/', views.history_view, name='history'),
    path('faq/', views.faq_view, name='faq'),
    path('api/patch-notes/', views.patch_notes_api, name='patch_notes_api'),
]