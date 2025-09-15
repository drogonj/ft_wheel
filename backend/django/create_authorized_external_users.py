import os, django, json
from django.core.management.base import CommandError

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'luckywheel.settings')
django.setup()

from custom_auth.models import AuthorizedExternalUser

# Opening & extracting data/authorized_external_users.json
# Expect this format :
#{
#     "authorized_external_users" : [
#        "yoyostud",
#        "someone",
#        "anotherGuy"
#     ]
#}



try:
    with open('/backend/django/data/authorized_external_users.json', 'r') as json_file:
        data = json.load(json_file)
except FileNotFoundError:
    raise Exception("file \"./authorized_external_users.json\" does not exist")
except json.JSONDecodeError:
    raise Exception("Syntax error")

if not 'authorized_external_users' in data:
    raise Exception("Bad format: Missing section: \"authorized_external_users\"")

for login in data['authorized_external_users']:
    obj, created = AuthorizedExternalUser.objects.get_or_create(login=login)
    if created:
        print(f'AuthorizedExternalUser {login} created.')
    else:
        print(f'AuthorizedExternalUser {login} already exists.')