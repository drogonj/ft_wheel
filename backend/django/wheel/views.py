from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from datetime import timedelta
import random, logging, json
import os

from .models import History
from luckywheel.utils import load_wheels, build_wheel_versions
from api.infra import handle_jackpots

logger = logging.getLogger('backend')

@login_required
@require_http_methods(["GET"])
def wheel_view(request):
    # Slug from url
    slug = request.GET.get('wheel') or request.GET.get('mode')
    wheels_store = getattr(settings, 'WHEEL_CONFIGS', {})
    if slug and slug in wheels_store:
        request.session['wheel_config_type'] = slug

    # fallback: keep existing else pick first available
    if 'wheel_config_type' not in request.session or request.session['wheel_config_type'] not in wheels_store:
        first = next(iter(wheels_store.keys()), None)
        if first:
            request.session['wheel_config_type'] = first

    config_type = request.session.get('wheel_config_type')
    sectors = wheels_store.get(config_type, {}).get('sectors', [])
    # Compute (or fetch) version id
    version_ids = getattr(settings, 'WHEEL_VERSION_IDS', {})
    version_id = version_ids.get(config_type)

    # Send only "label", "text", "color", "message" to client
    sectors = [{k: v for k, v in sector.items() if k in ('label', 'text', 'color', 'message')} for sector in sectors]

    request.session['current_wheel_sectors'] = sectors
    # Pass Python list (template uses json_script)
    return render(request, 'wheel/wheel.html', {"jackpots": sectors, "wheel_slug": config_type, 'wheel_version_id': version_id})


@login_required
@require_http_methods(["POST"])
def spin_view(request):
    if not request.user.can_spin():
        return HttpResponseForbidden();

    config_type = request.session.get('wheel_config_type', 'standard')
    sectors = settings.WHEEL_CONFIGS[config_type]['sectors'] if config_type in settings.WHEEL_CONFIGS else []
    # If config not in sectors, reject like outdated version (this error should happen only if a wheel was deleted/renamed or a user beeing naughty)
    if not sectors:
        return JsonResponse({'error': 'outdated_wheel', 'expected_version': "unknown"}, status=409)
    # Client provided version id? ensure still current.
    try:
        body = json.loads(request.body or '{}')
    except Exception:
        body = {}
    client_version = body.get('wheel_version_id')
    current_version = getattr(settings, 'WHEEL_VERSION_IDS', {}).get(config_type)
    if not client_version:
        return JsonResponse({'error': 'missing_wheel_version_id', 'expected_version': current_version}, status=409)
    if current_version and client_version != current_version:
        return JsonResponse({'error': 'outdated_wheel', 'expected_version': current_version if current_version else "unknown"}, status=409)

    result = random.randint(0, len(sectors)-1)
    request.user.last_spin = timezone.now()
    request.user.save(update_fields=["last_spin"])

    try:
        sent_to_infra = handle_jackpots(request.user, sectors[result])
        details=sectors[result]['label']
        if not sent_to_infra:
            details += "- ERROR"

        History.objects.create(
            wheel=config_type,
            details=details,
            color=sectors[result]['color'],
            user=request.user
        )
    except Exception as e:
        logger.error("Unexpected error while saving history or handling jackpots: %s", e)

    logger.info(f"Jackpots! {request.user.login} - {config_type} - {sectors[result]}")

    sector = sectors[result]
    # Send only "label", "text", "color" and "message" to client
    sector = {k: v for k, v in sector.items() if k in ('label', 'text', 'color', 'message')}

    return JsonResponse({'result': result, 'sector': sector, 'wheel_version_id': current_version})


@login_required
@require_http_methods(["GET"])
def time_to_spin_view(request):
    return JsonResponse({'timeToSpin': str(request.user.time_to_spin())})


@login_required
@csrf_protect
@require_http_methods(["POST"])
def change_wheel_config(request):
    try:
        data = json.loads(request.body)
        mode = data.get('mode')
        if mode not in settings.WHEEL_CONFIGS:
            return JsonResponse({'error': 'Configuration not available'}, status=400)
        
        sectors = settings.WHEEL_CONFIGS[mode]['sectors']
        request.session['wheel_config_type'] = mode
        
        return JsonResponse({'sectors': sectors})
    except Exception as e:
        logger.error(f"Error while changing wheel configuration: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
@require_http_methods(["GET"])
def history_view(request):
    # Get all history entries from any users (maximum of 100 entries)
    all_history = History.objects.all().order_by('-timestamp')[:100]
    my_history = History.objects.filter(user=request.user).order_by('-timestamp')[:100]
    
    return render(request, 'wheel/history.html', {'all_history': all_history, 'my_history': my_history})


@login_required
@require_http_methods(["GET"])
def faq_view(request):
    # Render the FAQ page
    return render(request, 'wheel/faq.html')


@require_http_methods(["GET"])
def patch_notes_api(request):
    try:
        patch_notes_path = os.path.join(settings.BASE_DIR, 'data', 'patch_notes.json')
        with open(patch_notes_path, 'r', encoding='utf-8') as f:
            patch_notes_data = json.load(f)
        return JsonResponse(patch_notes_data)
    except FileNotFoundError:
        return JsonResponse({
            'current_version': '1.0.0',
            'versions': {}
        })
    except Exception as e:
        logger.error(f"Error while reading patch notes: {e}")
        return JsonResponse({'error': 'Server error'}, status=500)


# ---------------- Admin Wheel Management ----------------

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
    return render(request, 'wheel/admin_wheels.html', {'configs': data})


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

    # Determine what format we're receiving
    if 'sectors' in payload and isinstance(payload['sectors'], list):
        wheel_data = {'sequence': payload['sectors']}
    elif 'jackpots' in payload and isinstance(payload['jackpots'], dict):
        wheel_data = {'jackpots': payload['jackpots']}
    else:
        return HttpResponseBadRequest('Expected either "sectors" or "jackpots" in payload')

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
        'sequence': []
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

