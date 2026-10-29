from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
import random


def generate_account_number():
    return str(random.randint(1000000000, 9999999999))


class BankAccount(models.Model):
    ACCOUNT_TYPE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('group', 'Group'),
    ]

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='bank_account',
        null=True,
        blank=True
    )
    account_number = models.CharField(
        max_length=10,
        unique=True,
        default=generate_account_number
    )
    account_type = models.CharField(
        max_length=10,
        choices=ACCOUNT_TYPE_CHOICES
    )
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"{self.user.get_full_name()} — {self.account_number}"
        return f"Group Account — {self.account_number}"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    ]

    account = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    transaction_type = models.CharField(
        max_length=15,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    performed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_transactions'
    )
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.transaction_type} — {self.amount} TZS ({self.account.account_number})"


class TransactionEditLog(models.Model):
    """Records every edit made to a transaction for accountability."""
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='edit_logs'
    )
    edited_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True
    )
    old_amount = models.DecimalField(max_digits=12, decimal_places=2)
    new_amount = models.DecimalField(max_digits=12, decimal_places=2)
    old_timestamp = models.DateTimeField()
    new_timestamp = models.DateTimeField()
    old_notes = models.TextField(blank=True, null=True)
    new_notes = models.TextField(blank=True, null=True)
    edited_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Edit on TX#{self.transaction.id} by {self.edited_by}"
    
