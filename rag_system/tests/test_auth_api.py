def test_register_and_login_flow(client):
    # 1. Register new user
    r1 = client.post("/api/v1/auth/register", json={
        "email": "fresh_user@example.com",
        "password": "Password123!",
        "full_name": "Fresh User"
    })
    assert r1.status_code == 201
    assert r1.get_json()["success"] is True
    token = r1.get_json()["data"]["access_token"]
    assert token

    # 2. Duplicate registration fails
    r_dup = client.post("/api/v1/auth/register", json={
        "email": "fresh_user@example.com",
        "password": "Password123!"
    })
    assert r_dup.status_code == 400
    assert "already exists" in r_dup.get_json()["error"]["message"]

    # 3. Successful login
    r_login = client.post("/api/v1/auth/login", json={
        "email": "fresh_user@example.com",
        "password": "Password123!"
    })
    assert r_login.status_code == 200
    assert r_login.get_json()["success"] is True

    # 4. Failed login with wrong password
    r_bad = client.post("/api/v1/auth/login", json={
        "email": "fresh_user@example.com",
        "password": "WrongPassword!"
    })
    assert r_bad.status_code == 401

    # 5. Protected profile route
    r_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r_me.status_code == 200
    assert r_me.get_json()["data"]["user"]["email"] == "fresh_user@example.com"

    # 6. Unauthenticated access rejected
    r_no_auth = client.get("/api/v1/auth/me")
    assert r_no_auth.status_code == 401
