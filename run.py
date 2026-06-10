"""PromoStudio - Development Runner

Starts both the backend (FastAPI) and frontend (Vite) servers.
"""

import subprocess
import signal
import sys
import os

BANNER = """
\033[95m╔══════════════════════════════════════════╗
║           \033[1mPromoStudio\033[0m\033[95m                   ║
╠══════════════════════════════════════════╣
║  Backend:   http://localhost:8000       ║
║  Frontend:  http://localhost:5173       ║
╚══════════════════════════════════════════╝\033[0m
"""

processes: list[subprocess.Popen[bytes]] = []


def shutdown(signum: int, frame: object) -> None:
    print("\n\033[93mShutting down PromoStudio...\033[0m")
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            proc.kill()
    sys.exit(0)


def main() -> None:
    print(BANNER)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    # Start backend
    backend_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "backend.app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload",
        ],
        cwd=root_dir,
    )
    processes.append(backend_proc)
    print("\033[92m[+] Backend started on port 8000\033[0m")

    # Start frontend
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
    )
    processes.append(frontend_proc)
    print("\033[92m[+] Frontend started on port 5173\033[0m")

    # Wait for either process to exit
    try:
        while True:
            for proc in processes:
                retcode = proc.poll()
                if retcode is not None:
                    print(f"\033[91m[!] Process exited with code {retcode}\033[0m")
                    shutdown(signal.SIGTERM, None)
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    main()
