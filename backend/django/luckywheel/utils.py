import os, json, uuid

def docker_secret(secret_name: str):
    secret_file = os.path.join("/run/secrets", secret_name)
    try:
        with open(secret_file, "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Can't find '{secret_name}' in /run/secrets/.")
    except Exception as e:
        raise Exception(f"Can't read secret '{secret_name}': {e}")


def load_wheels(wheel_configs_dir: str):
    """Load wheel configurations and return format: {slug: {title, sectors, url}}

    Fields in sectors:
    - label <string> - identifier/name of the sector
    - color <string> (default: #FFFFFF) - sector color
    - number <int> (default: 1) - how many times this sector appears (jackpots format only)
    - message <string> (default: "You won... something?") - message to show when landed on this sector  
    - function <string> (default: builtins.default) - function to call when landed on this sector
    - args <dict> (default: {}) - arguments to pass to the function

    This will be used as the single WHEEL_CONFIGS source."""
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

        # Support both jackpots and sequence formats
        if 'sequence' in data and isinstance(data['sequence'], list):
            # Direct sequence format
            sectors = data['sequence']
        else:
            # Legacy jackpots format
            jackpots = data.get('jackpots', {})
            sectors = [
                {
                    "label": k,
                    "color": v.get("color") or "#FFFFFF",
                    "message": v.get("message") or "You won... something?",
                    "function": v.get("function") or "builtins.default",
                    "args": v.get("args") or {},
                }
                for k, v in jackpots.items()
                for _ in range(v.get('number', 1))
            ]

        wheels[slug_norm] = {'title': title, 'sectors': sectors, 'url': slug_norm}
    return wheels


def build_wheel_versions(wheel_configs: dict):
    """Generate a unique ID per wheel configuration."""
    rebuild_time = uuid.uuid4().hex[:12]
    versions = {}
    for slug in wheel_configs.keys():
        versions[slug] = f"{slug}_{rebuild_time}"
    return versions
