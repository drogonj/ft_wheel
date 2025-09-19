
def default(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Default function when landing on a sector.
    Returns: (bool, str) - (success, message)
    """
    return True, "Default jackpot completed successfully", {"message": "This is the default jackpot response"}

def cancel_default(api_intra: object, user: object, args: dict) -> tuple[bool, str, dict]:
    """Default function when cancelling a sector.
    Returns: (bool, str) - (success, message)
    """
    return True, "Default jackpot cancellation completed", {}
