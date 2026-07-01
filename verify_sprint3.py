import os
import django
import sys
import secrets
from unittest.mock import patch, MagicMock

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "futb_events.settings")
django.setup()

from django.test import Client
from django.utils import timezone
from core.models import User, Event, Ticket, Payment, Interest

def check(label, condition):
    if condition:
        print(f"  [PASS] {label}")
    else:
        print(f"  [FAIL] {label}")
        sys.exit(1)

# Clean up database for clean testing
User.objects.filter(email__contains="test_s3_").delete()
Event.objects.filter(title__contains="Sprint 3 Test").delete()

print("\n=======================================================")
print("  SPRINT 3 - TICKETING MODULE VERIFICATION")
print("=======================================================")

# Setup test users
print("\n[1] Creating test users...")
student1 = User.objects.create_user(
    username="test_s3_student1@futb.edu",
    email="test_s3_student1@futb.edu",
    first_name="Jane",
    last_name="Doe",
    role="student",
    password="Password123!"
)
student2 = User.objects.create_user(
    username="test_s3_student2@futb.edu",
    email="test_s3_student2@futb.edu",
    first_name="John",
    last_name="Doe",
    role="student",
    password="Password123!"
)
organiser = User.objects.create_user(
    username="test_s3_organiser@futb.edu",
    email="test_s3_organiser@futb.edu",
    role="organiser",
    password="Password123!"
)

# Setup test events
print("[2] Creating test events...")
free_event = Event.objects.create(
    organiser=organiser,
    title="Sprint 3 Test Free Event",
    description="A free campus seminar",
    category="academic",
    date_time=timezone.now() + timezone.timedelta(days=2),
    venue="Hall A",
    capacity=1,  # low capacity to test "fully booked" limit
    event_type="free",
    ticket_price=0.00,
    status="published"
)
paid_event = Event.objects.create(
    organiser=organiser,
    title="Sprint 3 Test Paid Event",
    description="Paid concert",
    category="cultural",
    date_time=timezone.now() + timezone.timedelta(days=3),
    venue="Sports Complex",
    capacity=50,
    event_type="paid",
    ticket_price=1500.00,
    status="published"
)

# Login clients and get JWT tokens
client = Client()

def get_tokens(email):
    res = client.post("/api/auth/login/", {"email": email, "password": "Password123!"}, content_type="application/json")
    return res.json()["access"]

stu1_token = get_tokens(student1.email)
stu2_token = get_tokens(student2.email)

# Helper headers
auth_headers_stu1 = {"HTTP_AUTHORIZATION": f"Bearer {stu1_token}"}
auth_headers_stu2 = {"HTTP_AUTHORIZATION": f"Bearer {stu2_token}"}

# ── PART A: FREE REGISTRATION ───────────────────────────────────────────
print("\n[PART A] Testing Free Event Registration...")

# Test 1: Successful Registration
res = client.post(f"/api/events/{free_event.id}/register/", **auth_headers_stu1)
check("Register free event returns 201", res.status_code == 201)
data = res.json()
check("Contains event details (nested)", data["event"]["title"] == free_event.title)
check("Contains ticket_type='free'", data["ticket_type"] == "free")
check("Contains active status", data["status"] == "active")
check("Contains base64 QR code image string", data["qr_code_image"].startswith("data:image/png;base64,"))

# Test 2: Double Registration Rejected
res = client.post(f"/api/events/{free_event.id}/register/", **auth_headers_stu1)
check("Duplicate registration returns 400", res.status_code == 400)
print(f"DEBUG - duplicate registration response: {res.json()}")
check("Duplicate message returned", "already registered" in res.json().get("detail", "").lower())

# Test 3: Capacity Limit Checked (Capacity is 1, stu1 registered, so stu2 should be blocked)
res = client.post(f"/api/events/{free_event.id}/register/", **auth_headers_stu2)
check("Fully booked returns 400", res.status_code == 400)
check("Fully booked message returned", "fully booked" in res.json().get("detail", "").lower())

# Test 4: My Tickets View
res = client.get("/api/tickets/my/", **auth_headers_stu1)
check("My tickets returns 200", res.status_code == 200)
check("My tickets returns correct ticket count", len(res.json()) == 1)

# ── PART B: PAID REGISTRATION ───────────────────────────────────────────
print("\n[PART B] Testing Paid Flow with Mock Paystack...")

# Mocking Paystack API Responses
mock_initiate_response = MagicMock()
mock_initiate_response.json.return_value = {
    "status": True,
    "message": "Authorization URL created",
    "data": {
        "authorization_url": "https://checkout.paystack.com/mock_auth_url",
        "reference": "mock_ref_s3_12345"
    }
}

mock_verify_response = MagicMock()
mock_verify_response.json.return_value = {
    "status": True,
    "message": "Verification successful",
    "data": {
        "status": "success",
        "reference": "mock_ref_s3_12345",
        "amount": 150000
    }
}

# Test 5: Initiate Payment
with patch("requests.post", return_value=mock_initiate_response):
    res = client.post(f"/api/events/{paid_event.id}/pay/", **auth_headers_stu1)
    check("Initiate payment returns 200", res.status_code == 200)
    pay_data = res.json()
    check("Contains authorization_url", "authorization_url" in pay_data)
    check("Contains reference", pay_data["reference"] == "mock_ref_s3_12345")

    # Confirm Payment object is saved as pending
    payment = Payment.objects.get(paystack_ref="mock_ref_s3_12345")
    check("Payment is stored with pending status", payment.status == "pending")

# Test 6: Verify Payment (and create Ticket)
with patch("requests.get", return_value=mock_verify_response):
    res = client.get("/api/payments/verify/mock_ref_s3_12345/", **auth_headers_stu1)
    check("Verify payment returns 201 on success", res.status_code == 201)
    ticket_data = res.json()
    check("Paid ticket returned with paid ticket_type", ticket_data["ticket_type"] == "paid")
    check("Paid ticket has base64 QR code image", ticket_data["qr_code_image"].startswith("data:image/png;base64,"))

    # Confirm Payment updated to success
    payment.refresh_from_db()
    check("Payment record updated to success", payment.status == "success")
    check("Payment links to the newly created ticket", payment.ticket is not None)

# Test 7: Idempotency Verification
with patch("requests.get", return_value=mock_verify_response):
    # Call verify a second time for the same reference
    res2 = client.get("/api/payments/verify/mock_ref_s3_12345/", **auth_headers_stu1)
    check("Second verify call returns 200 (idempotent)", res2.status_code == 200)
    check("Returns same ticket ID", res2.json()["id"] == ticket_data["id"])
    
    # Verify no duplicate ticket was created in the database
    ticket_count = Ticket.objects.filter(event=paid_event, user=student1).count()
    check("Only one ticket exists in the database", ticket_count == 1)

print("\n=======================================================")
print("  ALL SPRINT 3 VERIFICATION TESTS PASSED!")
print("=======================================================")
