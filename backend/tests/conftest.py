import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import db as db_module
from app.core.security import hash_password
from app.main import app
from app.models.department import Department
from app.models.user import RoleName, User

TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db_module.Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        db_module.Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db_module.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    def _make_user(email: str, role: RoleName, department: Department | None = None, password: str = "test-password-123") -> User:
        user = User(
            email=email,
            full_name="Test User",
            role=role,
            hashed_password=hash_password(password),
            department_id=department.id if department else None,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make_user
