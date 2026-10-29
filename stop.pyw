import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(BASE_DIR, 'server.pid')


def stop_server():
    if not os.path.exists(PID_FILE):
        # Try to kill by port as fallback
        subprocess.run(
            'for /f "tokens=5" %a in (\'netstat -aon ^| find ":8000"\') do taskkill /F /PID %a',
            shell=True,
            capture_output=True
        )
        return

    with open(PID_FILE, 'r') as f:
        pid = f.read().strip()

    if pid:
        try:
            subprocess.run(
                ['taskkill', '/F', '/PID', pid],
                capture_output=True
            )
        except Exception:
            pass

    # Clean up PID file
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


if __name__ == '__main__':
    stop_server()