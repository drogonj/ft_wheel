from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
import os, json

from ft_wheel.utils import load_wheels, build_wheel_versions
from .admin_logging import logger as admin_logger


def _get_wheel_file_path(config):
    """Helper to get file path for a wheel config"""
    return os.path.join(settings.WHEEL_CONFIGS_DIR, f'jackpots_{config}.json')

def _reload_wheels_and_versions():
    """Helper to reload configs and rebuild version IDs"""
    settings.WHEEL_CONFIGS = load_wheels(settings.WHEEL_CONFIGS_DIR)
    settings.WHEEL_VERSION_IDS = build_wheel_versions(settings.WHEEL_CONFIGS)
    return settings.WHEEL_VERSION_IDS

def _normalize_wheel_name(name):
    """Helper to normalize wheel names"""
    return name.lower().replace(' ', '_')


@login_required
@require_GET
def admin_wheels(request):
    """Main wheels administration view"""
    if not request.user.has_perm('admin_wheels'):
        return HttpResponseForbidden("Access denied")

    data = {}
    for slug, meta in settings.WHEEL_CONFIGS.items():
        sectors = meta.get('sectors', [])
        data[slug] = {
            'count': len(sectors),
            'sample': sectors[:5],
            'title': meta.get('title'),
            'url': meta.get('url', slug),
            'ticket_only': bool(meta.get('ticket_only', False)),
        }
    
    if request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse({'configs': data})
    return render(request, 'administration/adm_wheels.html', {'configs': data})


@login_required
@require_http_methods(["GET", "POST"])
def edit_wheel(request, config: str):
    """Edit wheel configuration - view and modify sectors"""
    if not request.user.has_perm('edit_wheel'):
        return HttpResponseForbidden("Access denied")
    
    if config not in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest("Unknown wheel configuration")

    file_path = _get_wheel_file_path(config)

    if request.method == 'GET':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
            current_sectors = settings.WHEEL_CONFIGS[config]['sectors']
            return JsonResponse({'file': file_data, 'ordered': current_sectors})
        except Exception as e:
            admin_logger.error(f"Failed to load wheel {config}: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    try:
        payload = json.loads(request.body)
    except Exception as e:
        admin_logger.error(f"wheel_edit invalid_json by={request.user.login} slug={config} err={e}")
        return HttpResponseBadRequest('Invalid JSON')

    # Determine what format we're receiving and convert appropriately
    if 'sectors' in payload and isinstance(payload['sectors'], list):
        sectors_list = payload['sectors']
        
        # Check if there are duplicate labels (to determine storage format)
        labels = [sector.get('label', '').strip() for sector in sectors_list if sector.get('label', '').strip()]
        has_duplicates = len(labels) != len(set(labels))
        
        if has_duplicates:
            # Use sequence format to preserve all duplicates exactly
            sequence_list = []
            for sector in sectors_list:
                label = sector.get('label', '').strip()
                if not label:
                    continue
                sequence_list.append({
                    'label': label,
                    'color': sector.get('color', '#FFFFFF'),
                    'message': sector.get('message', 'You won... something?'),
                    'function': sector.get('function', 'builtins.default'),
                    'args': sector.get('args', {})
                })
            
            wheel_data = {'sequence': sequence_list}
        else:
            # No duplicates, use jackpots format (more efficient)
            jackpots_dict = {}
            for sector in sectors_list:
                label = sector.get('label', '').strip()
                if not label:
                    continue
                    
                jackpots_dict[label] = {
                    'color': sector.get('color', '#FFFFFF'),
                    'message': sector.get('message', 'You won... something?'),
                    'function': sector.get('function', 'builtins.default'),
                    'args': sector.get('args', {}),
                    'number': 1
                }
            
            wheel_data = {'jackpots': jackpots_dict}
        
    elif 'sequence' in payload and isinstance(payload['sequence'], list):
        wheel_data = {'sequence': payload['sequence']}
    elif 'jackpots' in payload and isinstance(payload['jackpots'], dict):
        wheel_data = {'jackpots': payload['jackpots']}
    else:
        admin_logger.error(f"wheel_edit invalid_payload by={request.user.login} slug={config}")
        return HttpResponseBadRequest('Expected "sectors", "sequence", or "jackpots" in payload')

    # Handle metadata (preserve existing if not provided)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except Exception:
        existing = {}

    final_url = _normalize_wheel_name(payload.get('url') or existing.get('url') or config)
    final_title = payload.get('title') or existing.get('title') or final_url.capitalize()
    final_ticket_only = bool(payload.get('ticket_only')) if 'ticket_only' in payload else bool(existing.get('ticket_only', False))
    
    wheel_data.update({
        'url': final_url,
        'title': final_title,
        'slug': final_url,  # Legacy compat
        'ticket_only': final_ticket_only,
    })

    # If URL (slug) changed, rename file path accordingly
    new_file_path = _get_wheel_file_path(final_url)
    try:
        if new_file_path != file_path and os.path.exists(file_path):
            os.replace(file_path, new_file_path)
            file_path = new_file_path
    except Exception as e:
        admin_logger.error(f"wheel_edit rename_failed by={request.user.login} from={config} to={final_url} err={e}")
        return JsonResponse({'error': f'Failed to rename file: {e}'}, status=500)

    # Save file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(wheel_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        admin_logger.error(f"wheel_edit save_failed by={request.user.login} slug={final_url} err={e}")
        return JsonResponse({'error': f'Failed to write file: {e}'}, status=500)

    # Reload and return
    versions = _reload_wheels_and_versions()
    sectors = settings.WHEEL_CONFIGS.get(final_url, {}).get('sectors', [])
    admin_logger.info(f"wheel_edit by={request.user.login} slug={final_url} title={final_title} sectors={len(sectors)} sectors={str(sectors)}")

    new_sectors = settings.WHEEL_CONFIGS.get(final_url, {}).get('sectors', [])
    return JsonResponse({
        'status': 'ok', 
        'sectors': new_sectors, 
        'title': final_title, 
        'url': final_url
    })


@login_required
@require_POST
def upload_wheel(request):
    """Upload a wheel configuration JSON file or raw JSON body.

    Accepts multipart/form-data with a file field named 'file' or
    application/json body with the wheel data. The JSON must contain at least
    one of: 'sequence' (list) or 'jackpots' (dict). Optional fields: 'url'/'slug', 'title'.
    """
    if not request.user.has_perm('edit_wheel'):
        return HttpResponseForbidden("Modification access denied")

    data = None
    MAX_BYTES = 512 * 1024  # 512KB per upload
    # Multipart upload
    if request.FILES.get('file'):
        try:
            f = request.FILES['file']
            if f.size and f.size > MAX_BYTES:
                return HttpResponseBadRequest('File too large (max 512KB)')
            raw = f.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return HttpResponseBadRequest('File too large (max 512KB)')
            raw = raw.decode('utf-8', errors='strict')
            data = json.loads(raw)
        except Exception as e:
            admin_logger.error(f"wheel_upload invalid_file by={request.user.login} err={e}")
            return HttpResponseBadRequest(f'Invalid file: {e}')
    else:
        # Fallback to JSON body
        try:
            if request.META.get('CONTENT_LENGTH') and int(request.META['CONTENT_LENGTH']) > MAX_BYTES:
                return HttpResponseBadRequest('Payload too large (max 512KB)')
            body = request.body[:MAX_BYTES + 1]
            if len(body) > MAX_BYTES:
                return HttpResponseBadRequest('Payload too large (max 512KB)')
            data = json.loads(body)
        except Exception as e:
            admin_logger.error(f"wheel_upload invalid_json by={request.user.login} err={e}")
            return HttpResponseBadRequest('Invalid JSON payload')

    if not isinstance(data, dict):
        return HttpResponseBadRequest('Payload must be a JSON object')

    if not (('sequence' in data and isinstance(data['sequence'], list)) or
            ('jackpots' in data and isinstance(data['jackpots'], dict))):
        return HttpResponseBadRequest("JSON must include 'sequence' (list) or 'jackpots' (dict)")

    raw_name = data.get('url') or data.get('slug') or 'uploaded'
    normalized = _normalize_wheel_name(raw_name)

    # If name already exists, add numeric suffix
    base = normalized
    i = 1
    while normalized in settings.WHEEL_CONFIGS:
        normalized = f"{base}-{i}"
        i += 1

    title = data.get('title') or normalized.capitalize()

    # Build final data to save: preserve sequence/jackpots as provided
    out = {
        'url': normalized,
        'slug': normalized,
        'title': title,
    }
    if 'sequence' in data:
        out['sequence'] = data['sequence']
    if 'jackpots' in data:
        out['jackpots'] = data['jackpots']

    # Ensure directory exists
    try:
        os.makedirs(settings.WHEEL_CONFIGS_DIR, exist_ok=True)
    except Exception as e:
        admin_logger.error(f"wheel_upload mkdir_failed by={request.user.login} err={e}")
        return JsonResponse({'error': f'Failed to ensure configs dir: {e}'}, status=500)

    # Save file
    file_path = _get_wheel_file_path(normalized)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
    except Exception as e:
        admin_logger.error(f"wheel_upload save_failed by={request.user.login} slug={normalized} err={e}")
        return JsonResponse({'error': str(e)}, status=500)

    versions = _reload_wheels_and_versions()
    sectors = settings.WHEEL_CONFIGS.get(normalized, {}).get('sectors', [])
    admin_logger.info(
       f"wheel_upload by={request.user.login} slug={normalized} title={title} "
       f"sectors_count={len(sectors)} sectors={str(sectors)}"
    )
    return JsonResponse({'status': 'uploaded', 'url': normalized, 'title': title})


@login_required
@require_POST
def create_wheel(request):
    """Create a new wheel configuration"""
    if not request.user.has_perm('edit_wheel'):
        return HttpResponseForbidden("Modification access denied")

    try:
        payload = json.loads(request.body)
    except Exception as e:
        admin_logger.error(f"wheel_create invalid_json by={request.user.login} err={e}")
        return HttpResponseBadRequest('Invalid JSON')
    
    raw_name = payload.get('url') or payload.get('name')
    if not raw_name:
        return HttpResponseBadRequest('Missing url/name')
    
    normalized_name = _normalize_wheel_name(raw_name)
    if normalized_name in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest('Wheel already exists')
    
    title = payload.get('title') or normalized_name.capitalize()
    wheel_data = {
        'url': normalized_name,
        'slug': normalized_name,
        'title': title,
        'jackpots': {}
    }
    
    file_path = _get_wheel_file_path(normalized_name)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(wheel_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        admin_logger.error(f"wheel_create save_failed by={request.user.login} slug={normalized_name} err={e}")
        return JsonResponse({'error': str(e)}, status=500)
    
    versions = _reload_wheels_and_versions()
    sectors = settings.WHEEL_CONFIGS.get(normalized_name, {}).get('sectors', [])
    admin_logger.info(f"wheel_create by={request.user.login} slug={normalized_name} title={title} sectors_count={len(sectors)} sectors={str(sectors)}")
    return JsonResponse({'status': 'created', 'url': normalized_name, 'title': title})


@login_required
@require_POST
def delete_wheel(request, config: str):
    """Delete a wheel configuration"""
    if not request.user.has_perm('edit_wheel'):
        return HttpResponseForbidden("Modification access denied")
    
    if config not in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest('Unknown wheel')
    
    # Remove file
    file_path = _get_wheel_file_path(config)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        admin_logger.error(f"wheel_delete delete_failed by={request.user.login} slug={config} err={e}")
        return JsonResponse({'error': f'Cannot delete file: {e}'}, status=500)
    
    # Remove from memory and update session if needed
    del settings.WHEEL_CONFIGS[config]
    if request.session.get('wheel_config_type') == config:
        fallback = next(iter(settings.WHEEL_CONFIGS.keys()), None)
        request.session['wheel_config_type'] = fallback
    
    versions = _reload_wheels_and_versions()
    admin_logger.info(f"wheel_delete by={request.user.login} slug={config}")
    return JsonResponse({'status': 'deleted', 'name': config})


@login_required
@require_GET
def download_wheel(request, config: str):
    """Download wheel configuration as JSON file"""
    if not request.user.has_perm('admin_wheels'):
        return HttpResponseForbidden("Access denied")
    
    if config not in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest('Unknown wheel')
    
    file_path = _get_wheel_file_path(config)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    response = HttpResponse(data, content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="jackpots_{config}.json"'
    return response

