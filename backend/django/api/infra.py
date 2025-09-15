import logging, requests, json

from luckywheel.utils import docker_secret
from .intra import intra_api

# Valid api_route in jackpot (see README.md)
#
#"api_route": {
#    "route": "/wallet",
#    "value": 2
#}

# Handled routes:
# - /coalition
#       args: value (int) - -2000 to 2000
# - /tig
#       args: value (str) - "2h", "4h", "8h"
# - /wallet
#       args: value (int) - 0 to 50
# - /notify (set to default - Send a message in kmbot channel)



# Examples of request:
#
# --url--:
# POST https://webhook.42mulhouse.fr/h/campus
#
# --Headers--:
# Content-Type: application/json
#
# --Payloads--:
# -> TIG:
# {
#     "type": "ft_wheel",
#     "action": "tig",
#     "login": "user42",
#     "amount": "1h",
#     "reason": "A very bad karma"
#     "hash": "your_infra_token"
#
# }
#
# -> coalition points:
# {
#     "type": "ft_wheel",
#     "action": "coalition",
#     "coa": "technicians",
#     "amount": 100,
#     "reason": "user42 seems lucky today"
#     "hash": "your_infra_token"
# }
#
# -> wallets:
# {
#     "type": "ft_wheel",
#     "action": "wallet",
#     "login": "user42",
#     "amount": 10,
#     "reason": "Jackpot for user42"
#     "hash": "your_infra_token"
# }
#
# -> specials jackpots:
# {
#     "type": "ft_wheel",
#     "action": "notification",
#     "text": "user42 won a Sandwich"
#     "hash": "your_infra_token"
# }


logger = logging.getLogger('api.infra')

infra_token = docker_secret('infra_token')



def handle_jackpots(user, jackpot):
    """
    Handle jackpots and choose the route.
    Called by wheel.views.spin
    """
    if not user or not jackpot:
        return False

    if jackpot.get('api_route', False):
        #Check if jackpot['api_route']['route'] and jackpot['api_route']['value'] exists
        if not isinstance(jackpot['api_route'], dict) or 'route' not in jackpot['api_route'] or 'value' not in jackpot['api_route']:
            return notify(user, jackpot=jackpot)

        if not jackpot['api_route']['route']:
            logger.error(
                f"Jackpot {jackpot} has no api_route or value."
                f"-> api.infra.handle_jackpots with args (user={user.login}, jackpot={jackpot}"
            )
            return notify(user, jackpot=jackpot)

        match jackpot['api_route']['route']:
            case '/coalition':
                return coalition(user, jackpot['api_route']['value'])
            case '/tig':
                return tig(user, jackpot['api_route']['value'])
            case '/wallet':
                return wallet(user, jackpot['api_route']['value'])
            case _:
                return notify(user, jackpot=jackpot)
    else:
        return notify(user, jackpot)



def tig(user, value):
    """
    Handle TIG jackpot requests.
    """

    # Small protections to avoid bad requests
    if value not in ["2h", "4h", "8h"]:
        logger.error(
            f"Invalid TIG value: {value} for user {user.login}."
            f"-> api.infra.tig with args (user={user.login}, value={value}"
        )
        return False

    payload = {
        "type": "ft_wheel",
        "action": "tig",
        "login": user.login,
        "amount": value,
        "reason": f"A very bad karma",
    }
    return infra_post(payload)    



def coalition(user, value):
    """
    Handle Coalition jackpot requests.
    """

    # Small protections to avoid bad requests
    if value < -2000 or value > 2000:
        logger.error(
            f"Invalid coalition value: {value} for user {user.login}."
            f"-> api.infra.coalition with args (user={user.login}, value={value}"
        )
        return False

    user_coa = intra_api.get_user_coa(user.login, fields=['id', 'name'])
    if not user_coa:
        logger.error(
            f"User {user.login} has no coalitions."
            f"-> api.infra.coalition with args (user={user.login}, value={value}"
        )
        return False
    if not user_coa[0].get('name'):
        logger.error(
            f"User {user.login} has no coalition name."
            f"-> api.infra.coalition with args (user={user.login}, value={value}"
        )
        return False

    # Users can have multiple coalitions, but we only use the first one
    # Wich should not be a problem in Piscines and "normals" accounts
    payload = {
        "type": "ft_wheel",
        "action": "coalition",
        "coa": user_coa[0]['name'].lower(),
        "amount": value,
        "reason": f"{user.login} seems lucky today" if value > 0 else f"Not a lucky day for {user.login}",
    }
    return infra_post(payload)



def wallet(user, value):
    """
    Handle Wallet jackpot requests.
    """

    # Small protections to avoid bad requests
    if value < 0 or value > 50:
        logger.error(
            f"Invalid wallet value: {value} for user {user.login}."
            f"-> api.infra.wallet with args (user={user.login}, value={value}"
        )
        return False
    
    payload = {
        "type": "ft_wheel",
        "action": "wallet",
        "login": user.login,
        "amount": value,
        "reason": f"Jackpot for {user.login}" if value > 0 else f"Bad luck for {user.login}",
    }
    return infra_post(payload)



def notify(user, jackpot):
    """
    Just send a message in kmbot channel for specials jackpots
    """
    if not jackpot['text']:
        logger.error(
            f"Jackpot {jackpot} has no text to notify."
            f"-> api.infra.notify with args (user={user.login}, jackpot={jackpot}"
        )
        return False

    payload = {
        "type": "ft_wheel",
        "action": "notification",
        "text": f"---\n{user.login} won {jackpot['text']}\n---",
    }
    return infra_post(payload)



def infra_post(payload):
    """
    Post data to the infra API at http://10.51.1.18:8080/h/campus
        route (str): The route to post to.
        payload (dict): The payload to post.
    Returns:
        dict: The response from the API.
    """

    url = f"http://10.51.1.18:8080/h/campus"
    headers = {'Content-Type': 'application/json'}

    #Add "hash" to payload
    if 'hash' not in payload:
        payload['hash'] = infra_token

    print(json.dumps(payload, indent=4))

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except requests.RequestException as e:
        logger.error(f"ERROR: {e}")
        return False