from app.db.session import SessionLocal
from app.services.cleanup_service import CleanupService


def main() -> None:
    with SessionLocal() as db:
        result = CleanupService(db).run()

    print(
        "cleanup_completed "
        f"expired_marked={result.expired_marked} "
        f"challenges_deleted={result.challenges_deleted} "
        f"audit_logs_deleted={result.audit_logs_deleted}"
    )


if __name__ == "__main__":
    main()
