import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import main

@pytest.fixture
def client(tmp_path, monkeypatch):
    tmp_db = tmp_path / "test.db"

    TEST_DB_URL = f"sqlite+aiosqlite:///{tmp_db}"

    test_engine = create_async_engine(TEST_DB_URL)

    TestSessionLocal = async_sessionmaker(
        bind = test_engine,
        autoflush = False,
        autocommit = False
    )

    test_upload_dir = tmp_path / "uploads"

    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(main, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(main, "UPLOAD_DIR", str(test_upload_dir))

    print(tmp_path)
    print("\n", tmp_db)
    print("\n", test_upload_dir)

    with TestClient(main.app) as test_client:
        yield test_client