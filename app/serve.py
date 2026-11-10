"""Container entry point: initialize the mounted disk, then run as haysub."""
import os
from pathlib import Path
import subprocess
import sys
import threading


def main():
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        import pwd
        user = pwd.getpwnam('haysub')
        database = Path(os.environ.get('HAYSUB_DB', '/var/data/haysub.sqlite3'))
        database.parent.mkdir(parents=True, exist_ok=True)
        os.chown(database.parent, user.pw_uid, user.pw_gid)
        for filename in (str(database), str(database)+'-wal', str(database)+'-shm', str(database)+'-journal'):
            if Path(filename).exists():
                os.chown(filename, user.pw_uid, user.pw_gid)
        os.setgroups([])
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
    import uvicorn
    stop=threading.Event();children=[]
    def supervise():
        # A separate worker process shares this instance's persistent metadata disk.
        while not stop.is_set():
            child=subprocess.Popen([sys.executable,'-m','app.media_worker']);children.append(child)
            while child.poll() is None and not stop.wait(2):pass
            if stop.is_set():
                child.terminate()
                try:child.wait(timeout=10)
                except subprocess.TimeoutExpired:child.kill();child.wait()
            children.remove(child)
            if not stop.is_set():stop.wait(5)
    if os.getenv('HAYSUB_MEDIA_WORKER_ENABLED')=='1' and os.getenv('HAYSUB_MEDIA_STORAGE'):
        threading.Thread(target=supervise,daemon=True).start()
    try:uvicorn.run('app.main:app', host='0.0.0.0' if os.getenv('HAYSUB_PUBLIC')=='1' else '127.0.0.1', port=int(os.getenv('PORT','8000')), workers=1,access_log=False)
    finally:
        stop.set()
        for child in list(children):
            if child.poll() is None:child.terminate()


if __name__ == '__main__':
    main()
