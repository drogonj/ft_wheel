from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.db.models import Count, Q
from datetime import datetime, timedelta
import json
import logging

from users.models import Account
from wheel.models import History
from .models import SiteSettings

logger = logging.getLogger(__name__)

def user_can_access_control_panel(user):
    """Check if user can access control panel"""
    if not user.is_authenticated:
        return False
    return user.is_admin()

def user_can_modify_settings(user):
    """Check if user can modify site settings"""
    if not user.is_authenticated:
        return False
    return user.is_admin()

@login_required
def control_panel_view(request):
    """Main control panel dashboard"""
    if not user_can_access_control_panel(request.user):
        return HttpResponseForbidden("Access denied")
    
    # Get or create site settings
    settings, created = SiteSettings.objects.get_or_create(pk=1)
    if created:
        logger.info("Created initial SiteSettings instance")
    
    # Calculate statistics
    today = timezone.now().date()
    week_ago = timezone.now() - timedelta(days=7)
    
    try:
        stats = {
            'total_users': Account.objects.count(),
            'active_users_today': Account.objects.filter(
                last_login__date=today
            ).count() if Account.objects.filter(last_login__date=today).exists() else 0,
            'active_users_week': Account.objects.filter(
                last_login__gte=week_ago
            ).count() if Account.objects.filter(last_login__gte=week_ago).exists() else 0,
            'total_spins_today': History.objects.filter(
                timestamp__date=today
            ).count(),
            'total_spins_week': History.objects.filter(
                timestamp__gte=week_ago
            ).count(),
            'error_spins_today': History.objects.filter(
                timestamp__date=today,
                success=False
            ).count(),
            'jackpot_cooldown_hours': settings.jackpot_cooldown // 3600,
        }
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        stats = {
            'total_users': 0,
            'active_users_today': 0,
            'active_users_week': 0,
            'total_spins_today': 0,
            'total_spins_week': 0,
            'error_spins_today': 0,
            'jackpot_cooldown_hours': settings.jackpot_cooldown // 3600,
        }
    
    # Recent activity
    try:
        recent_users = Account.objects.filter(
            last_login__gte=week_ago
        ).order_by('-last_login')[:10] if Account.objects.filter(last_login__gte=week_ago).exists() else []
        
        recent_errors = History.objects.filter(
            success=False,
            timestamp__gte=week_ago
        ).order_by('-timestamp')[:5]
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        recent_users = []
        recent_errors = []
    
    context = {
        'settings': settings,
        'stats': stats,
        'recent_users': recent_users,
        'recent_errors': recent_errors,
        'can_modify': user_can_modify_settings(request.user),
    }
    
    return render(request, 'administration/control_panel.html', context)

@login_required
@csrf_exempt
@require_POST
def toggle_maintenance_api(request):
    """Toggle maintenance mode via API"""
    if not user_can_modify_settings(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        enabled = bool(data.get('enabled', False))
        message = data.get('message', '').strip()
        
        if not message:
            message = "The site is currently under maintenance. Please check back later."
        
        settings, created = SiteSettings.objects.get_or_create(pk=1)
        settings.maintenance_mode = enabled
        settings.maintenance_message = message
        settings.save()
        
        logger.info(f"Maintenance mode {'enabled' if enabled else 'disabled'} by {request.user.login}")
        
        return JsonResponse({
            'success': True,
            'maintenance_mode': enabled,
            'message': f'Maintenance mode {"enabled" if enabled else "disabled"} successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error toggling maintenance mode: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_POST
def update_jackpot_cooldown_api(request):
    """Update jackpot cooldown setting"""
    if not user_can_modify_settings(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        hours = int(data.get('hours', 24))
        
        if hours < 1 or hours > 168:  # Between 1 hour and 1 week
            return JsonResponse({'success': False, 'error': 'Hours must be between 1 and 168'}, status=400)
        
        settings, created = SiteSettings.objects.get_or_create(pk=1)
        settings.jackpot_cooldown = hours * 3600  # Convert to seconds
        settings.save()
        
        logger.info(f"Jackpot cooldown updated to {hours} hours by {request.user.login}")
        
        return JsonResponse({
            'success': True,
            'hours': hours,
            'message': f'Jackpot cooldown updated to {hours} hours'
        })
        
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
    except Exception as e:
        logger.error(f"Error updating jackpot cooldown: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
def site_settings_api(request):
    """Get current site settings as JSON"""
    if not user_can_access_control_panel(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        settings, created = SiteSettings.objects.get_or_create(pk=1)
        
        return JsonResponse({
            'success': True,
            'settings': {
                'maintenance_mode': settings.maintenance_mode,
                'maintenance_message': settings.maintenance_message,
                'jackpot_cooldown': settings.jackpot_cooldown,
                'jackpot_cooldown_hours': settings.jackpot_cooldown // 3600,
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting site settings: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)