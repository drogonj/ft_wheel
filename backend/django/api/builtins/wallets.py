
# # # # # # # # # # # # # # # # #
# Give or take wallets to a user
# # # # # # # # # # # # # # # # #

# Example of POST /v2/transactions
# TODO

# Example of DELETE /v2/transactions/:id
# TODO

# Example of jackpots_<mod>.json entry:
# "10 Wallets !": {
#     "color": "#00FF00",
#     "number": 2,
#     "message": "You won 10 wallets!",
#     "function": "builtins.wallets",
#     "args": {
#         "amount": 10,
#         "reason": "{login} won 10 wallets"
#     }
# }

# Template args (available in "reason" field):
# - {login} - user login
# - {amount} - amount of wallets given or taken

# Intra Required Permissions: Transactions manager


def wallets(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Add or remove wallets from a user.
    Args:   
        api_intra: IntraAPI instance
        user: User object
        args: dict with keys:
            - amount: int, positive to add wallets, negative to remove wallets
            - reason: str, reason for the wallets change (optional)
    
    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - POST /v2/transactions
    """

    # Validate args
    try:
        amount = int(args.get('amount', 0))
    except (ValueError, TypeError):
        return False, "Amount must be a valid integer", {}
    if amount == 0:
        return False, "Amount cannot be zero, useless request ", {}
    try:
        reason = str(args.get('reason', 'No reason provided'))
    except (ValueError, TypeError):
        return False, "Reason must be a string", {}
    
    # Search for template args in reason
    reason = reason.replace('{login}', user.login).replace('{amount}', str(amount))

    payload = {
      "transaction[value]": amount,
      "transaction[user_id]": user.intra_id,
      "transaction[transactable_type]": "ft_wheel",
      "transaction[reason]": reason 
    }

    success, msg, data = api_intra.request(method='POST', url='/v2/transactions', headers={}, data=payload)
    return success, msg, data


def cancel_wallets(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Cancel a wallets transaction.
    Args:   
        api_intra: IntraAPI instance
        user: User object
        args: data of the original wallets call, must include:
            - id: id of the transaction to cancel
    
    Returns:
        tuple: (success: bool, message: str, data: dict)

    used api endpoints:
    - DELETE /v2/transactions/:id
    """
    
    # Validate args
    try:
        transaction_id = int(args.get('id', 0))
    except (ValueError, TypeError):
        return False, "transaction_id must be a valid integer", {}
    if transaction_id <= 0:
        return False, "Invalid or missing transaction ID", {}

    success, msg, data = api_intra.request(method='DELETE', url=f'/v2/transactions/{transaction_id}', headers={})
    return success, msg, data
