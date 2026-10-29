import os
import shutil
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import FileResponse, Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from accounts.utils import log_activity

BASE_DIR = settings.BASE_DIR
DB_PATH = BASE_DIR / 'db.sqlite3'
BACKUP_DIR = BASE_DIR / 'backups'


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


def get_backups():
    """Return list of backup files sorted by newest first."""
    if not BACKUP_DIR.exists():
        return []
    files = []
    for f in BACKUP_DIR.iterdir():
        if f.suffix == '.sqlite3':
            size_kb = round(f.stat().st_size / 1024, 1)
            modified = datetime.fromtimestamp(f.stat().st_mtime)
            files.append({
                'name': f.name,
                'size_kb': size_kb,
                'modified': modified,
            })
    return sorted(files, key=lambda x: x['modified'], reverse=True)


def find_backup(filename):
    """Return the path of a listed backup with exactly this name, or None.

    Matching against the real files (instead of joining the name onto BACKUP_DIR)
    means names like '..\\db.sqlite3' can never reach a file outside the folder.
    """
    if not BACKUP_DIR.exists():
        return None
    for f in BACKUP_DIR.iterdir():
        if f.name == filename and f.suffix == '.sqlite3' and f.is_file():
            return f
    return None


def do_backup(label='manual'):
    """Perform the actual backup."""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'mbonea_backup_{label}_{timestamp}.sqlite3'
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(DB_PATH, backup_path)
    return backup_name


@login_required
@role_required('admin')
def backup_home(request):
    backups = get_backups()
    return render(request, 'backup/backup_home.html', {
        'backups': backups,
        'backup_count': len(backups),
    })


@login_required
@role_required('admin')
def create_backup(request):
    if request.method == 'POST':
        try:
            backup_name = do_backup(label='manual')
            log_activity(
                user=request.user,
                action='backup',
                description=f'Manual backup created: {backup_name}',
                request=request
            )
            messages.success(request, f'Backup created successfully: {backup_name}')
        except Exception as e:
            messages.error(request, f'Backup failed: {e}')
    return redirect('backup')


@login_required
@role_required('admin')
def download_backup(request, filename):
    backup_path = find_backup(filename)
    if backup_path is None:
        raise Http404('Backup file not found.')
    return FileResponse(
        open(backup_path, 'rb'),
        as_attachment=True,
        filename=backup_path.name
    )


@login_required
@role_required('admin')
def delete_backup(request, filename):
    backup_path = find_backup(filename)
    if request.method == 'POST':
        if backup_path is not None:
            backup_path.unlink()
            messages.success(request, f'Backup "{backup_path.name}" deleted.')
        else:
            messages.error(request, 'Backup file not found.')
    return redirect('backup')