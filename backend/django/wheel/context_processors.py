from django.conf import settings

def wheel_list(request):
    """Expose available wheels with slug & title to all templates as WHEEL_LIST."""
    wheels_meta = []
    wheel_store = getattr(settings, 'DYNAMIC_WHEELS', {})
    for slug, data in wheel_store.items():
        wheels_meta.append({
            'slug': slug,
            'title': data.get('title', slug)
        })
    # sort by title for consistency
    wheels_meta.sort(key=lambda x: x['title'].lower())
    return {'WHEEL_LIST': wheels_meta}
