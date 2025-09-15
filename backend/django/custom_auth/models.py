from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets, base64

# Create your models here.
class AccountManager(BaseUserManager):
    def create_user(self, login, **extra_fields):
        user = self.model(login=login, **extra_fields)
        user.save()
        return user

    def create_superuser(self, login, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(login, **extra_fields)



class Account(AbstractBaseUser):
    date_joined = models.DateTimeField(verbose_name="date joined", auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="last login", auto_now=True)

    login = models.CharField(max_length=20, unique=True, blank=False, null=False)

    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    test_mode = models.BooleanField(default=False)

    has_consent = models.BooleanField(default=False)

    last_spin = models.DateTimeField(
        null=True,
        blank=True,
        default=timezone.now() - timedelta(days=1)
    )

    objects = AccountManager()

    USERNAME_FIELD = 'login'

    def __str__(self):
        return f"{self.login}"

    def set_password(self, raw_password):
        raise NotImplementedError("Password not implemented")

    def check_password(self, raw_password):
        return False
    
    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True
    
    def time_to_spin(self):
        if not self.last_spin:
            time_to_spin = timedelta(0)
        else:
            time_since_last_spin = timezone.now() - self.last_spin
            if time_since_last_spin >= timedelta(days=1):
                time_to_spin = timedelta(0)
            else:
                time_to_spin = timedelta(days=1) - time_since_last_spin
        
        return time_to_spin
    
    def can_spin(self):
        if self.time_to_spin() > timedelta(0) and not self.test_mode:
            return False
        return True



class OauthStateManager(models.Manager):
    def get_or_create_state(self, session_id):
        if not session_id:
            raise ValueError("session_id must be provided")
        try: 
            state = self.get(session_id=session_id)
        except OauthState.DoesNotExist:
            state = None

        if state:
            # Check for 2 minutes expiration
            if (timezone.now() - state.created_at).total_seconds() > 120:
                state.delete()
                state = None
            else:
                return state

        if not state:
            random_bytes = secrets.token_bytes(48)
            state = base64.urlsafe_b64encode(random_bytes).decode('utf-8').rstrip('=')
            return self.create(state=state, session_id=session_id)
        
    
    def get_state(self, session_id):
        if not session_id:
            raise ValueError("session_id must be provided")
        try:
            return self.get(session_id=session_id)
        except OauthState.DoesNotExist:
            raise ValueError("State not found for the provided session_id")


class OauthState(models.Model):
    state = models.CharField(max_length=100, unique=True, blank=False, null=False)
    session_id = models.CharField(max_length=100, unique=True, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.state}"
    
    objects = OauthStateManager()



class AuthorizedExternalUserManager(models.Manager):
    def get_or_create_user(self, login):
        if not login:
            raise ValueError("login must be provided")
        try:
            return self.get(login=login)
        except AuthorizedExternalUser.DoesNotExist:
            return self.create(login=login)



# This allow users who aren't in Piscine to use the app
# Use /admin to add external users
class AuthorizedExternalUser(models.Model):
    login = models.CharField(max_length=20, unique=True, blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuthorizedExternalUserManager()

    def __str__(self):
        return f"Special authorization for {self.login}"