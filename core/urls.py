from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, CustomTokenObtainPairView, ProfileView, LogoutView,
    EventListCreateView, EventDetailView, RecommendedEventsView,
    FreeEventRegisterView, MyTicketsView, InitiatePaymentView, VerifyPaymentView,
    FCMTokenUpdateView, TestReminderView
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/fcm-token/', FCMTokenUpdateView.as_view(), name='fcm-token'),
    
    path('events/', EventListCreateView.as_view(), name='event-list-create'),
    path('events/recommended/', RecommendedEventsView.as_view(), name='event-recommended'),
    path('events/<int:pk>/', EventDetailView.as_view(), name='event-detail'),
    path('events/<int:pk>/register/', FreeEventRegisterView.as_view(), name='free-event-register'),
    path('events/<int:pk>/pay/', InitiatePaymentView.as_view(), name='initiate-payment'),
    
    path('tickets/my/', MyTicketsView.as_view(), name='my-tickets'),
    path('payments/verify/<str:reference>/', VerifyPaymentView.as_view(), name='verify-payment'),
    
    path('notifications/test-reminder/', TestReminderView.as_view(), name='test-reminder'),
]
