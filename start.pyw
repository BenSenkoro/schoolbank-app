import subprocess
import sys
import os
import time
import webbrowser
import threading
def start_server():
    # Auto backup on startup
    try:
        import sys
        sys.path.insert(0, BASE_DIR)
        from backup.auto_backup import auto_backup
        auto_backup()
    except Exception:
        pass  # Don't stop server if backup fails

    if is_server_running():
        webbrowser.open(URL)
        return
    ...
# ── Paths ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(BASE_DIR, 'venv', 'Scripts', 'python.exe')
MANAGE_PY = os.path.join(BASE_DIR, 'manage.py')
PID_FILE = os.path.join(BASE_DIR, 'server.pid')
PORT = '8000'
URL = f'http://127.0.0.1:{PORT}/login/'

def show_notification(title, message):
    """Show a Windows toast notification."""
    try:
        import ctypes
        # Simple messagebox as fallback notification
        # We use a thread so it doesn't block the server
        def _notify():
            ctypes.windll.user32.MessageBoxW(
                0,
                message,
                title,
                0x40 | 0x1000  # MB_ICONINFORMATION | MB_SYSTEMMODAL
            )
        # Don't show blocking messagebox — just print to log
        pass
    except:
        pass


def open_browser():
    """Wait for server to start then open browser."""
    time.sleep(3)  # Give Django 3 seconds to start
    webbrowser.open(URL)


def is_server_running():
    """Check if server is already running."""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = f.read().strip()
        if pid:
            # Check if process is still alive
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}'],
                capture_output=True, text=True
            )
            if pid in result.stdout:
                return True
    return False


def start_server():
    if is_server_running():
        # Server already running, just open browser
        webbrowser.open(URL)
        return

    # Start Django server
    process = subprocess.Popen(
        [VENV_PYTHON, MANAGE_PY, 'runserver', f'127.0.0.1:{PORT}', '--noreload'],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW  # No terminal window
    )

    # Save PID so we can stop it later
    with open(PID_FILE, 'w') as f:
        f.write(str(process.pid))

    # Open browser in background thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    # Keep script alive while server runs
    process.wait()


if __name__ == '__main__':
    start_server()