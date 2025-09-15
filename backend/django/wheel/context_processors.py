from django.conf import settings

def wheel_list(request):
    """Expose available wheels with slug & title (and version id) to all templates as WHEEL_LIST.
    Also expose flags about user (superuser / testmode) for JS consumption.
    """
    wheels_meta = []
    wheel_store = getattr(settings, 'WHEEL_CONFIGS', {})
    version_ids = getattr(settings, 'WHEEL_VERSION_IDS', {})
    for slug, data in wheel_store.items():
        wheels_meta.append({
            'slug': slug,
            'title': data.get('title', slug),
            'version_id': version_ids.get(slug)
        })
    # sort by title for consistency
    wheels_meta.sort(key=lambda x: x['title'].lower())
    # testmode: expose if user is superuser or has attribute test_mode True
    user = getattr(request, 'user', None)
    is_super = bool(getattr(user, 'is_superuser', False))
    test_mode = bool(is_super or getattr(user, 'test_mode', False))  # Reuse is_super instead of re-checking
    return {
        'WHEEL_LIST': wheels_meta,
        'USER_IS_SUPERUSER': is_super,
        'USER_TEST_MODE': test_mode,
    }
