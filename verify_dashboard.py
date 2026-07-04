import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'futb_events.settings')
django.setup()

from rest_framework.test import APIClient
from core.models import User, Event, Ticket, Payment, Notification

def test_admin_dashboard():
    client = APIClient()

    # Create users
    student = User.objects.filter(email="student_dash@futb.edu.ng").first()
    if not student:
        student = User.objects.create_user(
            username="student_dash@futb.edu.ng",
            email="student_dash@futb.edu.ng",
            role="student",
            password="testpassword123"
        )
        
    organiser = User.objects.filter(email="organiser_dash@futb.edu.ng").first()
    if not organiser:
        organiser = User.objects.create_user(
            username="organiser_dash@futb.edu.ng",
            email="organiser_dash@futb.edu.ng",
            role="organiser",
            password="testpassword123"
        )

    admin = User.objects.filter(email="admin_dash@futb.edu.ng").first()
    if not admin:
        admin = User.objects.create_user(
            username="admin_dash@futb.edu.ng",
            email="admin_dash@futb.edu.ng",
            role="admin",
            password="testpassword123"
        )

    # Create Event & Tickets & Payment
    event = Event.objects.create(
        organiser=organiser,
        title="Sprint 5 Dashboard Event",
        description="Dashboard testing.",
        category="Sports",
        date_time=timezone.now(),
        venue="FUTB Arena",
        capacity=100,
        status="published"
    )
    
    ticket = Ticket.objects.create(
        user=student,
        event=event,
        qr_code_hash="dash_hash_123",
        ticket_type="free",
        status="active"
    )
    
    # Create notification to ensure notifications exist
    Notification.objects.create(
        user=student,
        event=event,
        type="email",
        message="Test reminder",
        status="sent"
    )

    print("--- Running Dashboard API Tests ---")

    # A. Test Student access (403)
    client.force_authenticate(user=student)
    res_student = client.get('/api/dashboard/')
    print(f"Student dashboard access status (Expected 403): {res_student.status_code}")

    # B. Test Organiser access (Should see my_events, but not overview or notifications)
    client.force_authenticate(user=organiser)
    res_org = client.get('/api/dashboard/')
    print(f"Organiser dashboard status (Expected 200): {res_org.status_code}")
    print(f"Contains 'my_events': {'my_events' in res_org.data}")
    print(f"Contains 'overview': {'overview' in res_org.data}")
    print(f"Contains 'recent_notifications': {'recent_notifications' in res_org.data}")

    # C. Test Admin access (Should see my_events, overview, and recent_notifications)
    client.force_authenticate(user=admin)
    res_admin = client.get('/api/dashboard/')
    print(f"Admin dashboard status (Expected 200): {res_admin.status_code}")
    print(f"Contains 'overview': {'overview' in res_admin.data}")
    print(f"Contains 'recent_notifications': {'recent_notifications' in res_admin.data}")
    print(f"Overview stats: {res_admin.data.get('overview')}")

    # D. Test Event Attendance (Organiser viewing own event)
    client.force_authenticate(user=organiser)
    res_att = client.get(f'/api/dashboard/events/{event.id}/attendance/')
    print(f"Event attendance status (Expected 200): {res_att.status_code}")
    print(f"Attendance details: {res_att.data}")

    # E. Test Event Attendance (Organiser viewing another organiser's event - 403)
    other_organiser = User.objects.filter(email="other_organiser@futb.edu.ng").first()
    if not other_organiser:
        other_organiser = User.objects.create_user(
            username="other_organiser@futb.edu.ng",
            email="other_organiser@futb.edu.ng",
            role="organiser",
            password="testpassword123"
        )
    client.force_authenticate(user=other_organiser)
    res_att_forbidden = client.get(f'/api/dashboard/events/{event.id}/attendance/')
    print(f"Other organiser attendance status (Expected 403): {res_att_forbidden.status_code}")

    # Clean up test data
    ticket.delete()
    event.delete()
    other_organiser.delete()
    print("-----------------------------------")

if __name__ == '__main__':
    test_admin_dashboard()
