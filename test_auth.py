import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from django.test import Client
import json

def run_tests():
    client = Client()

    # ── 6a. Register ────────────────────────────────────────────────────────
    print("=" * 60)
    print("6a. Registering a new test user (role=student, 2 interests)")
    print("=" * 60)

    from core.models import User
    User.objects.filter(email="teststudent@futb.edu").delete()

    register_payload = {
        "email": "teststudent@futb.edu",
        "password": "securepass123",
        "full_name": "Ada Lovelace",
        "department": "Computer Science",
        "faculty": "Science",
        "interests": ["academic", "technology"]
    }
    res = client.post(
        '/api/auth/register/',
        data=json.dumps(register_payload),
        content_type='application/json'
    )
    print(f"Status : {res.status_code}  (expected 201)")
    print(f"Body   : {json.dumps(res.json(), indent=2)}")
    print()

    # ── 6b. Login ────────────────────────────────────────────────────────────
    print("=" * 60)
    print("6b. Logging in – expecting access + refresh + role + full_name")
    print("=" * 60)

    # SimpleJWT TokenObtainPair uses 'username' field internally.
    # Since we stored email as username at registration, we pass email here.
    login_payload = {
        "username": "teststudent@futb.edu",
        "password": "securepass123"
    }
    res = client.post(
        '/api/auth/login/',
        data=json.dumps(login_payload),
        content_type='application/json'
    )
    print(f"Status : {res.status_code}  (expected 200)")
    body = res.json()
    access_token = body.get("access", "")
    print(f"access token present : {bool(access_token)}")
    print(f"refresh token present: {bool(body.get('refresh'))}")
    print(f"role returned        : {body.get('role')}")
    print(f"full_name returned   : {body.get('full_name')}")
    print()

    # ── 6c. Profile WITH token ───────────────────────────────────────────────
    print("=" * 60)
    print("6c. GET /api/auth/profile/  WITH valid access token")
    print("=" * 60)
    res = client.get(
        '/api/auth/profile/',
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )
    print(f"Status : {res.status_code}  (expected 200)")
    print(f"Body   : {json.dumps(res.json(), indent=2)}")
    print()

    # ── 6d. Profile WITHOUT token ────────────────────────────────────────────
    print("=" * 60)
    print("6d. GET /api/auth/profile/  WITHOUT any token")
    print("=" * 60)
    res = client.get('/api/auth/profile/')
    print(f"Status : {res.status_code}  (expected 401)")
    print(f"Body   : {res.json()}")
    print()

    # ── 6e. Profile with garbage token ───────────────────────────────────────
    print("=" * 60)
    print("6e. GET /api/auth/profile/  with a garbage token")
    print("=" * 60)
    res = client.get(
        '/api/auth/profile/',
        HTTP_AUTHORIZATION="Bearer totally.invalid.garbage_token"
    )
    print(f"Status : {res.status_code}  (expected 401)")
    print(f"Body   : {res.json()}")
    print()

    print("=" * 60)
    print("ALL CHECKS COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    run_tests()
