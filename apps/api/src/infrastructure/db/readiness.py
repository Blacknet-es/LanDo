from sqlalchemy import Connection, text


def verify_required_extensions(connection: Connection) -> None:
    vector_version = connection.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
    ).scalar_one_or_none()
    if vector_version is None:
        raise RuntimeError(
            "PostgreSQL pgvector is not enabled. Apply the database migrations in apps/db/migrations."
        )

    migration_table_exists = connection.execute(
        text("SELECT to_regclass('schema_migrations')")
    ).scalar_one()
    if migration_table_exists is None:
        raise RuntimeError(
            "The database schema is not up to date. Apply the migrations in apps/db/migrations."
        )
    migration_applied = connection.execute(
        text("SELECT 1 FROM schema_migrations WHERE version = '001_multi_tenant'")
    ).scalar_one_or_none()
    if migration_applied is None:
        raise RuntimeError(
            "The database schema is not up to date. Apply the migrations in apps/db/migrations."
        )
