from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from banking.models import BankAccount, Transaction
from loans.models import LoanRecord
from datetime import date, timedelta


def role_required(*roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, 'You do not have permission to access that page.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
@role_required('admin', 'manager')
def reports_home(request):
    return render(request, 'reports/reports_home.html')


@login_required
@role_required('admin', 'manager')
def daily_transactions(request):
    # Default to today, allow date filter
    selected_date = request.GET.get('date', timezone.now().date().isoformat())
    try:
        selected_date = date.fromisoformat(selected_date)
    except ValueError:
        selected_date = timezone.now().date()

    transactions = Transaction.objects.select_related(
        'account__user', 'performed_by'
    ).filter(timestamp__date=selected_date).order_by('timestamp')

    total_deposits = transactions.filter(
        transaction_type='deposit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_withdrawals = transactions.filter(
        transaction_type='withdrawal'
    ).aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'reports/daily_transactions.html', {
        'transactions': transactions,
        'selected_date': selected_date,
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'net': total_deposits - total_withdrawals,
    })


@login_required
@role_required('admin', 'manager')
def account_balances(request):
    account_type = request.GET.get('type', '')
    accounts = BankAccount.objects.select_related('user').filter(
        is_active=True
    ).order_by('account_type', 'user__first_name')

    if account_type:
        accounts = accounts.filter(account_type=account_type)

    total_balance = accounts.aggregate(
        total=Sum('balance')
    )['total'] or 0

    student_balance = BankAccount.objects.filter(
        account_type='student', is_active=True
    ).aggregate(total=Sum('balance'))['total'] or 0

    teacher_balance = BankAccount.objects.filter(
        account_type='teacher', is_active=True
    ).aggregate(total=Sum('balance'))['total'] or 0

    return render(request, 'reports/account_balances.html', {
        'accounts': accounts,
        'total_balance': total_balance,
        'student_balance': student_balance,
        'teacher_balance': teacher_balance,
        'account_type': account_type,
    })


@login_required
@role_required('admin', 'manager')
def loan_status_report(request):
    status_filter = request.GET.get('status', '')
    loans = LoanRecord.objects.select_related(
        'applicant__user', 'created_by'
    ).order_by('-date_issued')

    if status_filter:
        loans = loans.filter(status=status_filter)

    total_amount = loans.aggregate(
        total=Sum('amount')
    )['total'] or 0

    summary = {
        'total': LoanRecord.objects.count(),
        'pending': LoanRecord.objects.filter(status='pending').count(),
        'approved': LoanRecord.objects.filter(status='approved').count(),
        'rejected': LoanRecord.objects.filter(status='rejected').count(),
        'repaid': LoanRecord.objects.filter(status='repaid').count(),
        'approved_amount': LoanRecord.objects.filter(
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0,
    }

    return render(request, 'reports/loan_status.html', {
        'loans': loans,
        'total_amount': total_amount,
        'status_filter': status_filter,
        'summary': summary,
    })


@login_required
@role_required('admin', 'manager')
def deposit_withdrawal_history(request):
    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    tx_type = request.GET.get('type', '')

    transactions = Transaction.objects.select_related(
        'account__user', 'performed_by'
    ).order_by('-timestamp')

    if date_from:
        transactions = transactions.filter(timestamp__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(timestamp__date__lte=date_to)
    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)

    total_deposits = Transaction.objects.filter(
        transaction_type='deposit'
    )
    total_withdrawals = Transaction.objects.filter(
        transaction_type='withdrawal'
    )

    if date_from:
        total_deposits = total_deposits.filter(timestamp__date__gte=date_from)
        total_withdrawals = total_withdrawals.filter(timestamp__date__gte=date_from)
    if date_to:
        total_deposits = total_deposits.filter(timestamp__date__lte=date_to)
        total_withdrawals = total_withdrawals.filter(timestamp__date__lte=date_to)

    summary = {
        'total_deposits': total_deposits.aggregate(t=Sum('amount'))['t'] or 0,
        'total_withdrawals': total_withdrawals.aggregate(t=Sum('amount'))['t'] or 0,
        'count_deposits': total_deposits.count(),
        'count_withdrawals': total_withdrawals.count(),
    }

    return render(request, 'reports/deposit_withdrawal_history.html', {
        'transactions': transactions,
        'date_from': date_from,
        'date_to': date_to,
        'tx_type': tx_type,
        'summary': summary,
    })


@login_required
@role_required('admin', 'manager')
def account_list_report(request):
    account_type = request.GET.get('type', '')
    accounts = BankAccount.objects.select_related('user').order_by(
        'account_type', 'user__first_name'
    )

    if account_type:
        accounts = accounts.filter(account_type=account_type)

    summary = {
        'total': BankAccount.objects.count(),
        'students': BankAccount.objects.filter(account_type='student').count(),
        'teachers': BankAccount.objects.filter(account_type='teacher').count(),
        'active': BankAccount.objects.filter(is_active=True).count(),
        'inactive': BankAccount.objects.filter(is_active=False).count(),
    }

    return render(request, 'reports/account_list_report.html', {
        'accounts': accounts,
        'account_type': account_type,
        'summary': summary,
        'today': timezone.now().date(),
    })