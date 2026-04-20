from app.db.session import SessionLocal
from app.services.seed import seed_database


def main() -> None:
    with SessionLocal() as db:
        seed_database(db)


if __name__ == "__main__":
    main()
