"""Portable local-only launcher; shared Streamlit configuration stays cloud-ready."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _port(value):
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Port must be an integer.') from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError('Port must be between 1 and 65535.')
    return port


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run Student Success AI on this machine only.')
    parser.add_argument('--port', type=_port, default=8501)
    args = parser.parse_args(argv)
    command = [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app' / 'Home.py'),
               '--server.address', '127.0.0.1', '--server.port', str(args.port),
               '--server.headless', 'true']
    try:
        return subprocess.run(command, cwd=ROOT, check=False).returncode
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
