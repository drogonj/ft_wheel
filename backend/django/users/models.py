from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.apps import apps
from datetime import timedelta
import secrets, base64
from administration.models import SiteSettings
from django.db.models import Q
from django.utils import timezone as dj_tz

# Create your models here.
class AccountManager(BaseUserManager):
    def create_user(self, login, **extra_fields):
        user = self.model(login=login, **extra_fields)
        user.save()
        return user

    def create_superuser(self, login, role, **extra_fields):
        extra_fields.setdefault("role", role)
        extra_fields.setdefault("is_staff", True if role == 'admin' else False)
        return self.create_user(login, **extra_fields)



class Account(AbstractBaseUser):
    ROLES = [
        ('user', 'User'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    ]

    MODERATOR_PERMS = [
        'history_admin',
        'history_detail_api',
        'add_history_mark',
        'control_panel',
        'site_settings_api',
        'grant_ticket_api',
        'ticket_summary_api',
        'list_tickets_api',
        'delete_tickets_api',
        'bypass_maintenance',
    ]

    date_joined = models.DateTimeField(verbose_name="date joined", auto_now_add=True)
    last_login = models.DateTimeField(verbose_name="last login", auto_now=True)

    login = models.CharField(max_length=20, unique=True, blank=False, null=False)
    intra_id = models.IntegerField(unique=True, blank=False, null=False)

    # User rights -> [user, moderator, admin]
    role = models.CharField(max_length=10, choices=ROLES, default='user')
    is_staff = models.BooleanField(default=False)  # Required for admin access (not used otherwise)
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

    @property
    def is_superuser(self):
        return self.role == 'admin'

    @is_superuser.setter
    def is_superuser(self, value):
        if value:
            self.role = 'admin'
        elif self.role == 'admin':
            self.role = 'user'

    def is_admin(self):
        return self.role == 'admin'
    
    def is_moderator(self):
        return self.role in ['admin', 'moderator']

    def set_password(self, raw_password):
        raise NotImplementedError("Password not implemented")

    def check_password(self, raw_password):
        return False
    
    def has_perm(self, perm, obj=None):
        if self.is_admin():
            return True
        elif self.is_moderator() and perm in self.MODERATOR_PERMS:
            return True
        return False

    def has_module_perms(self, app_label):
        if self.is_admin():
            return True
        return ['wheel', 'users'].__contains__(app_label)
    
    def time_to_spin(self):
        # Get cooldown from site settings
        try:
            settings = SiteSettings.objects.get(pk=1)
            cooldown_seconds = settings.jackpot_cooldown
        except (ImportError, SiteSettings.DoesNotExist):
            # Fallback to 24 hours if settings not available
            cooldown_seconds = 86400
        
        cooldown_delta = timedelta(seconds=cooldown_seconds)
        
        if not self.last_spin:
            time_to_spin = timedelta(0)
        else:
            time_since_last_spin = timezone.now() - self.last_spin
            if time_since_last_spin >= cooldown_delta:
                time_to_spin = timedelta(0)
            else:
                time_to_spin = cooldown_delta - time_since_last_spin
        
        return time_to_spin

    def has_ticket(self, wheel_slug: str) -> bool:
        if not wheel_slug:
            return False
        # Lazy import to avoid circular import at app load
        Ticket = apps.get_model('wheel', 'Ticket')
        return Ticket.objects.filter(user=self, wheel_slug=wheel_slug, used_at__isnull=True).exists()

    def consume_ticket(self, wheel_slug: str) -> bool:
        """Consume one unused ticket for this wheel. Returns True if consumed."""
        if not wheel_slug:
            return False
        Ticket = apps.get_model('wheel', 'Ticket')
        ticket = Ticket.objects.filter(user=self, wheel_slug=wheel_slug, used_at__isnull=True).order_by('created_at').first()
        if not ticket:
            return False
        ticket.mark_used()
        return True

    def tickets_count(self, wheel_slug: str) -> int:
        if not wheel_slug:
            return 0
        Ticket = apps.get_model('wheel', 'Ticket')
        return Ticket.objects.filter(user=self, wheel_slug=wheel_slug, used_at__isnull=True).count()

    def can_spin_wheel(self, wheel_slug: str, ticket_only: bool) -> bool:
        """New gate: if ticket_only -> must have unused ticket.
        Else keep cooldown logic (test_mode bypasses cooldown as before).
        """
        if self.test_mode:
            return True
        if ticket_only:
            return self.has_ticket(wheel_slug)
        # standard cooldown
        if self.time_to_spin() > timedelta(0):
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
