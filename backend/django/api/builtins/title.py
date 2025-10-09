# # # # # # # # # # # # # # # # # 
# Give a, existing title to a user
# # # # # # # # # # # # # # # # # 

# Example of POST /v2/titles_users
# {
#   "titles_user[title_id]": 2589,
#   "titles_user[user_id]": 117200
# }

# Example of DELETE /v2/titles_users/:id
# TODO

# Example of jackpots_<mod>.json entry:
# "Title !": {
#     "color": "#800080",
#     "number": 4,
#     "message": "You won the title '{title_name}'!",
#     "function": "builtins.title",
#     "args": {
#         "title_id": 123, <- ID of the existing title to give
#     }
# }

# Intra Required Permissions: Advanced Tutor

def title(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Give a title to a user.
    Args:
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - title_id: int, ID of the title to give

    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - POST /v2/titles_users
    """

    # Validate args
    try:
        title_id = int(args.get('title_id', 0))
    except (ValueError, TypeError):
        return False, "title_id must be a valid integer", {}
    if title_id <= 0:
        return False, "Invalid or missing title ID", {}
    
    # Give the title to the user
    payload = {
      "titles_user[title_id]": title_id,
      "titles_user[user_id]": user.intra_id
    }
    success, msg, data = api_intra.request(method='POST', url='/v2/titles_users', headers={}, data=payload)
    return success, msg, data



def cancel_title(api_intra: object, user: object, args: dict):
    """Cancel a title from a user.
    Args:
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - title_id: int, ID of the title to cancel
    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - DELETE /v2/titles_users/:id
    """

    # Validate args
    try:
        id = int(args.get('id', 0))
    except (ValueError, TypeError):
        return False, "id must be a valid integer", {}
    if id <= 0:
        return False, "Invalid or missing titles_user ID", {}
    
    success, msg, data = api_intra.request(method='DELETE', url=f'/v2/titles_users/{id}', headers={})
    return success, msg, data