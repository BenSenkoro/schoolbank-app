from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from .models import LoanRecord
from banking.models import BankAccount
from accounts.utils import log_activity, paginate


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
@role_required('admin', 'manager', 'loan_manager')
def loan_list(request):
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    loans = LoanRecord.objects.select_related(
        'applicant__user', 'created_by'
    ).all().order_by('-created_at')

    if query:
        loans = loans.filter(
            Q(applicant__account_number__icontains=query) |
            Q(applicant__user__first_name__icontains=query) |
            Q(applicant__user__last_name__icontains=query) |
            Q(applicant__user__username__icontains=query) |
            Q(applicant_name__icontains=query)
        )

    if status_filter:
        loans = loans.filter(status=status_filter)

    stats = {
        'total': LoanRecord.objects.count(),
        'pending': LoanRecord.objects.filter(status='pending').count(),
        'approved': LoanRecord.objects.filter(status='approved').count(),
        'repaid': LoanRecord.objects.filter(status='repaid').count(),
        'total_amount': LoanRecord.objects.filter(
            status='approved'
        ).aggregate(total=Sum('amount'))['total'] or 0,
    }

    page_obj = paginate(request, loans)
    return render(request, 'loans/loan_list.html', {
        'loans': page_obj,
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'stats': stats,
    })


@login_required
@role_required('admin', 'manager', 'loan_manager')
def create_loan(request):
    accounts = BankAccount.objects.select_related('user').filter(is_active=True)

    if request.method == 'POST':
        applicant_type = request.POST.get('applicant_type')
        amount = request.POST.get('amount')
        repayment_period = request.POST.get('repayment_period_months')
        date_issued = request.POST.get('date_issued')
        notes = request.POST.get('notes', '')

        applicant_account = None
        applicant_name = ''

        if applicant_type == 'with_account':
            account_id = request.POST.get('applicant')
            if not account_id:
                messages.error(request, 'Please select an applicant account.')
                return render(request, 'loans/create_loan.html', {
                    'accounts': accounts,
                    'today': timezone.now().date().isoformat(),
                })
            applicant_account = BankAccount.objects.filter(id=account_id).first()
            if not applicant_account:
                messages.error(request, 'Selected account no longer exists. Please choose another.')
                return render(request, 'loans/create_loan.html', {
                    'accounts': accounts,
                    'today': timezone.now().date().isoformat(),
                })
        else:
            applicant_name = request.POST.get('applicant_name', '').strip()
            if not applicant_name:
                messages.error(request, 'Applicant name is required for loans without a bank account.')
                return render(request, 'loans/create_loan.html', {
                    'accounts': accounts,
                    'today': timezone.now().date().isoformat(),
                })

        # NOTE: No try/except here temporarily so Django shows the FULL error page
        loan = LoanRecord.objects.create(
            applicant=applicant_account,
            applicant_name=applicant_name,
            applicant_type=applicant_type,
            amount=amount,
            repayment_period_months=repayment_period,
            date_issued=date_issued,
            notes=notes,
            created_by=request.user,
            status='pending'
        )

        log_activity(
            user=request.user,
            action='loan_created',
            description=f'Loan record created for {loan.applicant_display_name} — TZS {amount} at {loan.base_interest_rate}% interest.',
            request=request
        )

        messages.success(request, f'Loan record created successfully for {loan.applicant_display_name}.')
        return redirect('loan_list')

    return render(request, 'loans/create_loan.html', {
        'accounts': accounts,
        'today': timezone.now().date().isoformat(),
    })


@login_required
@role_required('admin', 'manager', 'loan_manager')
def loan_detail(request, pk):
    loan = get_object_or_404(LoanRecord, pk=pk)
    return render(request, 'loans/loan_detail.html', {'loan': loan})


@login_required
@role_required('admin', 'manager')
def update_loan_status(request, pk):
    """Only admin and manager can change loan status."""
    loan = get_object_or_404(LoanRecord, pk=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'approved', 'rejected', 'repaid']:
            loan.status = new_status
            loan.save()
            log_activity(
                user=request.user,
                action='loan_status_updated',
                description=f'Loan #{loan.pk} status updated to {loan.get_status_display()}.',
                request=request
            )
            messages.success(request, f'Loan status updated to {loan.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status.')

    return redirect('loan_detail', pk=pk)
@login_required
@role_required('admin')
def delete_loan(request, pk):
    loan = get_object_or_404(LoanRecord, pk=pk)

    if request.method == 'POST':
        applicant_name = loan.applicant_display_name
        amount = loan.amount
        loan.delete()

        log_activity(
            user=request.user,
            action='loan_status_updated',
            description=f'Loan record for {applicant_name} (TZS {amount}) was deleted.',
            request=request
        )

        messages.success(request, f'Loan record for {applicant_name} has been deleted.')
        return redirect('loan_list')

    return render(request, 'loans/delete_loan.html', {'loan': loan})