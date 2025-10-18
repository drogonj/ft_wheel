import os, django, json
from django.core.management.base import CommandError
from django.contrib.auth import get_user_model

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ft_wheel.settings')
django.setup()
User = get_user_model()

# Opening & extracting data/superusers.json
# Expect this format :
# {
#      "superusers" : {
#        "your_login" : {
#           "intra_id": your_intra_id,
#           "testmode": true,
#           "role": "admin"
#        }
#      }
# }
try:
    with open('/backend/django/data/superusers.json', 'r') as json_file:
        data = json.load(json_file)
except FileNotFoundError:
    raise Exception("file \"./superusers.json\" does not exist")
except json.JSONDecodeError:
    raise Exception("Syntax error")


if not 'superusers' in data:
    raise Exception("Bad format: Missing section: \"superusers\"")

for login, details in data['superusers'].items():
    testmode = details.get('testmode', False)
    intra_id = details.get('intra_id', None)
    role = details.get('role', 'moderator')  # Default role is 'moderator'
    if not User.objects.filter(login=login).exists():
        User.objects.create_superuser(
            login=login,
            intra_id=intra_id,
            test_mode=testmode,
            role=role
        )
        print(f'Superuser {login} created.')
    else:
        print(f'Superuser {login} already exists.')