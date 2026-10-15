import pytest
from backend.app import create_app
from backend.app.extensions import db
from backend.app.services.auth.auth_service import AuthService


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_a(app):
    user = AuthService.register_user("user_a@example.com", "Password123!", "User Alpha")
    token, _ = AuthService.authenticate_user("user_a@example.com", "Password123!")
    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }


@pytest.fixture
def user_b(app):
    user = AuthService.register_user("user_b@example.com", "Password123!", "User Beta")
    token, _ = AuthService.authenticate_user("user_b@example.com", "Password123!")
    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }
