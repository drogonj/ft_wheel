from django.conf import settings

def wheel_list(request):
    """Expose available wheels with slug & title (and version id) to all templates as WHEEL_LIST.
    Also expose flags about user (role info / testmode) for JS consumption.
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
    
    user = getattr(request, 'user', None)
    
    # Role-based checks
    is_admin = False
    is_moderator = False
    is_super = False  # Keep for Django admin compatibility
    
    if user and user.is_authenticated:
        is_admin = getattr(user, 'role', None) == 'admin'
        is_moderator = getattr(user, 'role', None) in ['moderator', 'admin']
        # Django admin compatibility - admin role has superuser privileges
        is_super = is_admin
    
    test_mode = bool(getattr(user, 'test_mode', False))
    
    return {
        'WHEEL_LIST': wheels_meta,
        'USER_IS_SUPERUSER': is_super,  # Keep for backward compatibility
        'USER_IS_ADMIN': is_admin,
        'USER_IS_MODERATOR': is_moderator,
        'USER_TEST_MODE': test_mode,
    }
