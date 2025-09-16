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
from api.jackpots_handler import handle_jackpots

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

    # Send only "label", "color", "message" to client
    sectors = [{k: v for k, v in sector.items() if k in ('label', 'color', 'message')} for sector in sectors]

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
        handle_jackpots(request.user, sectors[result])
        details=sectors[result]['label']

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
    # Send only "label", "color" and "message" to client
    sector = {k: v for k, v in sector.items() if k in ('label', 'color', 'message')}

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
