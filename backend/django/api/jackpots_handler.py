import importlib, logging

from api.intra import intra_api

logger = logging.getLogger('backend')

# Reminder of jackpot structure:
# "another one": {
#     "color": "#FFFFFF",
#     "number": 1,
#     "message": "You won something huge !",
#     "function": "builtins.another_one",
#     "args": {
#         "amount": 1000
#     }
# }

def _parse_function(jackpot):
    """
    Parse the function path from the jackpot configuration.
    Args:
        jackpot: dict - jackpot configuration
    Returns: list - [module, function]
    Raises: Exception if invalid

    Example for function: "builtins.add_points"
    'builtins/' must contain 'add_points.py'
    -> with a function called 'add_points'
    -> and a function called 'cancel_add_points' (for rollback)
    """

    function = jackpot['function']
    if not function.startswith('builtins.') and not function.startswith('mods.'):
        raise Exception("Function path must start with 'builtins.' or 'mods.'.")
    
    try:
        module_path, func_name = function.rsplit('.', 1)
    except ValueError:
        raise Exception("Function path must contain a module and a function name separated by a dot.")
    
    # Convert "builtins.default" -> "api.builtins.default"
    if module_path == 'builtins':
        full_module_path = f'api.builtins.{func_name}'
    elif module_path == 'mods':
        full_module_path = f'api.mods.{func_name}'
    else:
        raise Exception(f"Unsupported module path: {module_path}")

    try:
        module = importlib.import_module(full_module_path)
    except ImportError as e:
        raise Exception(f"Could not import module '{full_module_path}': {e}")

    if not hasattr(module, func_name):
        raise Exception(f"Module '{full_module_path}' does not have a function '{func_name}'.")
    
    func = getattr(module, func_name)
    if not callable(func):
        raise Exception(f"'{func_name}' in module '{full_module_path}' is not callable.")

    return func_name, func  # Return (func_name, func_object)


def handle_jackpots(user, jackpot):
    """
    Handle jackpots and choose the route.
    Called by wheel.views.spin

    Args:
        user: User instance
        jackpot: dict - jackpot configuration
    Returns: None
    """
    if not user or not jackpot:
        intra_api.intra_logger("ERROR", f"handle_jackpots called with invalid user or jackpot: user={user}, jackpot={jackpot}")
        logger.error(f"handle_jackpots called with invalid user or jackpot: user={user}, jackpot={jackpot}")
        return
    if not isinstance(jackpot, dict):
        intra_api.intra_logger("ERROR", f"handle_jackpots called with invalid jackpot type: {type(jackpot)}")
        logger.error(f"handle_jackpots called with invalid jackpot type: {type(jackpot)}")
        return
    if 'function' not in jackpot or not jackpot['function']:
        intra_api.intra_logger("INFO", f"Jackpot '{jackpot.get('label', 'unknown')}' has no function defined, skipping.")
        logger.info(f"Jackpot '{jackpot.get('label', 'unknown')}' has no function defined, skipping.")
        return
    
    try:
        func_name, func = _parse_function(jackpot)
        func(intra_api, user, jackpot.get('args', {}))

    except Exception as e:
        logger.error(f"Error in handle_jackpot '{jackpot.get('label', 'unknown')}': {e}")
        intra_api.intra_logger("ERROR", f"Error in handle_jackpot '{jackpot.get('label', 'unknown')}': {e}")
        return
