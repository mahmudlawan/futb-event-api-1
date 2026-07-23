from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer, EventSerializer, EventCreateUpdateSerializer, TicketSerializer, FCMTokenSerializer, NotificationSerializer
from .permissions import IsOrganiser, IsAdminRole
from .models import User, Event, Ticket, Payment, Notification
from django.utils import timezone
from django.db.models import Q, Sum
from django.conf import settings
from django.db import transaction
from django.core.signing import Signer
import secrets
import requests
# POST /api/auth/register/
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_data = UserSerializer(user).data
            return Response(user_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# POST /api/auth/login/  – returns access + refresh + role + full_name
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# GET /api/auth/profile/
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# POST /api/auth/logout/  – blacklists the refresh token
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"detail": "Invalid or missing refresh token."}, status=status.HTTP_400_BAD_REQUEST)

# ─────────────────────────────────────────────
# Event Views
# ─────────────────────────────────────────────
class EventListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        events = Event.objects.filter(status='published', date_time__gt=now).order_by('date_time')
        
        category = request.query_params.get('category')
        faculty = request.query_params.get('faculty')
        search = request.query_params.get('search')
        
        if category:
            events = events.filter(category=category)
        if faculty:
            events = events.filter(organiser__faculty=faculty)
        if search:
            events = events.filter(Q(title__icontains=search) | Q(description__icontains=search))
            
        serializer = EventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def post(self, request):
        if request.user.role not in ['organiser', 'admin']:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = EventCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            event = serializer.save(organiser=request.user, status='published')
            return Response(EventSerializer(event).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return None

    def get(self, request, pk):
        event = self.get_object(pk)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = EventSerializer(event)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        event = self.get_object(pk)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if event.organiser != request.user and request.user.role != 'admin':
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
            
        serializer = EventCreateUpdateSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(EventSerializer(event).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        event = self.get_object(pk)
        if not event:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if event.organiser != request.user and request.user.role != 'admin':
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
            
        event.status = 'cancelled'
        event.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecommendedEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_categories = [interest.category for interest in user.interests.all()]
        user_faculty = user.faculty
        user_dept = user.department

        now = timezone.now()
        events = Event.objects.filter(status='published', date_time__gt=now).order_by('date_time')

        def score_event(event):
            score = 0
            # +2 if event category matches one of the student's interests
            if event.category in user_categories:
                score += 2
            # +1 if target_faculty is null/blank (open to all) OR matches student's faculty
            if not event.target_faculty or event.target_faculty == user_faculty:
                score += 1
            # +1 if target_department is null/blank (open to all) OR matches student's department
            if not event.target_department or event.target_department == user_dept:
                score += 1
            return score

        # Sort based on score (descending), max possible = 4
        ranked_events = sorted(events, key=score_event, reverse=True)
        
        serializer = EventSerializer(ranked_events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# PART A — FREE REGISTRATION & TICKETS
# ─────────────────────────────────────────────

class FreeEventRegisterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'student':
            return Response({"detail": "Only students can register for events."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

        if event.event_type != "free":
            return Response({"detail": "This is a paid event, use the payment endpoint instead."}, status=status.HTTP_400_BAD_REQUEST)

        # Duplicate Check
        if event.tickets.filter(user=request.user, status='active').exists():
            return Response({"detail": "You have already registered for this event."}, status=status.HTTP_400_BAD_REQUEST)

        # Capacity Check
        active_count = event.tickets.filter(status='active').count()
        if active_count >= event.capacity:
            return Response({"detail": "Event is fully booked."}, status=status.HTTP_400_BAD_REQUEST)

        # Atomic creation + cryptographic signing of ticket QR
        with transaction.atomic():
            ticket = Ticket.objects.create(
                user=request.user,
                event=event,
                qr_code_hash=secrets.token_hex(16),  # temporary unique placeholder
                ticket_type="free",
                status="active"
            )
            # Combine the ticket id + a cryptographically secure token and sign it
            signer = Signer()
            ticket.qr_code_hash = signer.sign(f"{ticket.id}:{secrets.token_hex(8)}")
            ticket.save()

        serializer = TicketSerializer(ticket)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyTicketsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tickets = Ticket.objects.filter(user=request.user)
        serializer = TicketSerializer(tickets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# PART B — PAYSTACK INTEGRATION (SANDBOX)
# ─────────────────────────────────────────────

class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'student':
            return Response({"detail": "Only students can register for events."}, status=status.HTTP_403_FORBIDDEN)

        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

        if event.event_type != "paid":
            return Response({"detail": "This is a free event, use the register endpoint instead."}, status=status.HTTP_400_BAD_REQUEST)

        # Duplicate Check
        if event.tickets.filter(user=request.user, status='active').exists():
            return Response({"detail": "You have already registered for this event."}, status=status.HTTP_400_BAD_REQUEST)

        # Capacity Check
        active_count = event.tickets.filter(status='active').count()
        if active_count >= event.capacity:
            return Response({"detail": "Event is fully booked."}, status=status.HTTP_400_BAD_REQUEST)

        # Call Paystack Transaction Initialize
        url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        # Ticket price in kobo (Paystack expected lowest currency unit)
        amount_in_kobo = int(event.ticket_price * 100)
        data = {
            "email": request.user.email,
            "amount": amount_in_kobo,
        }

        try:
            res = requests.post(url, json=data, headers=headers, timeout=10)
            res_data = res.json()
            if not res_data.get("status"):
                return Response({"detail": f"Paystack initiation failed: {res_data.get('message')}"}, status=status.HTTP_400_BAD_REQUEST)

            paystack_ref = res_data["data"]["reference"]
            authorization_url = res_data["data"]["authorization_url"]

            # Save pending payment
            Payment.objects.create(
                user=request.user,
                event=event,
                amount=event.ticket_price,
                paystack_ref=paystack_ref,
                status="pending"
            )

            return Response({
                "authorization_url": authorization_url,
                "reference": paystack_ref
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": f"Payment server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, reference):
        try:
            payment = Payment.objects.get(paystack_ref=reference)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)

        # Idempotency check: If reference is already verified, return existing ticket
        if payment.status == "success" and payment.ticket:
            return Response(TicketSerializer(payment.ticket).data, status=status.HTTP_200_OK)

        # Call Paystack Transaction Verify
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        }

        try:
            res = requests.get(url, headers=headers, timeout=10)
            res_data = res.json()
            if not res_data.get("status"):
                return Response({"detail": f"Paystack verification failed: {res_data.get('message')}"}, status=status.HTTP_400_BAD_REQUEST)

            paystack_status = res_data["data"]["status"]

            if paystack_status == "success":
                with transaction.atomic():
                    # Generate cryptographically signed paid ticket
                    ticket = Ticket.objects.create(
                        user=payment.user,
                        event=payment.event,
                        qr_code_hash=secrets.token_hex(16),
                        ticket_type="paid",
                        status="active"
                    )
                    signer = Signer()
                    ticket.qr_code_hash = signer.sign(f"{ticket.id}:{secrets.token_hex(8)}")
                    ticket.save()

                    # Save verified status
                    payment.status = "success"
                    payment.ticket = ticket
                    payment.paid_at = timezone.now()
                    payment.save()

                return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)
            else:
                # Update status (e.g. failed / abandoned)
                payment.status = paystack_status
                payment.save()
                return Response({"detail": f"Payment not successful. Status: {paystack_status}"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"detail": f"Payment verification server error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FCMTokenUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        if serializer.is_valid():
            request.user.fcm_token = serializer.validated_data['fcm_token']
            request.user.save()
            return Response({"detail": "FCM token updated successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TestReminderView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def post(self, request):
        from core.tasks import send_event_reminders
        try:
            send_event_reminders()
            return Response({"detail": "Successfully triggered send_event_reminders task."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"Error running reminders: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ValidateTicketView(APIView):
    permission_classes = [IsAuthenticated, IsOrganiser | IsAdminRole]

    def post(self, request):
        qr_code_hash = request.data.get("qr_code_hash")
        if not qr_code_hash:
            return Response({"detail": "qr_code_hash is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                ticket = Ticket.objects.select_for_update().get(qr_code_hash=qr_code_hash)
                
                if ticket.status == "used":
                    return Response({
                        "status": "ALREADY_USED",
                        "message": "This ticket has already been scanned. Entry denied.",
                        "scanned_at": ticket.scanned_at
                    }, status=status.HTTP_200_OK)
                    
                elif ticket.status == "cancelled":
                    return Response({
                        "status": "CANCELLED",
                        "message": "This ticket has been cancelled. Entry denied."
                    }, status=status.HTTP_200_OK)
                    
                elif ticket.status == "active":
                    ticket.status = "used"
                    ticket.scanned_at = timezone.now()
                    ticket.save()
                    
                    attendee_name = ticket.user.get_full_name() or ticket.user.username
                    
                    return Response({
                        "status": "VALID",
                        "message": "Ticket valid. Entry granted.",
                        "attendee_name": attendee_name,
                        "event_title": ticket.event.title,
                        "ticket_type": ticket.ticket_type
                      }, status=status.HTTP_200_OK)
                      
        except Ticket.DoesNotExist:
            return Response({
                "status": "INVALID",
                "message": "Ticket not recognised. Entry denied."
            }, status=status.HTTP_200_OK)

class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsOrganiser | IsAdminRole]

    def get(self, request):
        response_data = {}
        
        # 1. Overview (For Super Admin only)
        if request.user.role == 'admin':
            total_events = Event.objects.filter(status='published').count()
            total_students = User.objects.filter(role='student').count()
            total_tickets_issued = Ticket.objects.filter(status__in=['active', 'used']).count()
            
            rev_agg = Payment.objects.filter(status='success').aggregate(total=Sum('amount'))
            total_revenue = float(rev_agg['total'] or 0.00)
            
            response_data['overview'] = {
                "total_events": total_events,
                "total_students": total_students,
                "total_tickets_issued": total_tickets_issued,
                "total_revenue": total_revenue
            }
            
            # recent notifications (last 10 across the platform)
            notifications = Notification.objects.select_related('user', 'event').order_by('-id')[:10]
            recent_notifications = []
            for n in notifications:
                recent_notifications.append({
                    "user_email": n.user.email,
                    "event_title": n.event.title if n.event else None,
                    "type": n.type,
                    "status": n.status,
                    "sent_at": n.sent_at.isoformat() if n.sent_at else None
                })
            response_data['recent_notifications'] = recent_notifications
            
        # 2. My Events (For Organiser / Admin can also view their owned ones)
        my_events_list = []
        my_events_qs = Event.objects.filter(organiser=request.user)
        for event in my_events_qs:
            tickets_issued = event.tickets.filter(status__in=['active', 'used']).count()
            tickets_used = event.tickets.filter(status='used').count()
            spots_remaining = event.capacity - tickets_issued
            
            rev_agg = event.payments.filter(status='success').aggregate(total=Sum('amount'))
            revenue = float(rev_agg['total'] or 0.00)
            
            attendance_rate = round((tickets_used / event.capacity) * 100, 1) if event.capacity > 0 else 0.0
            
            my_events_list.append({
                "id": event.id,
                "title": event.title,
                "date_time": event.date_time.isoformat(),
                "venue": event.venue,
                "capacity": event.capacity,
                "tickets_issued": tickets_issued,
                "tickets_used": tickets_used,
                "spots_remaining": spots_remaining,
                "revenue": revenue,
                "attendance_rate": attendance_rate
            })
            
        response_data['my_events'] = my_events_list
        return Response(response_data, status=status.HTTP_200_OK)

class EventAttendanceView(APIView):
    permission_classes = [IsAuthenticated, IsOrganiser | IsAdminRole]

    def get(self, request, id):
        try:
            event = Event.objects.get(pk=id)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found."}, status=status.HTTP_404_NOT_FOUND)

        # Restrict organisers to only their own events
        if request.user.role == 'organiser' and event.organiser != request.user:
            return Response({"detail": "You do not have permission to view this event's attendance."}, status=status.HTTP_403_FORBIDDEN)

        tickets_issued = event.tickets.filter(status__in=['active', 'used']).count()
        tickets_used = event.tickets.filter(status='used').count()
        spots_remaining = event.capacity - tickets_issued
        attendance_rate = round((tickets_used / event.capacity) * 100, 1) if event.capacity > 0 else 0.0

        attendees = []
        tickets_qs = event.tickets.select_related('user').all()
        for t in tickets_qs:
            attendees.append({
                "full_name": t.user.get_full_name() or t.user.username,
                "email": t.user.email,
                "ticket_type": t.ticket_type,
                "status": t.status,
                "issued_at": t.issued_at.isoformat() if t.issued_at else None,
                "scanned_at": t.scanned_at.isoformat() if t.scanned_at else None
            })

        response_data = {
            "event_title": event.title,
            "date_time": event.date_time.isoformat(),
            "venue": event.venue,
            "capacity": event.capacity,
            "tickets_issued": tickets_issued,
            "tickets_used": tickets_used,
            "spots_remaining": spots_remaining,
            "attendance_rate": attendance_rate,
            "attendees": attendees
        }
        return Response(response_data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/notifications/
# Returns the authenticated user's notifications, newest first.
# ─────────────────────────────────────────────────────────────────────────────
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = (
            Notification.objects
            .filter(user=request.user)
            .select_related('event')
            .order_by('-id')
        )
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
