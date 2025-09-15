from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_GET, require_POST
from datetime import timedelta
import random, logging, json
import os

from .models import History, HistoryManager
from api.infra import handle_jackpots

logger = logging.getLogger('backend')
HistoryManager = History.objects

@login_required
@require_http_methods(["GET"])
def wheel_view(request):
    if not request.user:
        return HttpResponseBadRequest()
    
    # Slug depuis URL
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
    sectors = wheels_store.get(config_type, [])
    request.session['current_wheel_sectors'] = sectors
    return render(request, 'wheel/wheel.html', {"jackpots": sectors, "wheel_slug": config_type})


@login_required
@require_http_methods(["POST"])
def spin_view(request):
    if not request.user:
        return HttpResponseBadRequest()
    if not request.user.can_spin():
        return HttpResponseForbidden();

    config_type = request.session.get('wheel_config_type', 'standard')
    sectors = settings.WHEEL_CONFIGS[config_type]

    result = random.randint(0, len(sectors)-1)
    request.user.last_spin = timezone.now()
    request.user.save(update_fields=["last_spin"])

    try:
        sent_to_infra = handle_jackpots(request.user, sectors[result])
        details=sectors[result]['label']
        if not sent_to_infra:
            details += "- ERROR"

        HistoryManager.create(
            wheel=config_type,
            details=details,
            color=sectors[result]['color'],
            user=request.user
        )
    except Exception as e:
        logger.error("Unexpected error while saving history or handling jackpots: %s", e)

    logger.info(f"Jackpots! {request.user.login} - {config_type} - {sectors[result]}")
    return JsonResponse({'result': result, 'sector': sectors[result]})


@login_required
@require_http_methods(["GET"])
def time_to_spin_view(request):
    if not request.user:
        return HttpResponseBadRequest()
    return JsonResponse({'timeToSpin': str(request.user.time_to_spin())})


@login_required
@csrf_protect
@require_http_methods(["POST"])
def change_wheel_config(request):
    try:
        data = json.loads(request.body)
        mode = data.get('mode')
        
        # Vérifier si le mode demandé existe
        if mode not in settings.WHEEL_CONFIGS:
            return JsonResponse({'error': 'Configuration non disponible'}, status=400)
        
        # Générer les secteurs pour ce mode
        sectors = settings.WHEEL_CONFIGS[mode]
        
        # Stocker le type de configuration dans la session
        request.session['wheel_config_type'] = mode
        
        return JsonResponse({'sectors': sectors})
        
    except Exception as e:
        logger.error(f"Erreur lors du changement de configuration: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
@require_http_methods(["GET"])
def history_view(request):
    if not request.user:
        return HttpResponseBadRequest()
    
    # Get all history entries from any users (maximum of 100 entries)
    all_history = HistoryManager.all().order_by('-timestamp')[:100]
    my_history = HistoryManager.filter(user=request.user).order_by('-timestamp')[:100]
    
    return render(request, 'wheel/history.html', {'all_history': all_history, 'my_history': my_history})


@login_required
@require_http_methods(["GET"])
def faq_view(request):
    if not request.user:
        return HttpResponseBadRequest()
    
    # Render the FAQ page
    return render(request, 'wheel/faq.html')


@require_http_methods(["GET"])
def patch_notes_api(request):
    """API pour récupérer les patch notes actuelles"""
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
        logger.error(f"Erreur lors de la lecture des patch notes: {e}")
        return JsonResponse({'error': 'Erreur serveur'}, status=500)


# ---------------- Admin Wheel Management ----------------
@login_required
@require_GET
def admin_wheels(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    # Provide a simple JSON list if expecting API, otherwise render template (template can be added later)
    data = {}
    dyn = getattr(settings, 'DYNAMIC_WHEELS', {})
    for slug, meta in dyn.items():
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
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    if config not in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest("Unknown wheel configuration")

    wheel_dir = settings.WHEEL_CONFIGS_DIR
    file_path = os.path.join(wheel_dir, f'jackpots_{config}.json')

    if request.method == 'GET':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        # Return sectors in current in-memory order too
        ordered = settings.WHEEL_CONFIGS[config]
        return JsonResponse({
            'file': data,
            'ordered': ordered
        })

    # POST: update wheel definition
    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    sectors_payload = payload.get('sectors')
    jackpots = payload.get('jackpots')
    new_title = payload.get('title')
    new_url = payload.get('url')

    to_write = None
    if isinstance(sectors_payload, list):
        # Direct ordered sequence mode
        to_write = {'sequence': sectors_payload}
    elif isinstance(jackpots, dict):
        to_write = {'jackpots': jackpots}
    else:
        return HttpResponseBadRequest('Expected either {"sectors": [...]} or {"jackpots": {...}}')

    # Preserve existing metadata (title, slug) if present
    existing = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            existing = json.load(f)
    except Exception:
        pass
    # Determine slug/url final
    final_url = (new_url or existing.get('url') or existing.get('slug') or config).lower().replace(' ', '_')
    final_title = new_title or existing.get('title') or final_url.capitalize()
    to_write.setdefault('url', final_url)
    to_write.setdefault('title', final_title)
    # Keep legacy slug for backward compat
    to_write.setdefault('slug', final_url)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(to_write, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return JsonResponse({'error': f'Failed to write {file_path}: {e}'}, status=500)

    from luckywheel.utils import load_wheels
    # Reload dynamic wheels (single pass reload for simplicity)
    settings.DYNAMIC_WHEELS = load_wheels(settings.WHEEL_CONFIGS_DIR, balance=False)
    settings.WHEEL_CONFIGS = { slug: meta['sectors'] for slug, meta in settings.DYNAMIC_WHEELS.items() }
    return JsonResponse({'status': 'ok', 'sectors': settings.WHEEL_CONFIGS.get(final_url, []), 'title': final_title, 'url': final_url})


@login_required
@require_POST
def create_wheel(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')
    raw_url = payload.get('url') or payload.get('name')
    title = payload.get('title')
    if not raw_url:
        return HttpResponseBadRequest('Missing url')
    url_norm = raw_url.lower().replace(' ', '_')
    if url_norm in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest('Wheel already exists')
    final_title = title or url_norm.capitalize()
    file_path = os.path.join(settings.WHEEL_CONFIGS_DIR, f'jackpots_{url_norm}.json')
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({'url': url_norm, 'slug': url_norm, 'title': final_title, 'sequence': []}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    # Reload global stores to include new wheel
    from luckywheel.utils import load_wheels
    settings.DYNAMIC_WHEELS = load_wheels(settings.WHEEL_CONFIGS_DIR, balance=False)
    settings.WHEEL_CONFIGS = { slug: meta['sectors'] for slug, meta in settings.DYNAMIC_WHEELS.items() }
    return JsonResponse({'status': 'created', 'url': url_norm, 'title': final_title})


@login_required
@require_POST
def delete_wheel(request, config: str):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    if config not in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest('Unknown wheel')
    file_path = os.path.join(settings.WHEEL_CONFIGS_DIR, f'jackpots_{config}.json')
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        return JsonResponse({'error': f'Cannot delete file: {e}'}, status=500)
    del settings.WHEEL_CONFIGS[config]
    if hasattr(settings, 'DYNAMIC_WHEELS') and config in settings.DYNAMIC_WHEELS:
        del settings.DYNAMIC_WHEELS[config]
    # Clean session if user was on this config
    if request.session.get('wheel_config_type') == config:
        fallback = next(iter(settings.WHEEL_CONFIGS.keys()), None)
        request.session['wheel_config_type'] = fallback
    return JsonResponse({'status': 'deleted', 'name': config})


@login_required
@require_POST
def reload_wheels(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    from luckywheel.utils import load_wheels
    settings.DYNAMIC_WHEELS = load_wheels(settings.WHEEL_CONFIGS_DIR, balance=False)
    settings.WHEEL_CONFIGS = { slug: meta['sectors'] for slug, meta in settings.DYNAMIC_WHEELS.items() }
    return JsonResponse({'status': 'reloaded', 'count': len(settings.WHEEL_CONFIGS)})


@login_required
@require_GET
def download_wheel(request, config: str):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    if config not in settings.WHEEL_CONFIGS:
        return HttpResponseBadRequest('Unknown wheel')
    wheel_dir = settings.WHEEL_CONFIGS_DIR
    file_path = os.path.join(wheel_dir, f'jackpots_{config}.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    from django.http import HttpResponse
    resp = HttpResponse(data, content_type='application/json')
    resp['Content-Disposition'] = f'attachment; filename="jackpots_{config}.json"'
    return resp
