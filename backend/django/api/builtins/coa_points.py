
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


def coa_points(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Add or remove points from a coalition.
    Args:   
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - amount: int, positive to add points, negative to remove points
            - reason: str, reason for the points change (optional)
    """

    amount = int(args.get('amount', 0))
    if not isinstance(amount, int):
        raise ValueError("Amount must be an integer.")
    reason = args.get('reason', 'No reason provided')
    if not isinstance(reason, str):
        raise ValueError("Reason must be a string.")

    # Search for template args in reason
    reason = reason.replace('{login}', user.login)
    # Fetch user coalitions
    success, msg, data = api_intra.request('GET', f'/v2/users/{user.login}/coalitions')

    if not success:
        return False, f"Failed to fetch coalition data for {user.login}: {msg}", data
    if not data or len(data) == 0:
        return False, f"User {user.login} has no coalition data.", data

    # Get first coalition ID
    first_coalition = data[0]
    coa_id = first_coalition.get('id')

    if not coa_id:
        return False, f"Coalition ID not found for user {user.login}.", data

    payload = {
        "score[value]": amount,
        "score[reason]": reason
    }

    success, msg, n_data = api_intra.request(method='POST', url=f'/v2/coalitions/{coa_id}/scores', headers={}, data=payload)
    return success, msg, n_data


def cancel_coa_points(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    pass