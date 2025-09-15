import os, json, random

def docker_secret(secret_name):
    secret_file = os.path.join("/run/secrets", secret_name)
    try:
        with open(secret_file, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Can't find '{secret_name}' in /run/secrets/.")
    except Exception as e:
        raise Exception(f"Can't read secret '{secret_name}': {e}")


def colors_are_similar(color1, color2):
    def hex_to_rgb(hex_color):
        return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
    
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    # Distance euclidienne entre les couleurs
    distance = sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)) ** 0.5
    return distance < 100 


def init_jackpots(wheel_configs_dir, wheel_configs, balance: bool = True):
    for config in wheel_configs.keys():
        jackpots_file = os.path.join(wheel_configs_dir, f"jackpots_{config}.json")
        try:
            with open(jackpots_file, 'r') as json_file:
                jackpots_data = json.load(json_file)
        except FileNotFoundError:
            raise Exception(f"File \"jackpots_{config}.json\" not found in {wheel_configs_dir}")
        except json.JSONDecodeError:
            raise Exception(f"Syntax error in \"jackpots_{config}.json\"")
        except Exception as e:
            raise Exception(f"Error reading \"jackpots_{config}.json\": {e}")
        # Support two formats: legacy {"jackpots": {...}} and new {"sequence": [...]}
        if 'sequence' in jackpots_data and isinstance(jackpots_data['sequence'], list):
            # Use sequence directly (already expanded & ordered) - trust structure
            wheel_configs[config] = jackpots_data['sequence']
        else:
            wheel_configs[config] = [
                {
                    "color": value.get("color", None),
                    "text": value.get("text", None),
                    "label": key,
                    "message": value.get("message", None),
                    "api_route": value.get("api_route", None)
                }
                for key, value in jackpots_data['jackpots'].items()
                for _ in range(value.get("number", 1))
            ]

            if balance:
                try:
                    from luckywheel.utils import smart_balance_wheel  # noqa
                    wheel_configs[config] = smart_balance_wheel(wheel_configs[config])
                except Exception:
                    attempts = 0
                    while attempts < 20:
                        random.shuffle(wheel_configs[config])
                        has_bad_neighbors = any(
                            (wheel_configs[config][i]['label'] == wheel_configs[config][i + 1]['label'] or
                             colors_are_similar(wheel_configs[config][i]['color'], wheel_configs[config][i + 1]['color']))
                            for i in range(len(wheel_configs[config]) - 1)
                        )
                        if not has_bad_neighbors:
                            break
                        attempts += 1

    return wheel_configs


def load_wheels(wheel_configs_dir: str, balance: bool = True):
    wheels = {}
    if not os.path.isdir(wheel_configs_dir):
        return wheels
    for fname in os.listdir(wheel_configs_dir):
        if not fname.startswith('jackpots_') or not fname.endswith('.json'):
            continue
        path = os.path.join(wheel_configs_dir, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        slug_raw = data.get('url') or data.get('slug') or fname[len('jackpots_'):-5]
        slug_norm = slug_raw.lower().replace(' ', '_')
        title = data.get('title') or slug_norm.capitalize()
        if 'sequence' in data and isinstance(data['sequence'], list):
            sectors = data['sequence']
        else:
            jackpots = data.get('jackpots', {})
            sectors = [
                {
                    "color": v.get("color"),
                    "text": v.get("text"),
                    "label": k,
                    "message": v.get("message"),
                    "api_route": v.get("api_route")
                }
                for k, v in jackpots.items()
                for _ in range(v.get('number', 1))
            ]
            if balance:
                try:
                    from luckywheel.utils import smart_balance_wheel  # noqa
                    sectors = smart_balance_wheel(sectors)
                except Exception:
                    pass
        wheels[slug_norm] = {'title': title, 'sectors': sectors, 'url': slug_norm}
    return wheels
    