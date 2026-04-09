"""Tests for auth routes — POST /api/v1/auth/register and /login."""
from models.database import Athlete


def test_athlete_model_has_email_and_password_hash():
    """Athlete model declares email and password_hash columns."""
    mapper = Athlete.__mapper__
    assert "email" in mapper.columns
    assert "password_hash" in mapper.columns
