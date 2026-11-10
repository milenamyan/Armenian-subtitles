"""Start the local HaySub server, or reuse an instance already on port 8000."""
import json
import socket
import sys
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def main():
    root=Path(__file__).resolve().parent
    os.chdir(root)
    from dotenv import load_dotenv
    load_dotenv(root/'.env')
    address = ('127.0.0.1', 8000)
    with socket.socket() as probe:
        occupied = probe.connect_ex(address) == 0
    if occupied:
        try:
            with urlopen('http://127.0.0.1:8000/openapi.json', timeout=5) as response:
                schema = json.load(response)
            if schema.get('info', {}).get('title') == 'HaySub':
                route = schema.get('paths', {}).get('/api/subtitle-files/{identity}', {})
                if 'delete' not in route:
                    print('An older HaySub server is running. Stop it with Ctrl+C in its terminal, then run this command again.')
                    return 1
                print('HaySub is already running: http://127.0.0.1:8000')
                print('To load code or .env changes, stop it with Ctrl+C in its terminal first.')
                return 0
        except (URLError, TimeoutError, ValueError, OSError):
            pass
        print('Port 8000 is occupied by another service. Stop that service before starting HaySub.')
        return 1

    from app.serve import main as serve
    serve()
    return 0


if __name__ == '__main__':
    sys.exit(main())
