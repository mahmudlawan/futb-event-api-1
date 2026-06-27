from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer, EventSerializer, EventCreateUpdateSerializer
from .permissions import IsOrganiser, IsAdminRole
from .models import Event
from django.utils import timezone
from django.db.models import Q
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
        events = Event.objects.filter(status='published')
        
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
        events = Event.objects.filter(status='published', date_time__gt=now)

        def score_event(event):
            score = 0
            if event.category in user_categories:
                score += 2
            if event.organiser.faculty == user_faculty or event.organiser.department == user_dept:
                score += 1
            return score

        # Sort based on score (descending)
        ranked_events = sorted(events, key=score_event, reverse=True)
        
        serializer = EventSerializer(ranked_events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
