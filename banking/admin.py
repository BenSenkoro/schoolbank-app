from django.contrib import admin
from .models import BankAccount, Transaction

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'account_number', 'account_type', 'balance', 'is_active', 'created_at']
    list_filter = ['account_type', 'is_active']
    search_fields = ['user__username', 'account_number']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['account', 'transaction_type', 'amount', 'performed_by', 'timestamp']
    list_filter = ['transaction_type']