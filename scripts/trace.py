import glob
import json
import os
import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("python scripts/trace.py <correlation_id> [каталог_журналов]")
        return 2
    wanted = sys.argv[1]
    directory = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "logs")
    lines = []
    for path in glob.glob(os.path.join(directory, "*.log")):
        with open(path, encoding="utf-8") as handle:
            for raw in handle:
                try:
                    record = json.loads(raw)
                except ValueError:
                    continue
                if record.get("correlation_id", "").startswith(wanted):
                    lines.append(record)
    if not lines:
        print(f"Записей с correlation_id={wanted} не найдено в {os.path.abspath(directory)}")
        return 1
    for record in sorted(lines, key=lambda r: r["time"]):
        print(f'{record["time"]} {record["level"]:<7} [{record["service"]:<20}] {record["logger"]}: {record["message"]}')
    print(f"\nСтрок: {len(lines)}, сервисов: {len({r['service'] for r in lines})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
