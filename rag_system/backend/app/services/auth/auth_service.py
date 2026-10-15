import re
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from backend.app.extensions import db
from backend.app.models.user import User

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ph = PasswordHasher()


class AuthService:
    """Service handling user registration, authentication, and JWT lifecycle."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Secure password hashing using Argon2id with fallback to Werkzeug PBKDF2."""
        try:
            return ph.hash(password)
        except Exception:
            return generate_password_hash(password, method="pbkdf2:sha256")

    @staticmethod
    def verify_password(password_hash: str, password: str) -> bool:
        """Verify candidate password against stored Argon2/Werkzeug hash."""
        if password_hash.startswith("$argon2"):
            try:
                return ph.verify(password_hash, password)
            except VerifyMismatchError:
                return False
            except Exception:
                return False
        return check_password_hash(password_hash, password)

    @classmethod
    def register_user(cls, email: str, password: str, full_name: str = None) -> User:
        """Register a new user account with validation."""
        email = email.strip().lower()
        if not email or not EMAIL_REGEX.match(email):
            raise ValueError("Invalid email format.")

        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")

        existing = User.query.filter_by(email=email).first()
        if existing:
            raise ValueError("An account with this email already exists.")

        user = User(
            email=email,
            password_hash=cls.hash_password(password),
            full_name=full_name.strip() if full_name else None,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return user

    @classmethod
    def authenticate_user(cls, email: str, password: str) -> tuple[str, User]:
        """Authenticate user credentials and generate a JWT access token."""
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not cls.verify_password(user.password_hash, password):
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Account is disabled. Please contact support.")

        # Additional claims stored in token
        additional_claims = {
            "email": user.email,
            "full_name": user.full_name,
        }
        access_token = create_access_token(identity=user.id, additional_claims=additional_claims)
        return access_token, user
