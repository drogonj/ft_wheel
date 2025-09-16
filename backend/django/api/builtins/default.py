
def default(api_intra: object, user: object, args: dict):
    """Default function when landing on a sector."""

    try:
        api_intra.request('GET', f'/users/{user.login}')
    except Exception as e:
        print(f"Error fetching user data: {e}")
    return True

def cancel_default(api_intra: object, user: object, args: dict):
    """Default function when cancelling a sector."""
    return True
