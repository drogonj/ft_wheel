
# # # # # # # # # # # #
# Give a TIG to a user
# # # # # # # # # # # #

# Example of POST /v2/users/:user_id/closes
# TODO

# Example of POST /v2/community_services
# {
#   "id": 3,
#   "duration": 14400,
#   "schedule_at": "2017-11-27T06:00:00.000Z",
#   "occupation": "Regarder Shrek, en entier, avec Mathieu Trentin",
#   "state": "schedule",
#   "created_at": "2017-11-22T13:43:32.216Z",
#   "updated_at": "2017-11-22T13:43:32.216Z",
#   "close": {
#     "id": 2,
#     "reason": "Connecticut giants",
#     "state": "unclose",
#     "created_at": "2017-11-22T13:42:20.888Z",
#     "updated_at": "2017-11-22T13:42:20.987Z"
#   }
# }

# Example of jackpots_<mod>.json entry:
# "TIG !": {
#     "color": "#0000FF",
#     "number": 1,
#     "message": "You won the TIG group!",
#     "function": "builtins.tig",
#     "args": {
#         "duration": "2h",                     <- Must be one of ["2h", "4h", "8h"] (default: "2h")
#         "reason": "{login} won the TIG group" <- Reason for the TIG (default: "No reason provided")
#         "occupation": "Clean the keyboards",  <- Occupation for the TIG (default: "undefined")
#       }
#     }
# }

# Template args (available in "reason" field):
# - {login} - user login
# - {duration} - duration of the TIG

# Intra Required Permissions: Basic Staff / Advanced Staff (For DELETE permissions)

def tig(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Give a TIG to a user.
    Args:
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - duration: str, duration of the TIG (must be one of ["2h", "4h", "8h"]) (default: "2h")
            - reason: str, reason for assigning the TIG (default: "No reason provided")
            - occupation: str, occupation for the TIG (default: "undefined")
    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - POST /v2/users/:user_id/closes
    - POST /v2/community_services
    """

    # Validate args
    try:
        duration = str(args.get('duration', '2h'))
    except (ValueError, TypeError):
        return False, "Duration must be a string", {}
    if duration not in ["2h", "4h", "8h"]:
        return False, "Duration must be one of ['2h', '4h', '8h']", {}
    try:
        reason = str(args.get('reason', 'No reason provided'))
    except (ValueError, TypeError):
        return False, "Reason must be a string", {}
    try:
        occupation = str(args.get('occupation', 'undefined'))
    except (ValueError, TypeError):
        return False, "Occupation must be a string", {}

    # Convert duration in seconds
    duration_formatted = {"2h": 7200, "4h": 14400, "8h": 28800}[duration]

    # Search for template args in reason
    reason = reason.replace('{login}', user.login).replace('{duration}', duration)

    # Create the Closes
    payload = {
      "close[user_id]": user.intra_id,
      "close[closer_id]": user.intra_id,
      "close[kind]": "other",
      "close[reason]": "ft_wheel - " + reason,
      "close[community_services_attributes]": [{"[duration]": str(duration_formatted)}]
    }
    success, msg, data = api_intra.request(method='POST', url=f'/v2/users/{user.intra_id}/closes', headers={}, data=payload)
    if not success:
        return False, f"Error POSTING to /v2/users/{user.intra_id}/closes: {msg}", data
    
    # Get Close ID
    try:
        close_id = int(data.get('id', 0))
    except (ValueError, TypeError):
        return False, "Error retrieving close ID from response", data
    if close_id <= 0:
        return False, "Invalid close ID received", data
    
    # Create the Community Service
    payload = {
      "community_service[close_id]": close_id,
      "community_service[duration]" : str(duration_formatted),
      "community_service[occupation]" : occupation,
      "community_service[tiger_id]" : user.intra_id
    }
    success, msg, data = api_intra.request(method='POST', url='/v2/community_services', headers={}, data=payload)
    if not success:
        return False, f"Error POSTING to /v2/community_services: {msg}", data
    return success, msg, data



def cancel_tig(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Cancel a TIG from a user by closing the associated close.
    Args:
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - id: int, ID of the community service to cancel (required)
            - close['id']: int, ID of the close to cancel (required)
    Returns:
        tuple: (success: bool, message: str, data: dict)
    used api endpoints:
    - DELETE /v2/closes/:id
    - DELETE /v2/community_services/:id
    """

    # Validate args
    try:
        community_service_id = int(args.get('id', 0))
    except (ValueError, TypeError):
        return False, "community_service_id must be a valid integer", {}
    if community_service_id <= 0:
        return False, "Invalid or missing community_service ID", {}
    if 'close' not in args or 'id' not in args['close']:
        return False, "Missing 'close[id]' argument", {}
    try:
        close_id = int(args.get('close', {}).get('id', 0))
    except (ValueError, TypeError):
        return False, "close_id must be a valid integer", {}
    if close_id <= 0:
        return False, "Invalid or missing close ID", {}
    
    # Delete Community Service
    success, msg, cs_data = api_intra.request(method='DELETE', url=f'/v2/community_services/{community_service_id}', headers={})
    if not success:
        return False, f"Error DELETEing /v2/community_services/{community_service_id}: {msg}", cs_data

    # Delete Close
    success, msg, cl_data = api_intra.request(method='DELETE', url=f'/v2/closes/{close_id}', headers={})
    if not success:
        return False, f"Error DELETEing /v2/closes/{close_id}: {msg}", cl_data

    return True, "Successfully cancelled TIG", {"cs": cs_data, "cl": cl_data}