from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseForbidden
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
import logging, requests, json
from django.db import IntegrityError
from ft_wheel.utils import docker_secret
from .models import OauthStateManager, OauthState

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
	
	return render(request, 'users/auth.html',
	{
		'oauth_redirect_uri': f"{oauth_secrets['oauth_redirect_uri']}&state={oauth_state.state}",
	})



@require_http_methods(["GET"])
def callback_view(request):
	code = request.GET.get('code')
	state_param = request.GET.get('state')

	if request.GET.get('error'):
		return HttpResponseBadRequest('OAuth sent an error.')
	if not code:
		return HttpResponseBadRequest('OAuth code\'s missing.')

	try: 
		oauth_state = OauthStateManager.get_state(session_id=request.session.session_key)
		if not oauth_state:
			return redirect(f"{settings.WEBSITE_URL}/login?error=invalid_state")
		# Strictly validate 'state' returned by OAuth provider against stored value
		if not state_param or state_param != oauth_state.state:
			try:
				oauth_state.delete()
			except Exception:
				pass
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

		user, created = User.objects.get_or_create(
			login=user_data.get('login'),
		)

		if created:
			user.save()

		# Rotate the session to prevent fixation, then log the user in
		try:
			request.session.cycle_key()
		except Exception:
			pass
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
		return render(request, 'users/consent.html')
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
	