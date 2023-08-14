from rest_framework import serializers
from users.models import *
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import check_password

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data['email']
        password = data['password']
        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError({"message": "Invalid email or password."})

        if user.user_role != 1 or not user.is_admin_approved:
            raise serializers.ValidationError({"message": "User is not an admin."})

        data['user'] = user
        return data

    class Meta:
        model = User
        fields = ('email', 'password')


class AdminResetPasswordSerializer(serializers.Serializer):
    """
    
    """
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()

    def validate(self, data):
        user = self.context['request'].user
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        if not user:
            raise serializers.ValidationError({"message": "Admin user not found."})

        if not check_password(old_password, user.password):
            raise serializers.ValidationError({"message": "Old password is incorrect."})

        if new_password != confirm_password:
            raise serializers.ValidationError({"message": "Both passwords are not the same."})

        return data

    def update_password(self):
        user = self.context['request'].user
        new_password = self.validated_data.get("new_password")
        user.set_password(new_password)
        user.save()