import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO = ROOT / "proto"
ALL = ["auth", "request", "expert", "recovery", "chat", "payment", "notification", "analytics", "admin", "satellite"]
NEEDS = {
    "auth": ["auth"], "request": ["request", "auth", "expert"], "expert": ["expert", "auth", "request"],
    "recovery": ["recovery", "notification"], "chat": ["chat"], "payment": ["payment", "auth", "request"],
    "notification": ["notification"], "analytics": ["analytics"], "admin": ["admin", "auth"], "satellite": ["satellite"],
}


def generate(project: Path, protos: list) -> None:
    out = project / "app" / "proto"
    out.mkdir(parents=True, exist_ok=True)
    (out / "__init__.py").touch()
    for name in protos:
        subprocess.run([sys.executable, "-m", "grpc_tools.protoc", f"-I{PROTO}", f"--python_out={out}",
                        f"--grpc_python_out={out}", str(PROTO / f"{name}.proto")], check=True)
        grpc_file = out / f"{name}_pb2_grpc.py"
        text = grpc_file.read_text(encoding="utf8")
        grpc_file.write_text(re.sub(r"^import (\w+_pb2) as (\w+)$", r"from . import \1 as \2", text, flags=re.M),
                             encoding="utf8")
    print(f"{project.relative_to(ROOT)}: {', '.join(protos)}")


def main() -> int:
    try:
        import grpc_tools  
    except ImportError:
        print("Установите grpcio-tools:  pip install -r requirements-dev.txt")
        return 1
    for service, protos in NEEDS.items():
        generate(ROOT / "services" / f"{service}-service", protos)
    generate(ROOT / "gateway", ALL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
