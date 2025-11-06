
# # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Give or take coalition points to a user's coalition
# # # # # # # # # # # # # # # # # # # # # # # # # # # 


# Example of GET /users/{login}/coalitions
# [
#    {
#       "id":334,
#       "name":"Technicians",
#       "slug":"technicians",
#       "image_url":"https://cdn.intra.42.fr/coalition/image/334/technicians.svg",
#       "cover_url":"https://cdn.intra.42.fr/coalition/cover/334/background_login-a4e0666f73c02f025f590b474b394fd86e1cae20e95261a6e4862c2d0faa1b04.jpg",
#       "color":"#FFA91F",
#       "score":1924051,
#       "user_id":208584
#    }
# ]

# Example of POST /coalitions/{coa_id}/scores
# {
#    "id":6751201,
#    "coalition_id":334,
#    "scoreable_id":"None",
#    "scoreable_type":"None",
#    "coalitions_user_id":"None",
#    "calculation_id":"None",
#    "value":5,
#    "reason":"ngalzand won 5 coalition points",
#    "created_at":"2025-09-17T13:04:58.077Z",
#    "updated_at":"2025-09-17T13:04:58.077Z"
# }

# Example of DELETE /coalitions/{coa_id}/scores/{id}
# TODO

# Example of jackpots_<mod>.json entry:
# "5 Coalition points !": {
#     "color": "#FF0000",
#     "number": 3,
#     "message": "You won 5 coalition points!",
#     "function": "builtins.coa_points",
#     "args": {
#         "amount": 5,
#         "reason": "{login} won 5 coalition points"
#     }
# }

# Template args (available in "reason" field):
# - {login} - user login


# Intra Required Permissions: Advanced Staff
# This is completely stup*d btw...


def _sort_cursus_priority(cursus_users: dict) -> int:
    """Sort cursus_users by priority:
        1. Active cursus before ended cursus
        2. Main cursus before secondary cursus
    """
    if not isinstance(cursus_users, list):
        return []
    sorted_cursus = sorted(
        cursus_users,
        key=lambda cu: (
            cu.get('end_at') is not None,
            cu.get('cursus', {}).get('kind') != 'main'
        )
    )
    return sorted_cursus


def _get_primary_coalition(user_coalitions: list, blocs_data: list, user_data: dict) -> tuple[bool, str, dict]:
    cursus_list = _sort_cursus_priority(user_data.get('cursus_users', []))
    # For each cursus, check if there's a coalition in the blocs for that cursus
    for cursus in cursus_list:
        cursus_id = cursus.get('cursus', {}).get('id', None)
        if not cursus_id:
            continue
        for bloc in blocs_data:
            if str(bloc.get('cursus_id')) != str(cursus_id):
                continue
            # Get coalitions ids
            ids = [c.get('id', None) for c in bloc.get('coalitions', [])]
            # Found matching bloc, now find coalition in user's coalitions
            for coalition in user_coalitions:
                if coalition.get('id', None) in ids:
                    return True, "Primary coalition found.", coalition
    return False, "No coalition found for any of the user's cursus (active or inactive).", {}


def _get_user_primary_campus(user_data: dict) -> tuple[bool, str, dict]:
    """Fetch the primary campus of a user."""
    if not user_data.get('campus_users', None) or not isinstance(user_data['campus_users'], list):
        return False, "Campus users data not found/corrupted.", user_data
    primary_campus = None
    for campus in user_data['campus_users']:
        if campus.get('is_primary', False):
            primary_campus = campus
            break
    if not primary_campus:
        return False, "Primary campus not found.", {}
    return True, "Primary campus found.", primary_campus


def _get_coalition(api_intra: object, user: object) -> tuple[bool, str, dict]:
    """Fetch all required data then call _get_primary_coalition to get user's primary coalition."""
    # Getting user data
    success, msg, udata = api_intra.request('GET', f'/v2/users/{user.intra_id}')
    if not success:
        return False, f"Failed to fetch user data for {user.login}: {msg}", udata
    if not udata or not isinstance(udata, dict):
        return False, f"User data not found/corrupted for {user.login}.", udata
    
    # Extracting user's primary campus
    success, msg, primary_campus = _get_user_primary_campus(udata)
    campus_id = primary_campus.get('campus_id', None)
    if not campus_id:
        return False, f"Primary campus ID not found for {user.login}.", udata

    # Get user's coalitions
    success, msg, user_coalitions = api_intra.request('GET', f'/v2/users/{user.intra_id}/coalitions')
    if not success:
        return False, f"Failed to fetch coalitions data for {user.login}: {msg}", user_coalitions
    if not user_coalitions or not isinstance(user_coalitions, list) or len(user_coalitions) == 0:
        return False, f"Coalitions data not found/corrupted for {user.login}.", user_coalitions

    # Get v2/bloc with campus_id
    success, msg, blocs_data = api_intra.request('GET', f'/v2/blocs?filter[campus_id]={campus_id}')
    if not success:
        return False, f"Failed to fetch blocs data for {user.login}: {msg}", blocs_data
    if not blocs_data or not isinstance(blocs_data, list) or len(blocs_data) == 0:
        return False, f"Blocs data not found/corrupted for {user.login}.", blocs_data
    
    # Get Primary coalition from fetched data
    success, msg, data = _get_primary_coalition(user_coalitions, blocs_data, udata)
    if not success:
        return False, msg, data
    return True, "Primary coalition found.", data


def coa_points(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Add or remove points from a coalition.
    Args:   
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - amount: int, positive to add points, negative to remove points
            - reason: str, reason for the points change (optional)
    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - GET /v2/users/{login}/coalitions
    - POST /v2/coalitions/:coalition_id/scores
    """

    # Validate args
    try:
        amount = int(args.get('amount', 0))
    except (ValueError, TypeError):
        return False, "Amount must be a valid integer", {}
    if amount == 0:
        return False, "Amount cannot be zero, useless request", {}
    try:
        reason = str(args.get('reason', 'No reason provided'))
    except (ValueError, TypeError):
        return False, "Reason must be a string", {}

    # Search for template args in reason
    reason = reason.replace('{login}', user.login)

    # Get user's primary coalition
    success, msg, data = _get_coalition(api_intra, user)
    if not success:
        return False, msg, data
    
    coa_id = data.get('id', None)
    if not coa_id:
        return False, f"Coalition ID not found for user {user.login}.", data
    
    # Get coalition_user_id from user_id
    success, msg, data  = api_intra.request(method='GET', url=f'/v2/users/{user.intra_id}/coalitions_users', headers={})
    if not success or not isinstance(data, list) or not data or data[0].get('coalition_id', None) != coa_id:
        # coa points will be given but not linked to a specific coalition user
        coa_user_id = None
    else:
        coa_user_id = data[0].get('id', None)

    # Sending points change request
    payload = {
        "score[value]": amount,
        "score[reason]": reason,
        "score[coalitions_user_id]": coa_user_id
    }
    success, msg, n_data = api_intra.request(method='POST', url=f'/v2/coalitions/{coa_id}/scores', headers={}, data=payload)
    return success, msg, n_data


def cancel_coa_points(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Cancel a coalition points change by its ID.
    Args:   
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - data of the original coa_points call, must include:
                - id: int, ID of the coalition points change to cancel
                - coalition_id: int, ID of the coalition
    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - DELETE /v2/coalitions/:coalition_id/scores/:id (args: id, coalition_id)
    """

    # Validate args
    try:   
        int(args.get('id'))
    except (ValueError, TypeError):
        return False, "'id' argument must be a valid integer for cancel_coa_points.", args
    if int(args.get('id')) <= 0:
        return False, "'id' argument must be a positive integer for cancel_coa_points.", args
    try:   
        int(args.get('coalition_id'))
    except (ValueError, TypeError):
        return False, "'coalition_id' argument must be a valid integer for cancel_coa_points.", args
    if int(args.get('coalition_id')) <= 0:
        return False, "'coalition_id' argument must be a positive integer for cancel_coa_points.", args

    # Sending cancel request
    success, msg, data = api_intra.request(method='DELETE', url=f"/v2/coalitions/{args.get('coalition_id')}/scores/{args.get('id')}", headers={}, data={})

    if not success:
        return False, f"Failed to cancel coalition points change ID {args.get('id')}: {msg}", data
    return success, msg, data
