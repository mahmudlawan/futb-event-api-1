from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer, EventSerializer, EventCreateUpdateSerializer, TicketSerializer, FCMTokenSerializer, NotificationSerializer, ProfileUpdateSerializer, ChangePasswordSerializer
from .permissions import IsOrganiser, IsAdminRole
from .models import User, Event, Ticket, Payment, Notification
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q, Sum, Count
from django.conf import settings
from django.db import transaction
from django.core.signing import Signer
import os
import secrets
import requests
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view, permission_classes

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    db_status = 'ok'
    db_error = None
    user_count = 0
    migration_output = None

    if request.query_params.get('run_migrate') == 'true':
        try:
            from django.core.management import call_command
            import io
            out = io.StringIO()
            call_command('migrate', interactive=False, stdout=out)
            migration_output = out.getvalue()
        except Exception as e:
            migration_output = f"Migration failed: {e}"

    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
        user_count = User.objects.count()
    except Exception as e:
        db_status = 'error'
        db_error = str(e)

    return Response({
        'status': 'healthy' if db_status == 'ok' else 'degraded',
        'service': 'FUTB Smart Campus API',
        'version': '1.0.0',
        'database': db_status,
        'user_count': user_count,
        'db_error': db_error,
        'migration_output': migration_output,
    })

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
        serializer = UserSerializer(request.user, context={'request': request})
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
# POST /api/auth/profile/update/ – update user profile (PATCH)
class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            user = serializer.update_user(request.user, serializer.validated_data)
            return Response(UserSerializer(user, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# PATCH /api/auth/profile/picture/ – upload profile picture
class ProfilePictureUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        user = request.user

        if 'profile_picture' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=400
            )

        image_file = request.FILES['profile_picture']

        # Validate file type
        allowed_types = [
            'image/jpeg',
            'image/png',
            'image/jpg',
            'image/webp',
            'image/pjpeg',
            'image/x-png',
        ]
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        content_type = getattr(image_file, 'content_type', '').lower()
        ext = os.path.splitext(image_file.name)[1].lower() if image_file.name else ''

        if (content_type not in allowed_types) and (ext not in allowed_extensions):
            return Response(
                {'error': 'Only JPEG, PNG and WebP images are allowed'},
                status=400
            )

        # Validate file size (max 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'Image must be smaller than 5MB'},
                status=400
            )

        # Delete old picture if exists
        if user.profile_picture:
            try:
                if os.path.isfile(user.profile_picture.path):
                    os.remove(user.profile_picture.path)
            except Exception:
                pass

        # Save new picture
        user.profile_picture = image_file
        user.save()

        serializer = UserSerializer(
            user,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        return self.patch(request)



# POST /api/auth/change-password/ – change password (POST)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

import random
import string
from django.core.mail import send_mail

# POST /api/auth/forgot-password/
class RequestPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            otp = ''.join(random.choices(string.digits, k=6))
            expires = timezone.now() + timedelta(minutes=10)
            
            user.password_reset_otp = otp
            user.password_reset_otp_expires = expires
            user.save()
            
            send_mail(
                subject='FUTB Smart Campus — Password Reset Code',
                message=f'''Hello {user.first_name or user.email},

Your password reset code is:

{otp}

This code expires in 10 minutes.

If you did not request a password reset, please ignore this email.

FUTB Smart Campus Team''',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except User.DoesNotExist:
            pass # DO nothing, but still return success for security
        except Exception as e:
            return Response({"error": "Failed to send reset email. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "If this email is registered, a reset code has been sent."}, status=status.HTTP_200_OK)

# POST /api/auth/verify-otp/
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

        if user.password_reset_otp != otp:
            return Response({"error": "Invalid verification code"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.password_reset_otp_expires or timezone.now() > user.password_reset_otp_expires:
            return Response({"error": "Verification code has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        reset_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        user.password_reset_otp = reset_token
        user.password_reset_otp_expires = timezone.now() + timedelta(minutes=5)
        user.save()

        return Response({
            "message": "Code verified successfully",
            "reset_token": reset_token,
            "email": email
        }, status=status.HTTP_200_OK)

# POST /api/auth/reset-password/
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        reset_token = request.data.get("reset_token")
        new_password = request.data.get("new_password")

        if not email or not reset_token or not new_password:
            return Response({"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

        if user.password_reset_otp != reset_token:
            return Response({"error": "Invalid or expired reset token"}, status=status.HTTP_400_BAD_REQUEST)

        if not user.password_reset_otp_expires or timezone.now() > user.password_reset_otp_expires:
            return Response({"error": "Reset token has expired. Please start again."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.password_reset_otp = None
        user.password_reset_otp_expires = None
        user.save()

        return Response({"message": "Password reset successful. You can now log in with your new password."}, status=status.HTTP_200_OK)


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
            now = timezone.now()
            thirty_days_ago = now - timedelta(days=30)
            seven_days_ago = now - timedelta(days=7)

            # ── Core stats ──
            total_events = Event.objects.filter(status='published').count()
            total_students = User.objects.filter(role='student').count()
            total_organisers = User.objects.filter(role='organiser').count()
            total_tickets = Ticket.objects.filter(status__in=['active', 'used']).count()
            total_tickets_used = Ticket.objects.filter(status='used').count()

            rev_agg = Payment.objects.filter(status='success').aggregate(total=Sum('amount'))
            total_revenue = float(rev_agg['total'] or 0.00)

            # ── Attendance rate ──
            capacity_agg = Event.objects.filter(status='published').aggregate(total=Sum('capacity'))
            total_capacity = capacity_agg['total'] or 1
            overall_attendance_rate = round((total_tickets_used / total_capacity) * 100, 1)

            # ── Recent activity (last 30 days) ──
            new_students_30d = User.objects.filter(
                role='student',
                date_joined__gte=thirty_days_ago
            ).count()

            new_tickets_30d = Ticket.objects.filter(
                status__in=['active', 'used'],
                issued_at__gte=thirty_days_ago
            ).count()

            new_events_30d = Event.objects.filter(
                status='published',
                created_at__gte=thirty_days_ago
            ).count()

            revenue_30d = float(
                Payment.objects.filter(
                    status='success',
                    paid_at__gte=thirty_days_ago
                ).aggregate(total=Sum('amount'))['total'] or 0.00
            )

            # ── Category breakdown ──
            category_stats = []
            categories = ['academic', 'cultural', 'sports', 'social', 'technology']
            for cat in categories:
                event_count = Event.objects.filter(category=cat, status='published').count()
                ticket_count = Ticket.objects.filter(
                    event__category=cat,
                    status__in=['active', 'used']
                ).count()
                category_stats.append({
                    'category': cat,
                    'events': event_count,
                    'tickets': ticket_count,
                })

            # ── Top 5 events by attendance ──
            top_events = Event.objects.filter(status='published').annotate(
                ticket_count=Count(
                    'tickets',
                    filter=Q(tickets__status__in=['active', 'used'])
                )
            ).order_by('-ticket_count')[:5]

            top_events_data = [
                {
                    'id': e.id,
                    'title': e.title,
                    'category': e.category,
                    'tickets_issued': e.ticket_count,
                    'capacity': e.capacity,
                    'attendance_rate': round(
                        (e.ticket_count / e.capacity) * 100 if e.capacity > 0 else 0.0,
                        1
                    ),
                    'event_type': e.event_type,
                }
                for e in top_events
            ]

            # ── Weekly ticket registrations (last 7 days) ──
            weekly_data = []
            for i in range(6, -1, -1):
                day = now - timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
                count = Ticket.objects.filter(
                    issued_at__gte=day_start,
                    issued_at__lte=day_end,
                    status__in=['active', 'used']
                ).count()
                weekly_data.append({
                    'day': day.strftime('%a'),
                    'tickets': count,
                })

            response_data['overview'] = {
                # Core stats
                'total_events': total_events,
                'total_students': total_students,
                'total_organisers': total_organisers,
                'total_tickets_issued': total_tickets,
                'total_tickets_used': total_tickets_used,
                'total_revenue': total_revenue,
                'overall_attendance_rate': overall_attendance_rate,

                # Last 30 days
                'new_students_30d': new_students_30d,
                'new_tickets_30d': new_tickets_30d,
                'new_events_30d': new_events_30d,
                'revenue_30d': revenue_30d,

                # Analytics
                'category_breakdown': category_stats,
                'top_events': top_events_data,
                'weekly_registrations': weekly_data,
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
                "attendance_rate": attendance_rate,
                "event_type": event.event_type,
                "status": event.status,
            })

        response_data['my_events'] = my_events_list

        # Summary stats for organiser
        organiser_total_tickets = Ticket.objects.filter(
            event__organiser=request.user,
            status__in=['active', 'used']
        ).count()

        organiser_revenue = float(
            Payment.objects.filter(
                ticket__event__organiser=request.user,
                status='success'
            ).aggregate(total=Sum('amount'))['total'] or 0.00
        )

        organiser_total_events = Event.objects.filter(
            organiser=request.user,
            status='published'
        ).count()

        response_data['organiser_summary'] = {
            'total_events': organiser_total_events,
            'total_tickets': organiser_total_tickets,
            'total_revenue': organiser_revenue,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class AllUsersView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        role_filter = request.query_params.get('role', None)
        search = request.query_params.get('search', '')

        users = User.objects.all().order_by('-date_joined')

        if role_filter:
            users = users.filter(role=role_filter)

        if search:
            users = users.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(department__icontains=search)
            )

        user_data = []
        for u in users:
            ticket_count = Ticket.objects.filter(
                user=u,
                status__in=['active', 'used']
            ).count()
            user_data.append({
                'id': u.id,
                'full_name': u.get_full_name() or u.email.split('@')[0],
                'email': u.email,
                'role': u.role,
                'department': u.department or '',
                'faculty': u.faculty or '',
                'date_joined': u.date_joined.isoformat(),
                'tickets_count': ticket_count,
                'is_active': u.is_active,
            })

        return Response({
            'total': len(user_data),
            'users': user_data,
        }, status=status.HTTP_200_OK)


class UserRegisteredEventsView(APIView):
    """Return all events a specific user has registered for (admin only)."""
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, user_id):
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        tickets = Ticket.objects.filter(
            user=target_user,
            status__in=['active', 'used', 'cancelled']
        ).select_related('event').order_by('-issued_at')

        events_data = []
        for ticket in tickets:
            event = ticket.event
            events_data.append({
                'ticket_id': ticket.id,
                'ticket_status': ticket.status,
                'ticket_type': ticket.ticket_type,
                'issued_at': ticket.issued_at.isoformat(),
                'event': {
                    'id': event.id,
                    'title': event.title,
                    'date_time': event.date_time.isoformat(),
                    'venue': event.venue,
                    'category': event.category,
                    'event_type': event.event_type,
                    'status': event.status,
                    'capacity': event.capacity,
                },
            })

        return Response({
            'user': {
                'id': target_user.id,
                'full_name': target_user.get_full_name() or target_user.email.split('@')[0],
                'email': target_user.email,
                'role': target_user.role,
            },
            'total': len(events_data),
            'registered_events': events_data,
        }, status=status.HTTP_200_OK)


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
            "event": {
                "title": event.title,
                "date_time": event.date_time.isoformat(),
                "venue": event.venue,
                "capacity": event.capacity
            },
            "event_title": event.title,
            "date_time": event.date_time.isoformat(),
            "venue": event.venue,
            "capacity": event.capacity,
            "tickets_issued": tickets_issued,
            "tickets_used": tickets_used,
            "spots_remaining": spots_remaining,
            "attendance_rate": attendance_rate,
            "attendees": attendees,
            "reminder_summary": {
                "twenty_four_h": Notification.objects.filter(event=event, status='sent', sent_at__range=(event.date_time - timedelta(hours=24), event.date_time)).count(),
                "twelve_h": Notification.objects.filter(event=event, status='sent', sent_at__range=(event.date_time - timedelta(hours=12), event.date_time)).count(),
                "two_h": Notification.objects.filter(event=event, status='sent', sent_at__range=(event.date_time - timedelta(hours=2), event.date_time)).count()
            }
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


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/admin/events/<event_id>/announce/
# Sends a custom email to every student with an active ticket for the event.
# Admins can announce for any event; organisers only for their own.
# ─────────────────────────────────────────────────────────────────────────────
class AnnouncementView(APIView):
    permission_classes = [IsAuthenticated, IsOrganiser | IsAdminRole]

    def post(self, request, event_id):
        # ── Get the event ──
        try:
            event = Event.objects.get(id=event_id, status='published')
        except Event.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Permission check: organisers may only announce for their own events ──
        if request.user.role == 'organiser' and event.organiser != request.user:
            return Response(
                {'error': 'You can only send announcements for your own events'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Validate payload ──
        subject = str(request.data.get('subject', '')).strip()
        message = str(request.data.get('message', '')).strip()

        if not subject:
            return Response(
                {'error': 'Announcement subject is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not message:
            return Response(
                {'error': 'Announcement message is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(subject) > 150:
            return Response(
                {'error': 'Subject must be 150 characters or less'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(message) > 2000:
            return Response(
                {'error': 'Message must be 2000 characters or less'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Collect unique student emails ──
        active_tickets = (
            Ticket.objects
            .filter(event=event, status__in=['active', 'used'])
            .select_related('user')
        )

        if not active_tickets.exists():
            return Response(
                {'error': 'No registered students found for this event'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        student_emails = list({
            t.user.email for t in active_tickets if t.user.email
        })
        student_count = len(student_emails)

        # ── Build the email body ──
        full_message = (
            f"Dear Student,\n\n"
            f"You are receiving this announcement regarding the event "
            f"you registered for:\n\n"
            f"EVENT: {event.title}\n"
            f"DATE:  {event.date_time.strftime('%A, %d %B %Y at %I:%M %p')}\n"
            f"VENUE: {event.venue}\n\n"
            f"{'─' * 50}\n\n"
            f"{message}\n\n"
            f"{'─' * 50}\n\n"
            f"This message was sent by the event organiser through "
            f"FUTB Smart Campus.\n\n"
            f"FUTB Smart Campus Team\n"
            f"Federal University of Technology, Babura\n"
            f"support@futb.edu.ng"
        )

        # ── Send emails ──
        sent_count = 0
        failed_count = 0

        for email in student_emails:
            try:
                send_mail(
                    subject=f'[{event.title}] {subject}',
                    message=full_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                sent_count += 1
            except Exception:
                failed_count += 1

        # ── Log the action ──
        from .models import AdminLog
        AdminLog.objects.create(
            admin=request.user,
            action_type='announcement',
            target_id=event.id,
            description=(
                f'Sent announcement to {sent_count} student'
                f'{"s" if sent_count != 1 else ""} for event: {event.title}. '
                f'Subject: {subject}'
            ),
        )

        # ── Return response ──
        if failed_count == 0:
            return Response({
                'success': True,
                'message': (
                    f'Announcement sent successfully to {sent_count} '
                    f'student{"s" if sent_count != 1 else ""}'
                ),
                'sent_count': sent_count,
                'failed_count': 0,
            }, status=status.HTTP_200_OK)

        if sent_count > 0:
            return Response({
                'success': True,
                'message': (
                    f'Announcement sent to {sent_count} '
                    f'student{"s" if sent_count != 1 else ""}. '
                    f'{failed_count} delivery{"s" if failed_count != 1 else ""} failed.'
                ),
                'sent_count': sent_count,
                'failed_count': failed_count,
            }, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Failed to send announcement. Please check email configuration and try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
