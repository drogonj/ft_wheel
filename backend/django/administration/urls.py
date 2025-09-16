from django.urls import path, re_path
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns = [
    # Admin wheel management (superusers only)
    path('adm/wheels/', views.admin_wheels, name='admin_wheels'),
    path('adm/wheels/create/', views.create_wheel, name='create_wheel'),
    path('adm/wheels/<str:config>/delete/', views.delete_wheel, name='delete_wheel'),
    path('adm/wheels/<str:config>/download/', views.download_wheel, name='download_wheel'),
    path('adm/wheels/<str:config>/', views.edit_wheel, name='edit_wheel'),
]