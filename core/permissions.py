from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """
    Allows access only to users with the 'student' role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'student')

class IsOrganiser(permissions.BasePermission):
    """
    Allows access only to users with the 'organiser' role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'organiser')

class IsAdminRole(permissions.BasePermission):
    """
    Allows access only to users with the 'admin' role.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')
