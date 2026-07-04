import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from rest_framework.test import APIClient
from django.utils import timezone
from core.models import User, Event, Ticket

def test_qr_validation():
    client = APIClient()
    
    # 1. Create users
    student = User.objects.filter(email="student_v5@futb.edu.ng").first()
    if not student:
        student = User.objects.create_user(
            username="student_v5@futb.edu.ng",
            email="student_v5@futb.edu.ng",
            role="student",
            password="testpassword123"
        )
        
    organiser = User.objects.filter(email="organiser_v5@futb.edu.ng").first()
    if not organiser:
        organiser = User.objects.create_user(
            username="organiser_v5@futb.edu.ng",
            email="organiser_v5@futb.edu.ng",
            role="organiser",
            password="testpassword123"
        )

    # 2. Create Event & Tickets
    event = Event.objects.create(
        organiser=organiser,
        title="Sprint 5 Gate Event",
        description="Gate validation testing.",
        category="Sports",
        date_time=timezone.now(),
        venue="FUTB Gate",
        capacity=100
    )
    
    ticket_active = Ticket.objects.create(
        user=student,
        event=event,
        qr_code_hash="active_hash_123",
        ticket_type="free",
        status="active"
    )
    
    ticket_cancelled = Ticket.objects.create(
        user=student,
        event=event,
        qr_code_hash="cancelled_hash_123",
        ticket_type="free",
        status="cancelled"
    )

    print("--- Running QR Gate Validation Tests ---")

    # A. Test Student access (Should be Forbidden 403)
    client.force_authenticate(user=student)
    res_forbidden = client.post('/api/tickets/validate/', {"qr_code_hash": "active_hash_123"}, format="json")
    print(f"Student access response status (Expected 403): {res_forbidden.status_code}")

    # B. Test Organiser access
    client.force_authenticate(user=organiser)

    # Test Invalid QR hash
    res_invalid = client.post('/api/tickets/validate/', {"qr_code_hash": "non_existent_hash"}, format="json")
    print(f"Invalid ticket status (Expected 200): {res_invalid.status_code}")
    print(f"Invalid ticket response: {res_invalid.data}")

    # Test Cancelled ticket
    res_cancelled = client.post('/api/tickets/validate/', {"qr_code_hash": "cancelled_hash_123"}, format="json")
    print(f"Cancelled ticket response: {res_cancelled.data}")

    # Test Active ticket -> VALID
    res_valid = client.post('/api/tickets/validate/', {"qr_code_hash": "active_hash_123"}, format="json")
    print(f"Active ticket response: {res_valid.data}")

    # Test scanning the same ticket again -> ALREADY_USED
    res_used = client.post('/api/tickets/validate/', {"qr_code_hash": "active_hash_123"}, format="json")
    print(f"Used ticket response: {res_used.data}")

    # Clean up test records
    ticket_active.delete()
    ticket_cancelled.delete()
    event.delete()
    print("----------------------------------------")

if __name__ == '__main__':
    test_qr_validation()
