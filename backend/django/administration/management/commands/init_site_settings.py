from django.core.management.base import BaseCommand
from administration.models import SiteSettings

class Command(BaseCommand):
    help = 'Initialize site settings with default values'

    def handle(self, *args, **options):
        settings, created = SiteSettings.objects.get_or_create(pk=1)
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('Successfully created initial SiteSettings instance')
            )
        else:
            self.stdout.write(
                self.style.WARNING('SiteSettings instance already exists')
            )
        
        # Display current settings
        self.stdout.write(f"Maintenance mode: {settings.maintenance_mode}")
        self.stdout.write(f"Jackpot cooldown: {settings.jackpot_cooldown} seconds ({settings.jackpot_cooldown // 3600}h)")
        self.stdout.write(f"Maintenance message: {settings.maintenance_message[:50]}...")