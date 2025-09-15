**\#\#\#\#\# Add a feature \#\#\#\#\#**

To add a feature, please make a new branch, then do a pull request.

---

#### Running the project

**\#\#\#\#\# Secrets \#\#\#\#\#**

Initialization: Just `mv .env-template .env` and fill it with your own credentials

* DJANGO_SECRET should be "strong" -> a string of 32 base64 characters is great

Execute `docker_secrets.sh` which create a `./secrets` folder, used by `docker-compose.yaml`.

In containers, docker secrets are mounted in `/run/secrets`.

**\#\#\#\#\# Setup \#\#\#\#\#**

* Django only wait for **HTTP** connections.
  * If running the project locally, set **HTTPS** to False, else Django's authentication redirections will not work properly.
* Django is listening on **port 8000**, do not forget to proxy pass to "<backend_ip>:8000", or set **HOSTNAME** to "localhost:8000" if you're running the project locally.
* On 42API, redirect route is `FULL_URL/login/oauth/callback`

---

**\#\#\#\#\# Superusers \#\#\#\#\#**

Can be found in `PROJECT/backend/data/superusers.json`

Example of `superusers.json` :

```
{
     "superusers" : {
        "bchevall" : {
            "testmode": true
        },
       "ngalzand" : {
            "testmode": true
       }
     }
}
```

`testmode`: Allow infinite spins, bypassing the 24h delay
->  DEPRECATED since /static/js/wheel.js line 216 "counter_distance > 0" condition added

Superusers can access `/admin` (maybe change this route is Prod.)

---

**\#\#\#\#\# External Authorized users \#\#\#\#\#**

ft_wheel is now configured to allow only 42 Mulhouse pisciners.

To modify those checks, see /backend/django/custom_auth/views.py line 89

We can still bypass this by adding an Authorized External user in the admin pannel or in `data/authorized_external_users.json`.

Example of `authorized_external_users.json`:

```
{
    "authorized_external_users" : [
        "yohan",
        "abel",
        "daribeir"
    ]
}
```


**\#\#\#\#\# Jackpots \#\#\#\#\#**

Can be found in `PROJECT/backend/data/wheel_configs/`

Project is configured for 4 Risk levels (safe, standard, risky, extreme)

Here is an example of `jackpots_(risk)` :

```
{
    "jackpots": {
        "TIG 2h": {
            "text": "TIG 2h",
            "color": "#d20f39",
            "number": 1,
            "message": "Tu as gagné 2h de TIG ! C'est l'heure de l'entraînement !",
            "api_route" : {
                "route": "/tig",
                "value": "2h"
            }
        },
        "+50Pts": {
            "text": "+50Pts",
            "color": "#40a02b",
            "number": 2,
            "message": "50 points de coalitions, WOW !",
            "api_route" : {
                "route": "/coalition",
                "value": 50
            }
        },
        "-50Pts": {
            "text": "-50Pts",
            "color": "#e64553",
            "number": 2,
            "message": "-50 points de coalitions, aïe...",
            "api_route" : {
                "route": "/coalition",
                "value": -50
            }
        },
        "1 Wallet": {
            "text": "1 Wallet",
            "color": "#df8e1d",
            "number": 1,
            "message": "1 Wallet ! Tu peux désormais t'acheter une TIG dans le shop !",
            "api_route" : {
                "route": "/wallet",
                "value": 1
            }
        },
        "Mystère": {
            "text": "Mystère",
            "color": "#179299",
            "number": 1,
            "message": "Demande à un tuteur/maître nageur ta récompense secrète (mode standard)",
            "api_route" : {
                "route": "/notify"
            }
        }
    }
}

```

**\#\#\#\#\# Project's structure \#\#\#\#\#**

```
.
├── backend
│   ├── django
│   │   ├── create_superusers.py         # Script to create initial superusers from data/superusers.json
│   │   ├── custom_auth                  # Django app for custom authentication (42 OAuth)
│   │   │   ├── admin.py                 # Django admin registration for custom_auth models
│   │   │   ├── apps.py                  # App configuration
│   │   │   ├── __init__.py
│   │   │   ├── migrations               # Database migrations for custom_auth
│   │   │   │   ├── __init__.py
│   │   │   │   └── __pycache__          # Compiled migration files
│   │   │   ├── models.py                # Custom user model and OAuth state management
│   │   │   ├── __pycache__              # Compiled Python files for this app
│   │   │   ├── templates
│   │   │   │   └── custom_auth
│   │   │   │       └── auth.html        # Template for OAuth login
│   │   │   ├── tests.py                 # Unit tests for custom_auth
│   │   │   ├── urls.py                  # URL routes for custom_auth
│   │   │   └── views.py                 # Views for login, callback, logout
|   |   |
│   │   ├── data                         # List of superusers and jackpots
|   |   |   ├── ...
│   │   ├── luckywheel                   # Main Django project settings and utilities
|   |   |   ├── ...
│   │   ├── manage.py                    # Django management script
│   │   ├── static                       # Static files (CSS, JS, images, sounds)
|   |   |   ├── ...
│   │   └── wheel                        # Django app for the wheel game logic
|   |   |   ├── ...
|   |
│   ├── Dockerfile                       # Docker build instructions for backend
│   ├── requirements.txt                 # Python dependencies
│   └── start.sh                         # Entrypoint script for backend container
|
├── docker-compose.yaml                  # Multi-service orchestration (nginx, backend, postgres)
├── docker_secrets.sh                    # Script to generate Docker secrets from .env
├── Makefile                             # Project management commands (build, up, down, clean, etc.)
|
├── postgres
│   ├── Dockerfile                       # Docker build for custom Postgres image
│   └── export_credentials.sh            # Script to export DB credentials as Docker secrets
```
