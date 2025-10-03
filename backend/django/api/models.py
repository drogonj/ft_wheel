from django.db import models

# Add your models here.

class UniqueGroupOwner(models.Model):
    group_id = models.IntegerField(unique=True)
    owner_user_id = models.IntegerField()
    previous_user_id = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['group_id'], name='unique_group_ownership')
        ]

    objects = models.Manager()

    def __str__(self):
        return f"Group {self.group_id} owned by User {self.owner_user_id}"
