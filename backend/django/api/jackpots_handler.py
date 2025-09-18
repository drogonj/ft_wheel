import importlib, logging, queue, os
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

from api.intra import intra_api

# ---------------------
# non-blocking logging setup
# ---------------------
LOG_DIR = "/var/log/ft_wheel"
os.makedirs(LOG_DIR, exist_ok=True)

log_queue = queue.Queue(-1)  # file-backed queue handled by QueueListener thread

file_info_path = os.path.join(LOG_DIR, "jackpot_info.log")
file_error_path = os.path.join(LOG_DIR, "jackpot_error.log")

file_handler_info = RotatingFileHandler(file_info_path, maxBytes=10 * 1024 * 1024, backupCount=3)
file_handler_info.setLevel(logging.INFO)
file_handler_info.addFilter(lambda record: record.levelno <= logging.INFO)
file_handler_error = RotatingFileHandler(file_error_path, maxBytes=10 * 1024 * 1024, backupCount=3)
file_handler_error.setLevel(logging.ERROR)
file_handler_error.addFilter(lambda record: record.levelno >= logging.ERROR)


formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler_info.setFormatter(formatter)
file_handler_error.setFormatter(formatter)

# QueueListener will consume log_queue and write to handlers on a background thread.
_queue_listener = QueueListener(log_queue, file_handler_info, file_handler_error)
_queue_listener.start()

logger = logging.getLogger("intra")
logger.setLevel(logging.INFO)
logger.addHandler(QueueHandler(log_queue))


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
    
    # module muste have a cancel_<func_name> function as well
    cancel_func_name = f'cancel_{func_name}'
    if not hasattr(module, cancel_func_name):
        raise Exception(f"Module '{full_module_path}' does not have a cancel function '{cancel_func_name}'.")

    func = getattr(module, func_name)
    if not callable(func):
        raise Exception(f"'{func_name}' in module '{full_module_path}' is not callable.")

    return func_name, func  # Return (func_name, func_object)


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
    if 'function' not in jackpot or not jackpot['function']:
        error_msg = f"Jackpot '{jackpot.get('label', 'unknown')}' has no function defined, skipping."
        logger.info(error_msg)
        return False, error_msg, {}

    try:
        func_name, func = _parse_function(jackpot)
        success, msg, data = func(intra_api, user, jackpot.get('args', {}))

        if not success:
            #handle failure (if failure come from intra api, response contains the error details)
            logger.error(f"{msg}\n{str(data)}")
            return False, msg, data
        logger.info(f"{msg}\n{str(data)}")
        return True, msg, data
    except Exception as e:
        logger.error(f"Unexpected error in handle_jackpot '{jackpot.get('label', 'unknown')}': {e}")
        return False, str(e), {}
