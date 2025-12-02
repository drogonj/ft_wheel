from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction

from .admin_logging import logger as admin_logger
from wheel.models import Ticket

User = get_user_model()


@login_required
@require_POST
@transaction.atomic
def grant_ticket_api(request):
    if not request.user.has_perm('grant_ticket_api'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = request.body.decode('utf-8')
    except Exception:
        data = ''
    import json
    try:
        payload = json.loads(data or '{}')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    login = (payload.get('login') or '').strip()
    wheel_slug = (payload.get('wheel') or '').strip()

    if not login or not wheel_slug:
        return JsonResponse({'success': False, 'error': 'Missing login or wheel'}, status=400)

    # Validate wheel exists
    wheels = getattr(settings, 'WHEEL_CONFIGS', {})
    if wheel_slug not in wheels:
        return JsonResponse({'success': False, 'error': 'Unknown wheel slug'}, status=400)
    if not wheels[wheel_slug].get('ticket_only', False):
        return JsonResponse({'success': False, 'error': 'Wheel is not ticket-only'}, status=400)

    try:
        user = User.objects.get(login=login)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

    t = Ticket.objects.create(user=user, wheel_slug=wheel_slug, granted_by=request.user)
    admin_logger.info(f"ticket_granted by={request.user.login} to={user.login} wheel={wheel_slug} ticket_id={t.id}")

    return JsonResponse({'success': True, 'ticket': {'id': t.id, 'user': user.login, 'wheel': wheel_slug}})


@login_required
@require_GET
def tickets_summary_api(request):
    if not request.user.has_perm('ticket_summary_api'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    # Return counts per wheel (unused only) and last 20 granted
    from django.db.models import Count
    unused = (
        Ticket.objects.filter(used_at__isnull=True)
        .values('wheel_slug')
        .annotate(count=Count('id'))
        .order_by('wheel_slug')
    )
    recent = (
        Ticket.objects.select_related('user', 'granted_by')
        .order_by('-created_at')[:50]
    )
    return JsonResponse({
        'success': True,
        'unused': list(unused),
        'recent': [
            {
                'id': t.id,
                'wheel': t.wheel_slug,
                'user': t.user.login,
                'granted_by': t.granted_by.login if t.granted_by else None,
                'used_at': t.used_at.isoformat() if t.used_at else None,
                'created_at': t.created_at.isoformat(),
            }
            for t in recent
        ]
    })
