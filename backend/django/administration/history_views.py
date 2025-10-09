from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.utils import timezone
from django.db.models import Q
from wheel.models import History, HistoryMark
from api.jackpots_handler import cancel_jackpot
from .admin_logging import logger as admin_logger
import json


@login_required
@require_GET
def history_admin_view(request):
    """Main history administration view with pagination and filtering"""
    if not request.user.has_perm('history_admin'):
        return HttpResponseForbidden("Access denied")
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    wheel_filter = request.GET.get('wheel', '')
    status_filter = request.GET.get('status', '')  # 'cancelled', 'active', or ''
    marked_filter = request.GET.get('marked', '')  # 'marked', 'unmarked', or ''
    
    # Base queryset
    histories = History.objects.select_related('user', 'cancelled_by').prefetch_related('marks__marked_by')
    
    # Apply filters
    if search_query:
        histories = histories.filter(
            Q(user__login__icontains=search_query) |
            Q(details__icontains=search_query) |
            Q(r_message__icontains=search_query)
        )
    
    if wheel_filter:
        histories = histories.filter(wheel=wheel_filter)
    
    if status_filter == 'cancelled':
        histories = histories.filter(is_cancelled=True)
    elif status_filter == 'success':
        histories = histories.filter(is_cancelled=False, success=True)
    elif status_filter == 'error':
        histories = histories.filter(is_cancelled=False, success=False)
    
    if marked_filter == 'marked':
        histories = histories.filter(marks__isnull=False).distinct()
    elif marked_filter == 'unmarked':
        histories = histories.filter(marks__isnull=True)
    
    # Pagination
    paginator = Paginator(histories, 50)  # 50 entries per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get available wheels for filter dropdown
    available_wheels = History.objects.values_list('wheel', flat=True).distinct().order_by('wheel')
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'wheel_filter': wheel_filter,
        'status_filter': status_filter,
        'marked_filter': marked_filter,
        'available_wheels': available_wheels,
        'user_can_cancel': request.user.has_perm('cancel_history_entry'),
    }
    
    return render(request, 'administration/history_admin.html', context)


@login_required
@require_POST
def add_history_mark(request, history_id):
    """Add a validation mark to a history entry"""
    if not request.user.has_perm('add_history_mark'):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    history = get_object_or_404(History, id=history_id)
    
    try:
        data = json.loads(request.body)
        note = data.get('note', '').strip()[:200]  # Limit note length
        
        # Create or update mark
        mark, created = HistoryMark.objects.get_or_create(
            history=history,
            marked_by=request.user,
            defaults={'note': note}
        )
        
        if not created:
            mark.note = note
            mark.marked_at = timezone.now()
            mark.save()
        
        action = 'created' if created else 'updated'
        admin_logger.info(f"history_mark {action} by={request.user.login} history_id={history_id} note_len={len(note)}")
        
        # Return updated mark information
        marks_data = []
        for mark in history.marks.all():
            marks_data.append({
                'user': mark.marked_by.login,
                'role': mark.marked_by.role,
                'note': mark.note,
                'marked_at': mark.marked_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'success': True,
            'message': 'Mark added successfully',
            'marks_count': history.marks_count,
            'marks': marks_data
        })
        
    except Exception as e:
        admin_logger.error(f"history_mark error by={request.user.login} history_id={history_id} err={e}")
        return JsonResponse({'error': 'Failed to add mark'}, status=500)


@login_required
@require_http_methods(["POST"])
def cancel_history_entry(request, history_id):
    """Cancel a history entry by calling its cancel function"""
    if not request.user.has_perm('cancel_history_entry'):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    history = get_object_or_404(History, id=history_id)
    
    if history.is_cancelled:
        return JsonResponse({'error': 'History entry is already cancelled'}, status=400)
    
    if not history.can_be_cancelled():
        return JsonResponse({'error': 'This history entry cannot be cancelled'}, status=400)
    
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '').strip()[:200]
        
        success, message, cancel_data = cancel_jackpot(request.user, history.function_name, history.r_data)
        
        if success:
            # Mark as cancelled
            history.is_cancelled = True
            history.cancelled_at = timezone.now()
            history.cancelled_by = request.user
            history.cancellation_reason = reason
            history.save()
            
            admin_logger.info(f"history_cancel success by={request.user.login} history_id={history_id} function={history.function_name} reason={reason} msg={message} data={cancel_data}")
            
            return JsonResponse({
                'success': True,
                'message': f'History entry cancelled successfully: {message}',
                'cancel_data': cancel_data
            })
        else:
            admin_logger.error(f"history_cancel failed by={request.user.login} history_id={history_id} function={history.function_name} msg={message} data={cancel_data}")
            return JsonResponse({'error': f'Cancellation failed: {message} {cancel_data}'}, status=400)
            
    except Exception as e:
        admin_logger.error(f"history_cancel error by={request.user.login} history_id={history_id} err={e}")
        return JsonResponse({'error': 'Failed to cancel history entry'}, status=500)


@login_required
@require_GET
def history_detail_api(request, history_id):
    """Get detailed information about a history entry"""
    if not request.user.has_perm('history_detail_api'):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    history = get_object_or_404(History, id=history_id)
    
    # Prepare marks data
    marks_data = []
    for mark in history.marks.all():
        marks_data.append({
            'user': mark.marked_by.login,
            'role': mark.marked_by.get_role_display(),
            'note': mark.note,
            'marked_at': mark.marked_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Prepare response data
    data = {
        'id': history.id,
        'timestamp': history.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'wheel': history.wheel,
        'details': history.details,
        'color': history.color,
        'user': history.user.login,
        'function_name': history.function_name,
        'r_message': history.r_message,
        'r_data': history.r_data,
        'success': history.success,
        'is_cancelled': history.is_cancelled,
        'cancelled_at': history.cancelled_at.strftime('%Y-%m-%d %H:%M:%S') if history.cancelled_at else None,
        'cancelled_by': history.cancelled_by.login if history.cancelled_by else None,
        'cancellation_reason': history.cancellation_reason,
        'marks_count': history.marks_count,
        'marks': marks_data,
        'can_be_cancelled': history.can_be_cancelled()
    }
    
    return JsonResponse(data)