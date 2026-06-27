"""
Independent end-to-end verification of Sprint 1 Authentication Module.
Tests against the live Django dev server at http://127.0.0.1:8000
"""
import urllib.request
import urllib.error
import json
import sys

BASE = "http://127.0.0.1:8000"
PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def post(path, body=None, token=None):
    data = json.dumps(body).encode() if body else b""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}

def check(label, condition, detail=""):
    icon = PASS if condition else FAIL
    results.append(condition)
    print(f"  {icon}  {label}")
    if detail:
        print(f"         {detail}")

print()
print("=" * 65)
print("  SPRINT 1 - AUTHENTICATION MODULE - END-TO-END VERIFICATION")
print("=" * 65)

# ── Clean up any previous test user ─────────────────────────────────────────
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()
from core.models import User
User.objects.filter(email="verify@futb.edu").delete()

# ────────────────────────────────────────────────────────────────────────────
print("\n[1] REGISTER - POST /api/auth/register/")
print("-" * 65)

# 1a. Valid registration
status, body = post("/api/auth/register/", {
    "email": "verify@futb.edu",
    "password": "strongpass99",
    "full_name": "Amara Obi",
    "department": "Computer Science",
    "faculty": "Science & Technology",
    "interests": ["academic", "technology"]
})
check("Returns 201 Created", status == 201, f"Got {status}")
check("Returns id field", "id" in body, str(body.get("id")))
check("Returns email field", body.get("email") == "verify@futb.edu")
check("Returns full_name", body.get("full_name") == "Amara Obi")
check("Returns role = student", body.get("role") == "student")
check("Returns interests list", body.get("interests") == ["academic", "technology"], str(body.get("interests")))
check("Does NOT expose password", "password" not in body)

# 1b. Duplicate email rejected
status2, body2 = post("/api/auth/register/", {
    "email": "verify@futb.edu",
    "password": "strongpass99",
    "full_name": "Duplicate User",
    "department": "X",
    "faculty": "Y",
    "interests": ["sports"]
})
check("Duplicate email returns 400", status2 == 400, f"Got {status2}")

# 1c. Short password rejected
status3, _ = post("/api/auth/register/", {
    "email": "short@futb.edu",
    "password": "abc",        # only 3 chars
    "full_name": "Short Pass",
    "department": "X",
    "faculty": "Y",
    "interests": ["sports"]
})
check("Password < 8 chars returns 400", status3 == 400, f"Got {status3}")

# 1d. Invalid interest category rejected
status4, _ = post("/api/auth/register/", {
    "email": "bad@futb.edu",
    "password": "validpass99",
    "full_name": "Bad Interest",
    "department": "X",
    "faculty": "Y",
    "interests": ["basketball"]   # not in choices
})
check("Invalid interest category returns 400", status4 == 400, f"Got {status4}")

# ────────────────────────────────────────────────────────────────────────────
print("\n[2] LOGIN - POST /api/auth/login/")
print("-" * 65)

status, body = post("/api/auth/login/", {
    "username": "verify@futb.edu",
    "password": "strongpass99"
})
check("Returns 200 OK", status == 200, f"Got {status}")
check("Returns access token", bool(body.get("access")))
check("Returns refresh token", bool(body.get("refresh")))
check("Returns role in response", body.get("role") == "student", str(body.get("role")))
check("Returns full_name in response", body.get("full_name") == "Amara Obi", str(body.get("full_name")))

access_token = body.get("access", "")
refresh_token = body.get("refresh", "")

# Wrong password
status_wp, _ = post("/api/auth/login/", {"username": "verify@futb.edu", "password": "wrongpassword"})
check("Wrong password returns 401", status_wp == 401, f"Got {status_wp}")

# ────────────────────────────────────────────────────────────────────────────
print("\n[3] PROFILE - GET /api/auth/profile/")
print("-" * 65)

# With valid token
status, body = get("/api/auth/profile/", token=access_token)
check("With valid token -> 200", status == 200, f"Got {status}")
check("Profile contains email", body.get("email") == "verify@futb.edu")
check("Profile contains interests", body.get("interests") == ["academic", "technology"])
check("Profile does NOT expose password", "password" not in body)

# Without token
status_no, _ = get("/api/auth/profile/")
check("Without token -> 401", status_no == 401, f"Got {status_no}")

# Garbage token
status_bad, body_bad = get("/api/auth/profile/", token="garbage.token.xyz")
check("Garbage token -> 401", status_bad == 401, f"Got {status_bad}")

# ────────────────────────────────────────────────────────────────────────────
print("\n[4] TOKEN REFRESH - POST /api/auth/login/refresh/")
print("-" * 65)

status, body = post("/api/auth/login/refresh/", {"refresh": refresh_token})
check("Valid refresh -> 200 with new access token", status == 200 and bool(body.get("access")), f"Got {status}")

# Bad refresh token
status_bad, _ = post("/api/auth/login/refresh/", {"refresh": "bad.refresh.token"})
check("Invalid refresh token -> 401", status_bad == 401, f"Got {status_bad}")

# ────────────────────────────────────────────────────────────────────────────
print("\n[5] LOGOUT - POST /api/auth/logout/")
print("-" * 65)

# Get a fresh login to get a valid refresh token for logout
_, login_body = post("/api/auth/login/", {"username": "verify@futb.edu", "password": "strongpass99"})
fresh_access = login_body.get("access", "")
fresh_refresh = login_body.get("refresh", "")

status, _ = post("/api/auth/logout/", {"refresh": fresh_refresh}, token=fresh_access)
check("Logout returns 205 Reset Content", status == 205, f"Got {status}")

# Try using the blacklisted refresh token after logout
status_reuse, _ = post("/api/auth/login/refresh/", {"refresh": fresh_refresh})
check("Blacklisted refresh token rejected -> 401", status_reuse == 401, f"Got {status_reuse}")

# Logout without token → 401
status_nologout, _ = post("/api/auth/logout/", {"refresh": fresh_refresh})
check("Logout without auth token -> 401", status_nologout == 401, f"Got {status_nologout}")

# ────────────────────────────────────────────────────────────────────────────
print("\n[6] PERMISSIONS.PY - RBAC Classes Importable")
print("-" * 65)

try:
    from core.permissions import IsStudent, IsOrganiser, IsAdminRole
    check("IsStudent importable", True)
    check("IsOrganiser importable", True)
    check("IsAdminRole importable", True)
    # Verify they are proper DRF permission classes
    from rest_framework.permissions import BasePermission
    check("IsStudent extends BasePermission", issubclass(IsStudent, BasePermission))
    check("IsOrganiser extends BasePermission", issubclass(IsOrganiser, BasePermission))
    check("IsAdminRole extends BasePermission", issubclass(IsAdminRole, BasePermission))
except Exception as e:
    check("Permissions importable", False, str(e))

# ────────────────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
failed = total - passed

print()
print("=" * 65)
print(f"  RESULT: {passed}/{total} checks passed  |  {failed} failed")
if failed == 0:
    print("  >> ALL CHECKS PASSED -- Sprint 1 Authentication is VERIFIED")
else:
    print("  !! SOME CHECKS FAILED -- Review above output")
print("=" * 65)
sys.exit(0 if failed == 0 else 1)
