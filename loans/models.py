from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from accounts.models import CustomUser
from banking.models import BankAccount


class LoanRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('repaid', 'Repaid'),
    ]

    APPLICANT_TYPE_CHOICES = [
        ('with_account', 'Has Bank Account'),
        ('without_account', 'No Bank Account'),
    ]

    # Applicant can be linked to an account OR just a name if they have no account
    applicant = models.ForeignKey(
        BankAccount,
        on_delete=models.CASCADE,
        related_name='loans',
        null=True,
        blank=True
    )
    applicant_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Required only if applicant has no bank account"
    )
    applicant_type = models.CharField(
        max_length=20,
        choices=APPLICANT_TYPE_CHOICES,
        default='with_account'
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    repayment_period_months = models.PositiveIntegerField(
        help_text="Repayment period in months"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='loans_created'
    )
    date_issued = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        name = self.applicant.user.get_full_name() if self.applicant and self.applicant.user else self.applicant_name
        return f"Loan — {name} | {self.amount} TZS | {self.status}"

    # ── Interest Logic ──────────────────────────────────

    @property
    def base_interest_rate(self):
        """10% if has account, 15% if no account."""
        return 10 if self.applicant_type == 'with_account' else 15

    @property
    def due_date(self):
        """Date the loan is due based on issue date + repayment period."""
        return self.date_issued + relativedelta(months=self.repayment_period_months)

    @property
    def is_overdue(self):
        """True if due date has passed and not yet repaid."""
        if self.status == 'repaid':
            return False
        return timezone.now().date() > self.due_date

    @property
    def applicable_interest_rate(self):
        """Doubles the rate if overdue (penalty)."""
        rate = self.base_interest_rate
        if self.is_overdue:
            rate *= 2
        return rate

    @property
    def interest_amount(self):
        """Flat interest on principal."""
        return (self.amount * self.applicable_interest_rate) / 100

    @property
    def total_repayable(self):
        """Principal + interest."""
        return self.amount + self.interest_amount

    @property
    def monthly_repayment(self):
        """Total repayable divided across the period."""
        if self.repayment_period_months:
            return self.total_repayable / self.repayment_period_months
        return self.total_repayable

    @property
    def applicant_display_name(self):
        if self.applicant and self.applicant.user:
            return self.applicant.user.get_full_name() or self.applicant.user.username
        return self.applicant_name or "Unknown"