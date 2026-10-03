from .database import init_db
from .seed import seed, sid
from .service import SatelliteService


def main() -> None:
    init_db()
    print("Тестовые данные добавлены" if seed() else "Тестовые данные уже есть")

    service = SatelliteService()
    for f in service.list_fields(str(sid("user-1"))):
        values = [m.ndvi_value for m in service.list_measurements(f.id)]
        print(f"  {f.name}: NDVI {values}")
    for a in service.list_alerts():
        print(f"Предупреждение [{a.type}]: {a.message}")


if __name__ == "__main__":
    main()
