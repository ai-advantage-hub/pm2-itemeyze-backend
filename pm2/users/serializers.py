from rest_framework import serializers
from .models import User

class UserSerializer():
    """Serializer to serializer user fields"""

    class Meta:
        """meta class"""

        model = User
        fields = (
            "email",
            "id",
            "phone_number",
            "full_name",
            "verification_code",
        )

# class SignupSerializer(serializers.ModelSerializer):
#     email = serializers.EmailField(required=True, min_length=3, max_length=70)
#     password = serializers.CharField(write_only=True, required=True, min_length=8)
#     confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)
#     full_name = serializers.CharField(required=True, max_length=150)
#     company_name = serializers.CharField(required=True, max_length=150)

#     def validate_email(self, email):
#         if User.objects.filter(email=email).exists():
#             raise serializers.ValidationError("This Email already exists.")
#         return email

#     def validate(self, data):
#         password = data.get('password')
#         confirm_password = data.pop('confirm_password', None)

#         if password != confirm_password:
#             raise serializers.ValidationError("Passwords do not match.")

#         return data

#     def create(self, validated_data):
#         user = User.objects.create_user(
#             username=validated_data['email'],
#             email=validated_data['email'],
#             password=validated_data['password']
#         )
#         user.first_name = validated_data['full_name']
#         user.save()
#         return user

#     class Meta:
#         model = User
#         fields = ("full_name", "email", "password", "confirm_password", "company_name")

class SignupSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = User
        fields = ("full_name", "email", "password", "confirm_password")

    def validate_email(self, email):
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("This Email already exists.")
        return email

    def validate(self, data):
        password = data.get('password')
        confirm_password = data.pop('confirm_password', None)

        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")

        return data

    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name']
        )
        return user







