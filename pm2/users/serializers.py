from rest_framework import serializers
from .models import User, Company, UserCompany, OTP
from core.common_utils import generate_otp, send_verification_email
from django.contrib.auth import authenticate
import re
from django.utils import timezone



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
    
    def validate_password(self, password):
        if not re.search(r'[A-Z]', password):
            raise serializers.ValidationError("Password must contain at least 1 uppercase letter.")
        if not re.search(r'[a-z]', password):
            raise serializers.ValidationError("Password must contain at least 1 lowercase letter.")
        if not re.search(r'[0-9]', password):
            raise serializers.ValidationError("Password must contain at least 1 numeric character.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise serializers.ValidationError("Password must contain at least 1 special character.")
        return password

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
        send_verification_email(user.email, otp)
        return user
        

class UserLoginSerializer(serializers.Serializer):
    """
        UserLoginSerializer for User Login
    """
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data['email']
        password = data['password']
        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError({"message": "Invalid email or password."})

        # if not user.is_active:
        #     raise serializers.ValidationError({"message": "User account is not active."})

        # if not user.is_admin_approved:
        #     raise serializers.ValidationError({"message": "User is not approved by admin."})

        # if not user.is_email_verified:
        #     raise serializers.ValidationError({"message": "User email is not verified."})

        # if user.is_admin_approved == False or user.is_email_verified == False:
        #     raise serializers.ValidationError({"message": "User is not approved by admin or email is not verified."})

        data['user'] = user
        return data

    class Meta:
        model = User
        fields = ('email', 'password')


class ForgotPasswordSerializer(serializers.Serializer):
    """
       ForgotPasswordSerializer serializer will be used when user forget the password 
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)

    def create(self, validated_data):
        instance = User.objects.filter(user_role=User.USER,
                                       email=validated_data.get('email').lower()).only('id', 'email', ).first()
        if not instance:
            raise serializers.ValidationError({"message": "User not found."})

        # Generate forgot password OTP
        otp = generate_otp()
        OTP.objects.create(user=instance,otp=otp,otp_type=3)
        try:
            send_verification_email(instance.email, otp)
        except BaseException:
            pass
        
        return True
    

class ResetPasswordSerializer(serializers.Serializer):
    """
        ResetPasswordSerializer serializer used for reseting the password
    """
    email = serializers.EmailField(min_length=6, required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True, min_length=8)

    def validate(self, data):
        email = data.get('email')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({"message": "Passwords do not match."})
        user = User.objects.filter(email=email).first()

        data['user'] = user 
        return data

    def update(self, instance, validated_data):
        user = validated_data['user']
        new_password = validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user









