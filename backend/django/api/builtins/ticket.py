from wheel.models import Ticket, User
from django.conf import settings

# # # # # # # # # # # # # # # # # # # # # 
# Grant Ticket to a user for a given wheel
# # # # # # # # # # # # # # # # # # # # #

# Example of jackpots.json entry:
# "Ticket !": {
#     "color": "#FFD700",
#     "number": 2,
#     "message": "You won a ticket for the wheel '{wheel}'!",
#     "function": "builtins.ticket",
#     "args": {
#         "wheel": "42_wheel" <- slug of the wheel (must be ticket only)
#     }
# }

def ticket(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Grant a ticket to a user for a specific wheel.
    Args should include:
    - 'login': user's login
    - 'wheel': wheel slug

    Returns: (bool, str, dict) - (success, message, data)
    """
    wheel_slug = (args.get('wheel') or '').strip()

    if not wheel_slug:
        return False, "Missing wheel", {}

    # Validate wheel exists
    wheels = getattr(settings, 'WHEEL_CONFIGS', {})
    if wheel_slug not in wheels:
        return False, "Unknown wheel slug", {}
    if not wheels[wheel_slug].get('ticket_only', False):
        return False, "Wheel is not ticket-only", {}

    t = Ticket.objects.create(user=user, wheel_slug=wheel_slug, granted_by=None)

    return True, "Ticket granted", {'id': t.id, 'user': user.login, 'wheel': wheel_slug}


def cancel_ticket(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Cancel (delete) an unused ticket for a user for a specific wheel.
    Args should include:
    - 'login': user's login
    - 'wheel': wheel slug

    Returns: (bool, str, dict) - (success, message, data)
    """
    wheel_slug = (args.get('wheel') or '').strip()

    if not wheel_slug:
        return False, "Missing wheel", {}

    ticket = Ticket.objects.filter(user=user, wheel_slug=wheel_slug, used_at__isnull=True).first()
    if not ticket:
        return True, "No unused ticket found for this user and wheel", {}

    ticket.delete()

    return True, "Ticket cancelled", {'ticket_id': ticket.id}
