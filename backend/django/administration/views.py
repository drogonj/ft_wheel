from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
import random, logging, json
import os

from ft_wheel.utils import load_wheels, build_wheel_versions

logger = logging.getLogger('backend')

def _require_superuser(request):
    """Helper to check superuser access"""
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    return None

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
    error = _require_superuser(request)
    if error: return error

    data = {}
    for slug, meta in settings.WHEEL_CONFIGS.items():
        sectors = meta.get('sectors', [])
        data[slug] = {
            'count': len(sectors),
            'sample': sectors[:5],
            'title': meta.get('title'),
            'url': meta.get('url', slug)
        }
    
    if request.headers.get('Accept', '').startswith('application/json'):
        return JsonResponse({'configs': data})
    return render(request, 'administration/adm_wheels.html', {'configs': data})


@login_required
@require_http_methods(["GET", "POST"])
def edit_wheel(request, config: str):
    error = _require_superuser(request)
    if error: return error
    
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
            return JsonResponse({'error': str(e)}, status=500)

    # POST: Update wheel
    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    # Determine what format we're receiving and convert appropriately
    if 'sectors' in payload and isinstance(payload['sectors'], list):
        # Convert sectors list to jackpots format for file storage
        sectors_list = payload['sectors']
        jackpots_dict = {}
        
        for sector in sectors_list:
            label = sector.get('label', '').strip()
            if not label:
                continue
                
            # If this label already exists, we could increment a counter
            # but for simplicity, we'll use unique keys
            base_label = label
            counter = 1
            while label in jackpots_dict:
                label = f"{base_label}_{counter}"
                counter += 1
                
            jackpots_dict[label] = {
                'color': sector.get('color', '#FFFFFF'),
                'message': sector.get('message', 'You won... something?'),
                'function': sector.get('function', 'builtins.default'),
                'args': sector.get('args', {}),
                'number': 1  # Each sector appears once
            }
        
        wheel_data = {'jackpots': jackpots_dict}
        
    elif 'sequence' in payload and isinstance(payload['sequence'], list):
        wheel_data = {'sequence': payload['sequence']}
    elif 'jackpots' in payload and isinstance(payload['jackpots'], dict):
        wheel_data = {'jackpots': payload['jackpots']}
    else:
        return HttpResponseBadRequest('Expected "sectors", "sequence", or "jackpots" in payload')

    # Handle metadata (preserve existing if not provided)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except Exception:
        existing = {}

    final_url = _normalize_wheel_name(payload.get('url') or existing.get('url') or config)
    final_title = payload.get('title') or existing.get('title') or final_url.capitalize()
    
    wheel_data.update({
        'url': final_url,
        'title': final_title,
        'slug': final_url  # Legacy compat
    })

    # Save file
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(wheel_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return JsonResponse({'error': f'Failed to write file: {e}'}, status=500)

    # Reload and return
    versions = _reload_wheels_and_versions()
    logger.info(f"Rebuilt wheel versions after edit: {versions}")
    
    new_sectors = settings.WHEEL_CONFIGS.get(final_url, {}).get('sectors', [])
    return JsonResponse({
        'status': 'ok', 
        'sectors': new_sectors, 
        'title': final_title, 
        'url': final_url
    })


@login_required
@require_POST
def create_wheel(request):
    error = _require_superuser(request)
    if error: return error

    try:
        payload = json.loads(request.body)
    except Exception:
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
        return JsonResponse({'error': str(e)}, status=500)
    
    versions = _reload_wheels_and_versions()
    logger.info(f"Rebuilt wheel versions after create: {versions}")
    return JsonResponse({'status': 'created', 'url': normalized_name, 'title': title})


@login_required
@require_POST
def delete_wheel(request, config: str):
    error = _require_superuser(request)
    if error: return error
    
    if config not in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest('Unknown wheel')
    
    # Remove file
    file_path = _get_wheel_file_path(config)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        return JsonResponse({'error': f'Cannot delete file: {e}'}, status=500)
    
    # Remove from memory and update session if needed
    del settings.WHEEL_CONFIGS[config]
    if request.session.get('wheel_config_type') == config:
        fallback = next(iter(settings.WHEEL_CONFIGS.keys()), None)
        request.session['wheel_config_type'] = fallback
    
    versions = _reload_wheels_and_versions()
    logger.info(f"Rebuilt wheel versions after delete: {versions}")
    return JsonResponse({'status': 'deleted', 'name': config})


@login_required
@require_GET
def download_wheel(request, config: str):
    error = _require_superuser(request)
    if error: return error
    
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

