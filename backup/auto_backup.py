"""
Run this once to set up automatic daily backups.
It checks if a backup was made today — if not, makes one.
Call this from start.pyw on every startup.
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'db.sqlite3'
BACKUP_DIR = BASE_DIR / 'backups'


def auto_backup():
    """Make a backup if none exists for today."""
    BACKUP_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime('%Y%m%d')

    # Check if today's backup already exists
    existing = [f for f in BACKUP_DIR.iterdir() if today in f.name]
    if existing:
        return  # Already backed up today

    # Create today's backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'mbonea_backup_auto_{timestamp}.sqlite3'
    backup_path = BACKUP_DIR / backup_name
    shutil.copy2(DB_PATH, backup_path)

    # Keep only last 30 backups to save space
    all_backups = sorted(
        [f for f in BACKUP_DIR.iterdir() if f.suffix == '.sqlite3'],
        key=lambda x: x.stat().st_mtime
    )
    while len(all_backups) > 30:
        all_backups[0].unlink()
        all_backups.pop(0)


if __name__ == '__main__':
    auto_backup()