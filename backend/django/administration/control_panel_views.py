from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.utils import timezone
from django.db.models import Count, Q
from django.db import transaction
from datetime import datetime, timedelta
import json
from .admin_logging import logger as admin_logger

from users.models import Account
from wheel.models import History
from .models import SiteSettings


@login_required
@require_GET
def control_panel_view(request):
    """Main control panel dashboard"""
    if not request.user.has_perm('control_panel'):
        return HttpResponseForbidden("Access denied")
    
    # Get or create site settings
    settings, created = SiteSettings.objects.get_or_create(pk=1)
    
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
        admin_logger.error(f"Error calculating stats: {e}")
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
        admin_logger.error(f"Error getting recent activity: {e}")
        recent_users = []
        recent_errors = []
    
    context = {
        'settings': settings,
        'stats': stats,
        'recent_users': recent_users,
        'recent_errors': recent_errors,
        'user_role': request.user.role,
    }
    
    return render(request, 'administration/control_panel.html', context)


@login_required
@require_POST
def toggle_maintenance_api(request):
    """Toggle maintenance mode via API"""
    if not request.user.has_perm('modify_site_settings'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        enabled = bool(data.get('enabled', False))
        message = data.get('message', '').strip()
        
        if not message:
            message = "The site is currently under maintenance. Please check back later."
        
        with transaction.atomic():
            settings, created = SiteSettings.objects.select_for_update().get_or_create(pk=1)
            settings.maintenance_mode = enabled
            settings.maintenance_message = message
            settings.save()
        # business log
        admin_logger.info(f"maintenance_toggle by={request.user.login} enabled={enabled}")
        
        return JsonResponse({
            'success': True,
            'maintenance_mode': enabled,
            'message': f'Maintenance mode {"enabled" if enabled else "disabled"} successfully'
        })
        
    except json.JSONDecodeError:
        admin_logger.error(f"maintenance_toggle_error by={request.user.login} error=Invalid JSON")
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        admin_logger.error(f"maintenance_toggle_error by={request.user.login} error={str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def update_jackpot_cooldown_api(request):
    """Update jackpot cooldown setting"""
    if not request.user.has_perm('modify_site_settings'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
    try:
        data = json.loads(request.body)
        hours = int(data.get('hours', 24))
        
        if hours < 1 or hours > 168:  # Between 1 hour and 1 week
            return JsonResponse({'success': False, 'error': 'Hours must be between 1 and 168'}, status=400)
        
        with transaction.atomic():
            settings, created = SiteSettings.objects.select_for_update().get_or_create(pk=1)
            settings.jackpot_cooldown = hours * 3600  # Convert to seconds
            settings.save()
        # business log
        admin_logger.info(f"jackpot_cooldown_update by={request.user.login} hours={hours}")
        
        return JsonResponse({
            'success': True,
            'hours': hours,
            'message': f'Jackpot cooldown updated to {hours} hours'
        })
        
    except (json.JSONDecodeError, ValueError):
        admin_logger.error(f"jackpot_cooldown_update_error by={request.user.login} error=Invalid data")
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
    except Exception as e:
        admin_logger.error(f"jackpot_cooldown_update_error by={request.user.login} error={str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_GET
@login_required
def site_settings_api(request):
    """Get current site settings as JSON"""
    if not request.user.has_perm('site_settings_api'):
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
                'announcement_message': settings.announcement_message,
            }
        })
        
    except Exception as e:
        admin_logger.error(f"Error getting site settings: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def update_announcement_api(request):
    """Update site-wide announcement message"""
    if not request.user.has_perm('modify_site_settings'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
        message = (data.get('message') or '').strip()
        if len(message) > 255:
            return JsonResponse({'success': False, 'error': 'Message too long (max 255)'}, status=400)

        with transaction.atomic():
            site_settings, _ = SiteSettings.objects.select_for_update().get_or_create(pk=1)
            site_settings.announcement_message = message or "Welcome on ft_wheel, have fun !"
            site_settings.save(update_fields=['announcement_message'])
        admin_logger.info(f"announcement_update by={request.user.login} message_len={len(site_settings.announcement_message)}")

        return JsonResponse({'success': True, 'message': 'Announcement updated successfully'})
    except (json.JSONDecodeError, ValueError):
        admin_logger.error(f"announcement_update_error by={request.user.login} error=Invalid data")
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
    except Exception as e:
        admin_logger.error(f"announcement_update_error by={request.user.login} error={str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)