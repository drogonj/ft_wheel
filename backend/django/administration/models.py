from django.db import models

class SiteSettings(models.Model):
    """Model to store site-wide settings"""

    # Maintenance (only moderators and admins can access the site)
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(
        default="The site is currently under maintenance. Please check back later."
    )

    # Jackpot cooldown in seconds (default 24*60*60s)
    jackpot_cooldown = models.PositiveIntegerField(default=86400)
