from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Bank Manager'),
        ('loan_manager', 'Loan Manager'),
        ('teller', 'Teller'),
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student'
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
        ('account_created', 'Account Created'),
        ('account_edited', 'Account Edited'),
        ('transaction_edited', 'Transaction Edited'),
        ('transaction_deleted', 'Transaction Deleted'),
        ('user_created', 'User Created'),
        ('user_edited', 'User Edited'),
        ('user_toggled', 'User Activated/Deactivated'),
        ('loan_created', 'Loan Created'),
        ('loan_status_updated', 'Loan Status Updated'),
        ('bulk_import', 'Bulk Import'),
        ('backup', 'Database Backup'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} — {self.action} — {self.timestamp}"