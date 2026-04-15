from rest_framework.permissions import BasePermission


class IsStaffUser(BasePermission):
    """
    Allow access only to users with is_staff=True.
    Used for all admin dashboard endpoints.
    """
    message = 'You do not have staff privileges to access this resource.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
