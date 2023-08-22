""" check for user role here and apply them in every api """
# import 
from rest_framework.permissions import BasePermission
from users.models import User


class CheckAdminRoleStatusPermission(BasePermission):
    """
        CheckAdminRoleStatusPermission class used to check Admin Role Status Is active or not.
    """
    message = "Permission is allowed only to admin user."

    def has_permission(self, request, view):
        if User.objects.filter(id=request.user.id, user_role=1,
                               is_active=True).exists():
            return True
        return False