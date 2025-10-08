from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# History marks for admin/moderator validation
class HistoryMark(models.Model):
    """Represents a validation mark on a history entry"""
    history = models.ForeignKey('History', on_delete=models.CASCADE, related_name='marks')
    marked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history_marks')
    marked_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=200, blank=True, help_text="Optional note about the validation")
    
    class Meta:
        unique_together = ['history', 'marked_by']  # One mark per user per history
        ordering = ['-marked_at']
    
    def __str__(self):
        return f"Mark by {self.marked_by.login} on {self.history.id}"

# History model
class History(models.Model):
    id = models.AutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    wheel = models.CharField(max_length=50, default='standard', db_index=True)  # Add index for frequent queries
    details = models.CharField(max_length=250, blank=True, null=True)  # CharField instead of TextField
    color = models.CharField(max_length=20, default='#FFFFFF')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='histories')

    function_name = models.CharField(max_length=100, blank=False, null=False)  # Complete Name of the function executed (ex: 'builtins.default')
    r_message = models.CharField(blank=True, null=True)  # message of intra response
    r_data = models.JSONField(blank=True, null=True)  # data of intra response
    success = models.BooleanField(default=True, help_text="Whether the jackpot execution was successful")
    
    # Admin fields
    is_cancelled = models.BooleanField(default=False, help_text="Whether this entry has been cancelled")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_histories')
    cancellation_reason = models.CharField(max_length=200, blank=True)

    def __str__(self):
        status = " [CANCELLED]" if self.is_cancelled else ""
        return f"{self.timestamp} - {self.user} - {self.wheel} - {self.details}{status}"
    
    @property
    def marks_count(self):
        """Number of validation marks"""
        return self.marks.count()
    
    @property 
    def marked_by_users(self):
        """List of users who marked this entry"""
        return [mark.marked_by for mark in self.marks.all()]
    
    def can_be_cancelled(self):
        """Check if this history entry can be cancelled"""
        return not self.is_cancelled and self.r_data is not None and self.success is True
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Histories"


class Ticket(models.Model):
    """Represents a spin ticket grant. A ticket allows one spin regardless of cooldown.
    If a wheel is marked as ticket_only, user must have at least one unused ticket for that wheel.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    wheel_slug = models.CharField(max_length=50, db_index=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['wheel_slug', 'user']),
            models.Index(fields=['used_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        status = 'used' if self.used_at else 'unused'
        return f"Ticket[{self.wheel_slug}] {self.user.login} ({status})"

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    def mark_used(self):
        if not self.used_at:
            self.used_at = timezone.now()
            self.save(update_fields=['used_at'])