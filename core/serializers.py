from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Interest
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

    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'department', 'faculty', 'interests']

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
            role='student',
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
