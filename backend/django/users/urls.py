from django.urls import path, re_path
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('login/oauth/callback', views.callback_view, name='callback'),
    path('logout/', views.logout_view, name='logout'),
    path('consent/', views.consent_view, name='consent'),
    path('accept_consent/', views.accept_consent_view, name='accept_consent'),
]