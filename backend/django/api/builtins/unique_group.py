from api.models import UniqueGroupOwner

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Give or take a unique group to a user
# 1 user only can have this title, if someone else has it, it is removed from him/her
#
# The uniqueness of the group owner is effective only on this instance of ft_wheel
# Externals users who have the same group on Intra will not be affected
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# Example of GET /v2/users/:user_id/groups_users 
# TODO

# Example of POST /v2/groups_users
# {
#   "id": 27422,
#   "group": {
#     "id": 478,
#     "name": "Blessed  🍀"
#   },
#   "user_id": 117633
# }

# Example of DELETE /v2/groups_users/:id
# TODO

# Example of jackpots_<mod>.json entry:
# "Unique Group !": {
#     "color": "#FFD700",
#     "number": 2,
#     "message": "You won the unique group '{group_name}'!",
#     "function": "builtins.unique_group",
#     "args": {
#         "group_id": 561, <- ID of the existing group to give (must be unique)
# }

# Intra Required Permissions: Advanced Tutor


def unique_group(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Give the unique group to a user, removing it from any other user who has it.
    Args:
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - group_id: int, ID of the group to give (must be unique)

    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - GET /v2/users/:user_id/groups_users
    - POST /v2/groups_users
    - DELETE /v2/groups_users/:id
    """

    # Args validation
    try:
        group_id = int(args.get('group_id', 0))
    except (ValueError, TypeError):
        return False, "group_id must be a valid integer", {}
        
    if group_id <= 0:
        return False, "Invalid or missing group ID", {}

    # Get current owner of the unique group from UniqueGroupOwner table
    current_owner = UniqueGroupOwner.objects.filter(group_id=group_id).first()
    if current_owner:
        current_owner_id = current_owner.owner_user_id
    else:
        current_owner_id = None

    if current_owner_id:
        # If the user already has the group, do nothing
        if current_owner_id == user.id:
            return True, "User already has the unique group", {}
        
        # Be sure the current owner still has the group
        success, msg, data = api_intra.request(method='GET', url=f'/v2/users/{current_owner_id}/groups_users', headers={})
        if not success:
            return False, f"Error checking current group owner: {msg}", {}
        has_group = any(gu['group_id'] == group_id for gu in data)

        # If user still has the group, remove it
        if has_group:
            # Remove the group from the current owner
            gu_id = next(gu['id'] for gu in data if gu['group_id'] == group_id)
            success, msg, data = api_intra.request(method='DELETE', url=f'/v2/groups_users/{gu_id}', headers={})
            if not success:
                return False, f"Error removing group from current owner: {msg}", data
            
    # Give the group to the new user
    payload = {
        "groups_user[group_id]": group_id,
        "groups_user[user_id]": user.intra_id
    }
    success, msg, data = api_intra.request(method='POST', url='/v2/groups_users', headers={}, data=payload)
    if not success:
        return False, f"Error giving group to user: {msg}", data
    
    # Set user as the new owner in UniqueGroupOwner table
    UniqueGroupOwner.objects.update_or_create(
        group_id=group_id,
        defaults={
            'owner_user_id': user.id,
            'previous_user_id': current_owner_id
        }
    )
    return success, msg, data


# Only delete the group_users if the user have one linked to the specified group
# Do not restore the group to the previous owner
def cancel_unique_group(api_intra: object, user: object, args: dict):
    """Cancel a unique group from a user.
    Args:
        api_intra: IntraAPI instance
        user: User object
        args: dict containing the response from POST /v2/groups_users:
            - id: int, ID of the groups_users record (27422 in example)
            - group: dict with 'id' key (478 in example)
            - user_id: int, user ID

    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - GET /v2/users/:user_id/groups_users
    - DELETE /v2/groups_users/:id
    """

    # Args validation - extract group_users_id from 'id' field
    try:
        group_users_id = int(args.get('id', 0))  # 27422
    except (ValueError, TypeError):
        return False, "id must be a valid integer", {}
    if group_users_id <= 0:
        return False, "Invalid or missing groups_users ID", {}
    
    # Extract group_id from nested 'group.id' field
    if 'group' in args and isinstance(args['group'], dict) and 'id' in args['group']:
        try:
            group_id = int(args['group']['id'])  # 478
        except (ValueError, TypeError):
            return False, "group['id'] must be a valid integer", {}
        if group_id <= 0:
            return False, "Invalid or missing group ID", {}
    else:
        return False, "Missing 'group[id]' argument", {}

    # Ensure the user still has the group
    success, msg, data = api_intra.request(method='GET', url=f'/v2/users/{user.intra_id}/groups_users', headers={})
    if not success:
        return False, f"Error checking user's groups: {msg}", {}
        
    # Check if user has this specific group_users record
    has_group = any(gu['id'] == group_users_id and gu.get('group', {}).get('id') == group_id for gu in data)
    if not has_group:
        return True, f"User does not have the group_users record {group_users_id}", {}

    # Remove the group from the user
    success, msg, delete_data = api_intra.request(method='DELETE', url=f'/v2/groups_users/{group_users_id}', headers={})
    if not success:
        return False, f"Error removing groups_users {group_users_id}: {msg}", delete_data
    
    # Clean up the ownership record
    try:
        ownership_deleted = UniqueGroupOwner.objects.filter(group_id=group_id, owner_user_id=user.id).delete()
        delete_data['ownership_cleanup'] = f"Deleted {ownership_deleted[0]} ownership records"
    except Exception as e:
        # Non-fatal, but log it
        delete_data['cleanup_warning'] = f"Could not clean ownership record: {e}"
    
    return True, f"Successfully removed group {group_id} (groups_users {group_users_id}) from user", delete_data