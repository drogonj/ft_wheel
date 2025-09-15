from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class HistoryManager(models.Manager):
    def create(self, wheel, details, color, user):
        history = self.model(
            wheel=wheel,
            details=details,
            color=color,
            user=user
        )
        history.save()
        return history

# History model
class History(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    wheel = models.CharField(max_length=50, default='standard')
    details = models.TextField(max_length=250, blank=True, null=True)
    color = models.CharField(max_length=20, default='#FFFFFF')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='histories')

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.wheel} - {self.details}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Histories"