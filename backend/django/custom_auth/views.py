from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
import logging, requests, json
from django.db import IntegrityError
from luckywheel.utils import docker_secret
from .models import OauthStateManager, OauthState, AuthorizedExternalUser

User = get_user_model()
OauthStateManager = OauthState.objects

oauth_secrets = {
	'oauth_uid': docker_secret("oauth_uid"),
	'oauth_secret': docker_secret("oauth_secret"),
	'oauth_redirect_uri': docker_secret("oauth_redirect_uri"),
}


logger = logging.getLogger('backend')



@require_http_methods(["GET"])
def login_view(request):

	# Use generated state if it exists, otherwise create a new one (see .models.OauthState)
	try:
		if not request.session.session_key:
			request.session.save()
		oauth_state = OauthStateManager.get_or_create_state(session_id=request.session.session_key)
	except IntegrityError as e:
		logger.error(f"IntegrityError while creating OauthState: {e}")
		return HttpResponseBadRequest('Failed to create OAuth state.')
	except Exception as e:
		logger.error(f"Unexpected error: {e}")
		return HttpResponseBadRequest('An unexpected error occurred.')
	
	return render(request, 'custom_auth/auth.html',
	{
		'oauth_redirect_uri': f"{oauth_secrets['oauth_redirect_uri']}&state={oauth_state.state}",
	})



@require_http_methods(["GET"])
def callback_view(request):
	code = request.GET.get('code')

	if request.GET.get('error'):
		return HttpResponseBadRequest('OAuth sent an error.')
	if not code:
		return HttpResponseBadRequest('OAuth code\'s missing.')

	try: 
		oauth_state = OauthStateManager.get_state(session_id=request.session.session_key)
		if not oauth_state:
			return redirect(f"{settings.WEBSITE_URL}/login?error=invalid_state")
	except Exception as e:
		logger.error(f"Error retrieving OAuth state: {e}")
		return redirect(f"{settings.WEBSITE_URL}/login?error=invalid_state")
	
	data = {
		'grant_type': 'authorization_code',
		'client_id': oauth_secrets['oauth_uid'],
		'client_secret': oauth_secrets['oauth_secret'],
		'code': code,
		'redirect_uri': f'{settings.WEBSITE_URL}/login/oauth/callback',
		'state': oauth_state.state,
	}


	try:
		response = requests.post('https://api.intra.42.fr/oauth/token', data=data)
		if response.status_code != 200:
			return HttpResponseBadRequest(f'Failed to retrieve token: {response.status_code} {response.text}')

		token_data = response.json()
		access_token = token_data.get('access_token')

		response = requests.get("https://api.intra.42.fr/v2/me", headers={'Authorization': f'Bearer {access_token}'})
		if response.status_code != 200:
			return HttpResponseBadRequest(f'Failed to retrieve user\'s data: {response.status_code} {response.text}')

		user_data = response.json()

		# If user's cursus isn't normal (for a pisciner) or campus.campus_id is not 48
		if user_data.get('cursus_users') is None or len(user_data.get('cursus_users')) != 1 or \
			user_data.get('cursus_users')[0].get('cursus_id', None) != 9 or (campus[0].get('id') if (campus := user_data.get('campus')) else None) != 48:

			# If user is in AuthorizedExternalUserManager, allow login
			if not AuthorizedExternalUser.objects.filter(login=user_data.get('login')).exists():
				oauth_state.delete()
				# If user is not in AuthorizedExternalUserManager, return bad request
				logger.warning(f"Unauthorized access attempt by user: {user_data.get('login')}")
				return redirect(f"{settings.WEBSITE_URL}/not_authorized")
			


		user, created = User.objects.get_or_create(
			login=user_data.get('login'),
		)

		if created:
			user.save()

		login(request, user, backend='django.contrib.auth.backends.ModelBackend')
	except requests.exceptions.RequestException as e:
		oauth_state.delete()
		return HttpResponseBadRequest(f'Request failed: {e}')
	except IntegrityError as e:
		oauth_state.delete()
		return HttpResponseBadRequest(f'Integrity error: {e}')
	except Exception as e:
		oauth_state.delete()
		logger.error(f"Unexpected error: {e}")
		return HttpResponseBadRequest('An unexpected error occurred.')

	oauth_state.delete()
	return redirect(f"{settings.WEBSITE_URL}/")



@login_required
@require_http_methods(["GET"])
def logout_view(request):
	if request.user:
		logout(request)
		return redirect(f"{settings.WEBSITE_URL}/")
	else:
		return HttpResponseBadRequest()



@login_required
@require_http_methods(["GET"])
def consent_view(request):
	if request.user:
		return render(request, 'custom_auth/consent.html')
	else:
		return HttpResponseBadRequest()
	


@login_required
@require_http_methods(["POST"])
def accept_consent_view(request):
	if request.user:
		request.user.has_consent = True
		request.user.save(update_fields=['has_consent'])
		return redirect(f"{settings.WEBSITE_URL}/")
	else:
		return HttpResponseBadRequest()
	


@require_http_methods(["GET"])
def not_authorized_view(request):
	# This view is used to display a message when the user is not authorized
	return render(request, 'custom_auth/not_authorized.html', status=403)