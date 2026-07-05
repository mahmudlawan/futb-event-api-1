import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from rest_framework.test import APIClient
from django.utils import timezone
from core.models import User, Event, Ticket

def run_all_checks():
    client = APIClient()
    
    # Use a unique hash each run to avoid stale data collisions
    unique_hash = f"partc_qr_{uuid.uuid4().hex[:12]}"
    
    # -- Setup Users --
    student, _ = User.objects.get_or_create(email="partc_student@futb.edu.ng", defaults={
        'username': 'partc_student@futb.edu.ng',
        'first_name': 'Ali', 'last_name': 'Bello',
        'role': 'student', 'password': 'testpassword123'
    })

    organiser, _ = User.objects.get_or_create(email="partc_organiser@futb.edu.ng", defaults={
        'username': 'partc_organiser@futb.edu.ng',
        'role': 'organiser', 'password': 'testpassword123'
    })

    admin_user, _ = User.objects.get_or_create(email="partc_admin@futb.edu.ng", defaults={
        'username': 'partc_admin@futb.edu.ng',
        'role': 'admin', 'password': 'testpassword123'
    })

    # -- Setup Event and Ticket --
    event = Event.objects.create(
        organiser=organiser,
        title="Sprint 5 Part C Test Event",
        description="Full integration test.",
        category="Technology",
        date_time=timezone.now(),
        venue="FUTB Tech Hall",
        capacity=200,
        event_type="free",
        status="upcoming"
    )

    ticket = Ticket.objects.create(
        user=student, event=event,
        qr_code_hash=unique_hash,
        ticket_type="free", status="active"
    )

    print("=" * 60)
    print("SPRINT 5 PART C -- FULL VERIFICATION TEST")
    print("=" * 60)

    # -- CHECK A --
    print("\n[A] Get valid QR code hash from existing active ticket")
    real_ticket = Ticket.objects.get(qr_code_hash=unique_hash)
    print(f"    DB qr_code_hash : {real_ticket.qr_code_hash}")
    print(f"    DB status       : {real_ticket.status}")
    assert real_ticket.status == "active", "FAIL: Ticket should be active"
    print("    PASS [OK]")

    # -- CHECK B --
    print("\n[B] Organiser scans valid ticket -> expect VALID, DB status -> 'used'")
    client.force_authenticate(user=organiser)
    res_b = client.post('/api/tickets/validate/', {"qr_code_hash": unique_hash}, format="json")
    print(f"    HTTP status     : {res_b.status_code}")
    print(f"    Response        : {dict(res_b.data)}")
    assert res_b.status_code == 200, "FAIL: Expected 200"
    assert res_b.data['status'] == "VALID", "FAIL: Expected VALID"
    db_ticket = Ticket.objects.get(qr_code_hash=unique_hash)
    print(f"    DB status after : {db_ticket.status}")
    print(f"    DB scanned_at   : {db_ticket.scanned_at}")
    assert db_ticket.status == "used", "FAIL: DB status should be 'used'"
    assert db_ticket.scanned_at is not None, "FAIL: scanned_at should be set"
    print("    PASS [OK]")

    # -- CHECK C --
    print("\n[C] Same ticket scanned again -> expect ALREADY_USED")
    res_c = client.post('/api/tickets/validate/', {"qr_code_hash": unique_hash}, format="json")
    print(f"    HTTP status     : {res_c.status_code}")
    print(f"    Response        : {dict(res_c.data)}")
    assert res_c.data['status'] == "ALREADY_USED", "FAIL: Expected ALREADY_USED"
    print("    PASS [OK]")

    # -- CHECK D --
    print("\n[D] Completely fake QR hash -> expect INVALID")
    res_d = client.post('/api/tickets/validate/', {"qr_code_hash": "THIS_HASH_DOES_NOT_EXIST_XYZ"}, format="json")
    print(f"    HTTP status     : {res_d.status_code}")
    print(f"    Response        : {dict(res_d.data)}")
    assert res_d.data['status'] == "INVALID", "FAIL: Expected INVALID"
    print("    PASS [OK]")

    # -- CHECK E --
    print("\n[E] Student tries to call validate -> expect 403 Forbidden")
    client.force_authenticate(user=student)
    res_e = client.post('/api/tickets/validate/', {"qr_code_hash": unique_hash}, format="json")
    print(f"    HTTP status     : {res_e.status_code}")
    assert res_e.status_code == 403, "FAIL: Expected 403"
    print("    PASS [OK]")

    # -- CHECK F --
    print("\n[F] Organiser calls GET /api/dashboard/ -> confirm fields present")
    client.force_authenticate(user=organiser)
    res_f = client.get('/api/dashboard/')
    print(f"    HTTP status     : {res_f.status_code}")
    assert res_f.status_code == 200, "FAIL: Expected 200"
    assert 'my_events' in res_f.data, "FAIL: 'my_events' missing"
    assert 'overview' not in res_f.data, "FAIL: 'overview' should not appear for organiser"
    test_event_data = next((e for e in res_f.data['my_events'] if e['id'] == event.id), None)
    assert test_event_data is not None, "FAIL: Test event not found in my_events"
    print(f"    Contains 'my_events'            : True")
    print(f"    Organiser sees 'overview'       : {'overview' in res_f.data} (expected: False)")
    print(f"    Test event stats:")
    print(f"      tickets_issued   : {test_event_data['tickets_issued']}")
    print(f"      tickets_used     : {test_event_data['tickets_used']}")
    print(f"      spots_remaining  : {test_event_data['spots_remaining']}")
    print(f"      attendance_rate  : {test_event_data['attendance_rate']}%")
    print("    PASS [OK]")

    # -- CHECK G --
    print(f"\n[G] GET /api/dashboard/events/{event.id}/attendance/ -> scanned student in list")
    res_g = client.get(f'/api/dashboard/events/{event.id}/attendance/')
    print(f"    HTTP status     : {res_g.status_code}")
    assert res_g.status_code == 200, "FAIL: Expected 200"
    attendees = res_g.data.get('attendees', [])
    scanned = next((a for a in attendees if a['email'] == student.email), None)
    assert scanned is not None, "FAIL: Student not found in attendees list"
    print(f"    Attendees count  : {len(attendees)}")
    print(f"    Student found    : {scanned['email']}")
    print(f"    Ticket status    : {scanned['status']}")
    print(f"    scanned_at set   : {scanned['scanned_at'] is not None}")
    print(f"    scanned_at value : {scanned['scanned_at']}")
    assert scanned['status'] == 'used', "FAIL: Ticket status should be 'used'"
    assert scanned['scanned_at'] is not None, "FAIL: scanned_at should be populated"
    print("    PASS [OK]")

    # -- Cleanup --
    ticket.delete()
    event.delete()
    print("\n" + "=" * 60)
    print("ALL 7 CHECKS PASSED SUCCESSFULLY [OK]")
    print("=" * 60)

if __name__ == '__main__':
    run_all_checks()
