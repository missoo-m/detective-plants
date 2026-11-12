import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = sorted(p for p in (ROOT / "services").iterdir() if (p / "app").is_dir())
GATEWAY = ROOT / "gateway"
COMMANDS = {
    "init": (SERVICES, [sys.executable, "-m", "app.main", "--init-only"]),
    "test": (SERVICES + [GATEWAY], [sys.executable, "-m", "pytest", "-q"]),
}


def run_each(command: str) -> int:
    projects, cmd = COMMANDS[command]
    failed = []
    for project in projects:
        print(f"\n=== {project.name} ===", flush=True)
        if subprocess.run(cmd, cwd=project).returncode != 0:
            failed.append(project.name)
    print("\nОшибки в проектах:" if failed else "\nВсе проекты выполнены успешно", ", ".join(failed))
    return 1 if failed else 0


def start_all() -> int:
    processes = []

    def pump(name: str, process: subprocess.Popen) -> None:
        for line in process.stdout:
            print(f"[{name}] {line.rstrip()}", flush=True)

    env = dict(os.environ, PYTHONUNBUFFERED="1")
    launches = [(p.name, p, [sys.executable, "-m", "app.main"]) for p in SERVICES]
    launches.append(("gateway", GATEWAY, [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"]))
    for name, cwd, cmd in launches:
        process = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        processes.append((name, process))
        threading.Thread(target=pump, args=(name, process), daemon=True).start()
    print("Запущено процессов:", len(processes), "— GraphiQL: http://localhost:8000/graphql, Ctrl+C — остановка")
    try:
        while all(p.poll() is None for _, p in processes):
            time.sleep(1)
        dead = [n for n, p in processes if p.poll() is not None]
        print("Процесс завершился:", ", ".join(dead))
    except KeyboardInterrupt:
        pass
    for _, process in processes:
        if process.poll() is None:
            process.terminate()
    for _, process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
    return 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) == 2 else None
    if command == "gen":
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_proto.py")]).returncode
    if command == "start":
        return start_all()
    if command in COMMANDS:
        return run_each(command)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
