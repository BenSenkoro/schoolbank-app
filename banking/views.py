from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import F, Q, Sum
from .models import BankAccount, Transaction, TransactionEditLog
from accounts.models import CustomUser
import re
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from accounts.utils import log_activity, paginate
from uuid import uuid4


def role_required(*roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles:
                messages.error(request, 'You do not have permission.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def transactions_home(user):
    # Tellers can't open the transaction list, so send them to their dashboard.
    return 'transaction_list' if user.role in ['admin', 'manager'] else 'dashboard'


# ── One-time form tokens ──────────────────────────────────────
# Each money form carries a token that can be used once, so a refresh,
# back-button resubmit or double click can't record the same transaction twice.

def issue_form_token(request):
    token = uuid4().hex
    tokens = request.session.get('form_tokens', [])[-19:]
    tokens.append(token)
    request.session['form_tokens'] = tokens
    return token


def use_form_token(request):
    token = request.POST.get('form_token')
    tokens = request.session.get('form_tokens', [])
    if not token or token not in tokens:
        return False
    tokens.remove(token)
    request.session['form_tokens'] = tokens
    request.session.save()  # save now so a second request arriving straight after sees it used
    return True


def duplicate_submission(request):
    messages.warning(request, 'That form was already submitted, so nothing new was recorded. '
                              'Check recent transactions before trying again.')
    return redirect(transactions_home(request.user))


# ── Account Views ──────────────────────────────────────────

@login_required
@role_required('admin', 'manager')
def account_list(request):
    query = request.GET.get('q', '').strip()
    accounts = BankAccount.objects.select_related('user').all().order_by('-created_at')
    if query:
        accounts = accounts.filter(
            Q(account_number__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__username__icontains=query)
        )
    page_obj = paginate(request, accounts)
    return render(request, 'banking/account_list.html', {
        'accounts': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
@role_required('admin', 'manager')
def create_account(request):
    existing_account_user_ids = BankAccount.objects.values_list('user_id', flat=True)
    eligible_users = CustomUser.objects.filter(
        role__in=['student', 'teacher']
    ).exclude(id__in=existing_account_user_ids)

    if request.method == 'POST':
        user_id = request.POST.get('user')
        account_type = request.POST.get('account_type')
        initial_deposit = request.POST.get('initial_deposit', 0)

        try:
            user = CustomUser.objects.get(id=user_id)
            initial_deposit = Decimal(initial_deposit or 0)

            account = BankAccount.objects.create(
                user=user,
                account_type=account_type,
                balance=initial_deposit
            )

            if initial_deposit > 0:
                Transaction.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=initial_deposit,
                    performed_by=request.user,
                    notes='Initial deposit on account opening'
                )

            messages.success(request, f'Account {account.account_number} created successfully.')
            log_activity(
            user=request.user,
            action='account_created',
            description=f'Bank account {account.account_number} created for {user.get_full_name() or user.username}.',
            request=request)
            return redirect('account_list')
        except Exception as e:
            messages.error(request, f'Error creating account: {e}')

    return render(request, 'banking/create_account.html', {'users': eligible_users})


@login_required
@role_required('admin', 'manager')
def account_detail(request, pk):
    account = get_object_or_404(BankAccount, pk=pk)
    transactions = account.transactions.all().order_by('-timestamp')[:20]
    return render(request, 'banking/account_detail.html', {
        'account': account,
        'transactions': transactions,
    })


# ── Money form helpers ────────────────────────────────────────

MAX_AMOUNT = Decimal('9999999999')  # fits Transaction.amount (12 digits, 2 decimals)


def parse_amount(raw):
    """Whole shillings only; commas allowed. Returns (amount, error)."""
    raw = (raw or '').replace(',', '').strip()
    if re.fullmatch(r'\d+\.\d*[1-9]\d*', raw):
        return None, 'Enter a whole number of shillings (no cents).'
    if not re.fullmatch(r'\d+(\.0*)?', raw):   # plain digits only: no signs, spaces or "1e3"
        return None, 'Enter the amount in TZS.'
    amount = Decimal(raw).to_integral_value()
    if amount <= 0:
        return None, 'Amount must be greater than zero.'
    if amount > MAX_AMOUNT:
        return None, 'That amount is too large.'
    return amount, None


def parse_past_timestamp(raw):
    """Blank means now. A backdated time is allowed, a future one is not. Returns (timestamp, error)."""
    if not raw:
        return timezone.now(), None
    timestamp = parse_datetime(raw)
    if timestamp is None:
        return None, 'Enter a valid transaction date and time.'
    if timezone.is_naive(timestamp):
        timestamp = timezone.make_aware(timestamp)
    if timestamp > timezone.now() + timedelta(minutes=5):
        return None, 'The transaction date can’t be in the future.'
    return timestamp, None


def get_active_account(raw_id):
    try:
        return BankAccount.objects.select_related('user').get(pk=int(raw_id), is_active=True)
    except (TypeError, ValueError, BankAccount.DoesNotExist):
        return None


def money_form_context(request, form):
    """Context shared by the deposit, withdrawal and transfer pages.

    `form` is the submitted POST (so values survive an error) or the GET query
    (so a link like ?account=5 can preselect an account).
    """
    accounts = BankAccount.objects.select_related('user').filter(is_active=True).order_by('account_number')
    return {
        'form': form,
        'form_token': issue_form_token(request),
        'max_timestamp': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
        'accounts_data': [{
            'id': a.pk,
            'number': a.account_number,
            'name': (a.user.get_full_name() or a.user.username) if a.user else 'Group Account',
            'type': a.get_account_type_display(),
            'balance': str(a.balance),
        } for a in accounts],
    }


# ── Deposit ─────────────────────────────────────────────────

@login_required
@role_required('admin', 'manager', 'teller')
def deposit(request):
    form = request.GET
    if request.method == 'POST':
        if not use_form_token(request):
            return duplicate_submission(request)
        form = request.POST

        account = get_active_account(form.get('account'))
        amount, amount_error = parse_amount(form.get('amount'))
        timestamp, time_error = parse_past_timestamp(form.get('timestamp'))
        error = 'Choose the account to deposit into.' if account is None else amount_error or time_error

        if error:
            messages.error(request, error)
        else:
            with db_transaction.atomic():
                BankAccount.objects.filter(pk=account.pk).update(balance=F('balance') + amount)
                tx = Transaction.objects.create(
                    account=account,
                    transaction_type='deposit',
                    amount=amount,
                    performed_by=request.user,
                    notes=form.get('notes', '').strip(),
                    timestamp=timestamp
                )
            log_activity(
            user=request.user,
            action='deposit',
            description=f'Deposited TZS {amount:,.2f} to account {account.account_number}.',
            request=request)
            return redirect('transaction_receipt', pk=tx.pk)

    return render(request, 'banking/deposit.html', money_form_context(request, form))


# ── Withdrawal ───────────────────────────────────────────────

@login_required
@role_required('admin', 'manager', 'teller')
def withdrawal(request):
    form = request.GET
    if request.method == 'POST':
        if not use_form_token(request):
            return duplicate_submission(request)
        form = request.POST

        account = get_active_account(form.get('account'))
        amount, amount_error = parse_amount(form.get('amount'))
        timestamp, time_error = parse_past_timestamp(form.get('timestamp'))
        error = 'Choose the account to withdraw from.' if account is None else amount_error or time_error

        if not error:
            with db_transaction.atomic():
                # Only debit if the balance still covers it, even if another withdrawal landed first
                debited = BankAccount.objects.filter(pk=account.pk, balance__gte=amount).update(
                    balance=F('balance') - amount)
                if debited:
                    tx = Transaction.objects.create(
                        account=account,
                        transaction_type='withdrawal',
                        amount=amount,
                        performed_by=request.user,
                        notes=form.get('notes', '').strip(),
                        timestamp=timestamp
                    )
            if not debited:
                account.refresh_from_db()
                error = f'Insufficient balance. Current balance is TZS {account.balance:,.2f}.'

        if error:
            messages.error(request, error)
        else:
            log_activity(
            user=request.user,
            action='withdrawal',
            description=f'Withdrew TZS {amount:,.2f} from account {account.account_number}.',
            request=request)
            return redirect('transaction_receipt', pk=tx.pk)

    return render(request, 'banking/withdrawal.html', money_form_context(request, form))


# ── Transfer ─────────────────────────────────────────────────

@login_required
@role_required('admin', 'manager', 'teller')
def transfer(request):
    form = request.GET
    if request.method == 'POST':
        if not use_form_token(request):
            return duplicate_submission(request)
        form = request.POST

        from_account = get_active_account(form.get('from_account'))
        to_account = get_active_account(form.get('to_account'))
        amount, amount_error = parse_amount(form.get('amount'))
        notes = form.get('notes', '').strip()

        if from_account is None:
            error = 'Choose the account to transfer from.'
        elif to_account is None:
            error = 'Choose the account to transfer to.'
        elif from_account.pk == to_account.pk:
            error = 'Cannot transfer to the same account.'
        else:
            error = amount_error

        if not error:
            now = timezone.now()
            with db_transaction.atomic():
                debited = BankAccount.objects.filter(pk=from_account.pk, balance__gte=amount).update(
                    balance=F('balance') - amount)
                if debited:
                    BankAccount.objects.filter(pk=to_account.pk).update(balance=F('balance') + amount)
                    tx_out = Transaction.objects.create(
                        account=from_account,
                        transaction_type='transfer_out',
                        amount=amount,
                        performed_by=request.user,
                        notes=notes or f'Transfer to {to_account.account_number}',
                        timestamp=now
                    )
                    Transaction.objects.create(
                        account=to_account,
                        transaction_type='transfer_in',
                        amount=amount,
                        performed_by=request.user,
                        notes=notes or f'Transfer from {from_account.account_number}',
                        timestamp=now
                    )
            if not debited:
                from_account.refresh_from_db()
                error = f'Insufficient balance. Current balance is TZS {from_account.balance:,.2f}.'

        if error:
            messages.error(request, error)
        else:
            log_activity(
            user=request.user,
            action='transfer',
            description=f'Transferred TZS {amount:,.2f} from {from_account.account_number} to {to_account.account_number}.',
            request=request)
            return redirect('transaction_receipt', pk=tx_out.pk)

    return render(request, 'banking/transfer.html', money_form_context(request, form))


# ── Transaction List ──────────────────────────────────────────

@login_required
@role_required('admin', 'manager')
def transaction_list(request):
    query = request.GET.get('q', '').strip()
    transactions = Transaction.objects.select_related(
        'account__user', 'performed_by'
    ).all().order_by('-timestamp')

    if query:
        transactions = transactions.filter(
            Q(account__account_number__icontains=query) |
            Q(account__user__first_name__icontains=query) |
            Q(account__user__last_name__icontains=query) |
            Q(account__user__username__icontains=query)
        )

    page_obj = paginate(request, transactions)
    return render(request, 'banking/transaction_list.html', {
        'transactions': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


# ── Edit Transaction ──────────────────────────────────────────

@login_required
@role_required('admin', 'manager', 'teller')
def edit_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        new_amount_raw = request.POST.get('amount')
        new_timestamp_raw = request.POST.get('timestamp')
        new_notes = request.POST.get('notes', '')
        reason = request.POST.get('reason', '')

        try:
            new_amount = Decimal(new_amount_raw)
            from django.utils.dateparse import parse_datetime
            new_timestamp = parse_datetime(new_timestamp_raw) or tx.timestamp

            if new_amount <= 0:
                messages.error(request, 'Amount must be greater than zero.')
            else:
                account = tx.account
                old_amount = tx.amount

                # Reverse old effect and apply new amount on balance
                if tx.transaction_type == 'deposit' or tx.transaction_type == 'transfer_in':
                    account.balance -= old_amount
                    account.balance += new_amount
                elif tx.transaction_type == 'withdrawal' or tx.transaction_type == 'transfer_out':
                    account.balance += old_amount
                    account.balance -= new_amount

                account.save()

                # Log the edit
                TransactionEditLog.objects.create(
                    transaction=tx,
                    edited_by=request.user,
                    old_amount=old_amount,
                    new_amount=new_amount,
                    old_timestamp=tx.timestamp,
                    new_timestamp=new_timestamp,
                    old_notes=tx.notes,
                    new_notes=new_notes,
                    reason=reason
                )

                tx.amount = new_amount
                tx.timestamp = new_timestamp
                tx.notes = new_notes
                tx.is_edited = True
                tx.save()
                log_activity(
                user=request.user,
                action='transaction_edited',
                description=f'Transaction #{tx.pk} edited. Amount changed from {old_amount} to {new_amount} TZS.',
                request=request)

                messages.success(request, 'Transaction updated successfully.')
                return redirect(transactions_home(request.user))

        except Exception as e:
            messages.error(request, f'Error updating transaction: {e}')

    edit_logs = tx.edit_logs.select_related('edited_by').order_by('-edited_at')

    return render(request, 'banking/edit_transaction.html', {
        'tx': tx,
        'edit_logs': edit_logs,
        'timestamp_str': tx.timestamp.strftime('%Y-%m-%dT%H:%M'),
    })


# ── Delete Transaction ────────────────────────────────────────

@login_required
@role_required('admin', 'manager', 'teller')
def delete_transaction(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        account = tx.account

        # Reverse the balance effect
        if tx.transaction_type in ['deposit', 'transfer_in']:
            account.balance -= tx.amount
        elif tx.transaction_type in ['withdrawal', 'transfer_out']:
            account.balance += tx.amount

        account.save()
        log_activity(
        user=request.user,
        action='transaction_deleted',
        description=f'Transaction #{tx.pk} of TZS {tx.amount:,.2f} deleted from account {account.account_number}.',
        request=request)
        tx.delete()

        messages.success(request, 'Transaction deleted and balance reversed.')
        return redirect(transactions_home(request.user))

    return render(request, 'banking/delete_transaction.html', {'tx': tx})


# ── Account Statement ─────────────────────────────────────────

@login_required
@role_required('admin', 'manager', 'teller')
def account_statement(request, pk):
    account = get_object_or_404(BankAccount, pk=pk)
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    transactions = account.transactions.order_by('timestamp')

    if date_from:
        transactions = transactions.filter(timestamp__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(timestamp__date__lte=date_to)

    # Calculate running balance
    running = []
    balance = Decimal('0.00')
    for tx in transactions:
        if tx.transaction_type in ['deposit', 'transfer_in']:
            balance += tx.amount
        else:
            balance -= tx.amount
        running.append({'tx': tx, 'balance_after': balance})

    return render(request, 'banking/account_statement.html', {
        'account': account,
        'running': running,
        'date_from': date_from,
        'date_to': date_to,
        'today': timezone.now().date(),
    })


# ── Transaction Receipt ───────────────────────────────────────

@login_required
@role_required('admin', 'manager', 'teller')
def transaction_receipt(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    return render(request, 'banking/transaction_receipt.html', {'tx': tx})
