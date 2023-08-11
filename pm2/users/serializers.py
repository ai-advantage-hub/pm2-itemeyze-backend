from rest_framework import serializers
from .models import User, Company, UserCompany, OTP
from core.common_utils import send_signup_verification_email, generate_otp, send_forgot_password_email

class UserSerializer():
    """Serializer to serialize user fields"""

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


class SignupSerializer(serializers.ModelSerializer):
    """
        Serializer for Signup
    """
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)
    company_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("full_name", "email", "password", "confirm_password", "company_id")

    def validate_email(self, email):
        """
            validate_email method to validate email
        """
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("This Email already exists.")
        return email

    def validate(self, data):
        """
            validate method to validate passwords
        """
        password = data.get('password')
        confirm_password = data.pop('confirm_password', None)

        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")

        return data
    
    def create(self, validated_data):
        """
            Create method to create user and generate otp
        """
        company_id = validated_data['company_id'] 
        user = User(email=validated_data['email'],full_name=validated_data['full_name'])
        user.set_password(validated_data['password'])
        user.save()
        UserCompany.objects.create(user=user, company_id=company_id)
        otp = generate_otp()
        OTP.objects.create(user=user,otp=otp,otp_type=1)
        send_forgot_password_email(user.email, otp)
        return user










