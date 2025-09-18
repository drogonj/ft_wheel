from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# History model
class History(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    wheel = models.CharField(max_length=50, default='standard', db_index=True)  # Add index for frequent queries
    details = models.CharField(max_length=250, blank=True, null=True)  # CharField instead of TextField
    color = models.CharField(max_length=20, default='#FFFFFF')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='histories')

    r_message = models.CharField(blank=True, null=True)  # message of intra response
    r_data = models.TextField(blank=True, null=True)  # data of intra response

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.wheel} - {self.details}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Histories"