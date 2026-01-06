"""Authentication endpoint tests."""
import pytest
from fastapi.testclient import TestClient

from api.tests.conftest import TEST_USER_PASSWORD


class TestRegister:
    """Tests for POST /api/auth/register"""

    def test_register_user(self, client: TestClient):
        """Test successful user registration."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepass123",
            "name": "New User"
        })

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
        assert data["user"]["role"] == "user"
        assert "id" in data["user"]

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration fails with existing email."""
        response = client.post("/api/auth/register", json={
            "email": test_user.email,
            "password": "anotherpass",
            "name": "Duplicate User"
        })

        assert response.status_code == 400

    def test_register_weak_password(self, client: TestClient):
        """Test registration fails with short password."""
        response = client.post("/api/auth/register", json={
            "email": "weak@example.com",
            "password": "12345",
            "name": "Weak Password User"
        })

        assert response.status_code == 400

    def test_register_invalid_email(self, client: TestClient):
        """Test registration fails with invalid email format."""
        response = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "validpass123",
            "name": "Invalid Email User"
        })

        assert response.status_code == 422  # Pydantic validation


class TestLogin:
    """Tests for POST /api/auth/login"""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login with valid credentials."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": TEST_USER_PASSWORD
        })

        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == test_user.email

    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """Test login fails with wrong password."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword"
        })

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login fails for non-existent user."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })

        assert response.status_code == 401

    def test_login_demo_mode(self, client: TestClient):
        """Test demo mode login (password='demo' works for any email)."""
        response = client.post("/api/auth/login", json={
            "email": "demo@test.com",
            "password": "demo"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "demo@test.com"
        assert data["user"]["role"] == "annotator"


class TestGetCurrentUser:
    """Tests for GET /api/auth/me"""

    def test_get_current_user_authenticated(self, client: TestClient, auth_headers, test_user):
        """Test /me returns user info with valid token."""
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name

    def test_get_current_user_unauthenticated(self, client: TestClient):
        """Test /me returns 401 without token."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test /me returns 401 with malformed token."""
        response = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })

        assert response.status_code == 401

    def test_get_current_user_no_bearer_prefix(self, client: TestClient, auth_token):
        """Test /me returns 401 when Bearer prefix is missing."""
        response = client.get("/api/auth/me", headers={
            "Authorization": auth_token  # Missing "Bearer "
        })

        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/auth/logout"""

    def test_logout(self, client: TestClient):
        """Test logout endpoint returns success."""
        response = client.post("/api/auth/logout")

        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"
