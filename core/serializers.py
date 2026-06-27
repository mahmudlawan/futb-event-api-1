from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Interest, Event
from django.db import transaction


# ─────────────────────────────────────────────
# User read serializer (never exposes password)
# ─────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    interests = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'department', 'faculty', 'role', 'interests']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_interests(self, obj):
        return [interest.category for interest in obj.interests.all()]


# ─────────────────────────────────────────────
# Registration serializer
# ─────────────────────────────────────────────
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    interests = serializers.ListField(
        child=serializers.ChoiceField(choices=Interest.CATEGORY_CHOICES),
        write_only=True
    )
    full_name = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, default='student')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'department', 'faculty', 'interests', 'role']

    @transaction.atomic
    def create(self, validated_data):
        interests_data = validated_data.pop('interests', [])
        full_name = validated_data.pop('full_name', '')

        parts = full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        email = validated_data.get('email')

        user = User.objects.create_user(
            username=email,          # username == email so JWT login works with email
            email=email,
            first_name=first_name,
            last_name=last_name,
            department=validated_data.get('department', ''),
            faculty=validated_data.get('faculty', ''),
            role=validated_data.get('role', 'student'),
            password=validated_data.get('password')
        )

        for category in interests_data:
            Interest.objects.create(user=user, category=category)

        return user


# ─────────────────────────────────────────────
# Custom JWT serializer – injects role & full_name
# ─────────────────────────────────────────────
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Append extra user info to the token response
        data['role'] = self.user.role
        data['full_name'] = self.user.get_full_name() or self.user.username
        return data

# ─────────────────────────────────────────────
# Event serializers
# ─────────────────────────────────────────────
class EventSerializer(serializers.ModelSerializer):
    organiser = serializers.SerializerMethodField()
    spots_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'organiser', 'title', 'description', 'category', 'date_time', 
                  'venue', 'capacity', 'event_type', 'ticket_price', 'status', 
                  'spots_remaining', 'target_faculty', 'target_department', 'created_at']

    def get_organiser(self, obj):
        return {
            "id": obj.organiser.id,
            "full_name": obj.organiser.get_full_name() or obj.organiser.username
        }

    def get_spots_remaining(self, obj):
        # capacity minus number of active tickets issued so far
        active_tickets = obj.tickets.filter(status='active').count()
        return obj.capacity - active_tickets


class EventCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'date_time', 
                  'venue', 'capacity', 'event_type', 'ticket_price',
                  'target_faculty', 'target_department']
