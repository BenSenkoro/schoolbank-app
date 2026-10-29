from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from banking.models import BankAccount, Transaction
from django.db.models import Sum, Count
from django.utils import timezone

@login_required
def dashboard_router(request):
    role = request.user.role

    if role in ['admin', 'manager']:
        # Real stats for admin/manager
        total_accounts = BankAccount.objects.count()
        total_members = BankAccount.objects.count()
        total_balance = BankAccount.objects.aggregate(
            total=Sum('balance'))['total'] or 0

        today = timezone.now().date()
        today_deposits = Transaction.objects.filter(
            transaction_type='deposit',
            timestamp__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0

        today_withdrawals = Transaction.objects.filter(
            transaction_type='withdrawal',
            timestamp__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0

        recent_transactions = Transaction.objects.select_related(
            'account__user', 'performed_by'
        ).order_by('-timestamp')[:8]

        context = {
            'total_accounts': total_accounts,
            'total_members': total_members,
            'total_balance': total_balance,
            'today_deposits': today_deposits,
            'today_withdrawals': today_withdrawals,
            'recent_transactions': recent_transactions,
        }

        if role == 'admin':
            return render(request, 'dashboard/admin_dashboard.html', context)
        else:
            return render(request, 'dashboard/manager_dashboard.html', context)

    elif role == 'loan_manager':
        from loans.models import LoanRecord

        stats = {
            'total': LoanRecord.objects.count(),
            'pending': LoanRecord.objects.filter(status='pending').count(),
            'approved': LoanRecord.objects.filter(status='approved').count(),
            'repaid': LoanRecord.objects.filter(status='repaid').count(),
            'total_amount': LoanRecord.objects.filter(
                status='approved'
            ).aggregate(total=Sum('amount'))['total'] or 0,
        }
        recent_loans = LoanRecord.objects.select_related(
            'applicant__user'
        ).order_by('-created_at')[:8]

        return render(request, 'dashboard/loan_dashboard.html', {
            'stats': stats,
            'recent_loans': recent_loans,
        })
    elif role == 'teller':
        today = timezone.now().date()
        today_deposits = Transaction.objects.filter(
            transaction_type='deposit',
            timestamp__date=today,
            performed_by=request.user
        ).aggregate(total=Sum('amount'))['total'] or 0

        today_withdrawals = Transaction.objects.filter(
            transaction_type='withdrawal',
            timestamp__date=today,
            performed_by=request.user
        ).aggregate(total=Sum('amount'))['total'] or 0

        recent_transactions = Transaction.objects.select_related(
            'account__user'
        ).filter(
            performed_by=request.user
        ).order_by('-timestamp')[:8]

        return render(request, 'dashboard/teller_dashboard.html', {
            'today_deposits': today_deposits,
            'today_withdrawals': today_withdrawals,
            'recent_transactions': recent_transactions,
        })

    elif role in ['student', 'teacher']:
        try:
            account = request.user.bank_account
            transactions = account.transactions.order_by('-timestamp')[:8]
            context = {'account': account, 'transactions': transactions}
        except BankAccount.DoesNotExist:
            context = {'account': None, 'transactions': []}
        return render(request, 'dashboard/member_dashboard.html', context)

    else:
        return redirect('login')