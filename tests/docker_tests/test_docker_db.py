import pytest
from sqlalchemy import create_engine, text

from .config import docker_settings


@pytest.mark.docker
def test_database_connection():
    engine = create_engine(docker_settings.DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.docker
@pytest.mark.skip(reason="Needs fixing")
def test_database_migrations_applied():
    engine = create_engine(docker_settings.DATABASE_URL)
    with engine.connect() as connection:
        tables = ["user", "homeworktask", "submission", "feedback"]
        for table in tables:
            result = connection.execute(
                text(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
                )
            )
            assert result.scalar(), f"Table {table} does not exist"
