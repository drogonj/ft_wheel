import importlib, logging, queue, os
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

from api.intra import intra_api
from .jackpot_logging import logger

def _parse_function(function):
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
    
    # module muste have a cancel_<func_name> function as well
    cancel_func_name = f'cancel_{func_name}'
    if not hasattr(module, cancel_func_name):
        raise Exception(f"Module '{full_module_path}' does not have a cancel function '{cancel_func_name}'.")

    func = getattr(module, func_name)
    if not callable(func):
        raise Exception(f"'{func_name}' in module '{full_module_path}' is not callable.")

    cancel_func = getattr(module, cancel_func_name)
    if not callable(cancel_func):
        raise Exception(f"'{cancel_func_name}' in module '{full_module_path}' is not callable.")

    return func, cancel_func  # Return functions objects



def handle_jackpots(user, jackpot) -> tuple[bool, str, dict]:
    """
    Handle jackpots and choose the route.
    Called by wheel.views.spin

    Args:
        user: User instance
        jackpot: dict - jackpot configuration
    Returns: None
    """
    if not user or not jackpot:
        error_msg = f"handle_jackpots called with invalid user or jackpot: user={user}, jackpot={jackpot}"
        logger.error(error_msg)
        return False, error_msg, {}
    if not isinstance(jackpot, dict):
        error_msg = f"Jackpot is not a dictionary: {jackpot}"
        logger.error(error_msg)
        return False, error_msg, {}
    if 'function' not in jackpot or not jackpot['function'] or not isinstance(jackpot['function'], str):
        error_msg = f"Jackpot '{jackpot.get('label', 'unknown')}' has no function defined, skipping."
        logger.info(error_msg)
        return False, error_msg, {}

    try:
        func, cancel_func = _parse_function(jackpot['function'])
        success, msg, data = func(intra_api, user, jackpot.get('args', {}))

        if not success:
            #handle failure (if failure come from intra api, response contains the error details)
            logger.error(f"{msg}\n{str(data)}")
            return False, msg, data
        logger.info(f"{msg}\n{str(data)}")
        return True, msg, data
    except Exception as e:
        logger.error(f"Error in handle_jackpot '{jackpot.get('label', 'unknown')}': {e}")
        return False, str(e), {}



def cancel_jackpot(user: object, function_name: str, r_data: dict) -> tuple[bool, str, dict]:
    """
    Cancel a jackpot by calling its cancel function.
    Called by administration.history_views.cancel_history_api

    Args:
        user: User instance
        jackpot: dict - jackpot configuration
    Returns: (bool, str, dict) - (success, message, r_data)
    """
    if not user or not function_name:
        error_msg = f"cancel_jackpot called with invalid user or function_name: user={user}, function_name={function_name}"
        logger.error(error_msg)
        return False, error_msg, {}
    if not isinstance(function_name, str):
        error_msg = f"Function name is not a string: {function_name}"
        logger.error(error_msg)
        return False, error_msg, {}
    if not isinstance(r_data, dict):
        error_msg = f"Data is not a dictionary: {r_data}"
        logger.error(error_msg)
        return False, error_msg, {}

    try:
        func, cancel_func = _parse_function(function_name)
        success, msg, data = cancel_func(intra_api, user, r_data)

        if not success:
            #handle failure (if failure come from intra api, response contains the error details)
            logger.error(f"Cancellation failed: '{function_name} {user.login} {r_data}' -> {msg}\n{str(data)}")
            return False, msg, data
        logger.info(f"Cancellation succeeded: '{function_name} {user.login} {r_data}' -> {msg}\n{str(data)}")
        return True, msg, data
    except Exception as e:
        logger.error(f"Error in cancel_jackpot '{function_name} {user.login} {r_data}': {e}")
        return False, str(e), {}