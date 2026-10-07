"""
    python scripts/run_all.py init    # создать таблицы и тестовые данные во всех БД 
    python scripts/run_all.py test    # прогнать тесты всех сервисов и gateway
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVICES = sorted(p for p in (ROOT / "services").iterdir() if (p / "app").is_dir())
COMMANDS = {
    "init": (SERVICES, [sys.executable, "-m", "app.main"]),
    "test": (SERVICES + [ROOT / "gateway"], [sys.executable, "-m", "pytest", "-q"]),
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        return 2
    projects, cmd = COMMANDS[sys.argv[1]]
    failed = []
    for project in projects:
        print(f"\n=== {project.name} ===", flush=True)
        if subprocess.run(cmd, cwd=project).returncode != 0:
            failed.append(project.name)
    print("\nОшибки в проектах:" if failed else "\nВсе проекты выполнены успешно", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
