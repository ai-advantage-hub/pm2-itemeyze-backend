from rest_framework import serializers
from users.models import *
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import check_password
from core.common_utils import generate_otp, send_verification_email, send_verification_link

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data['email']
        password = data['password']
        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError({"message": "Invalid email or password."})

        if user.user_role != 1 or user.is_email_verified is False:
            raise serializers.ValidationError({"message": "User is not an admin."})
        data['user'] = user
        return data

    class Meta:
        model = User
        fields = ('email', 'password')


class AdminResetPasswordSerializer(serializers.Serializer):
    """
    admin reset password
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
            raise serializers.ValidationError({"message": "Incorrect old password."})

        if new_password != confirm_password:
            raise serializers.ValidationError({"message": "New password and Confirm password should be same."})

        return data

    def update_password(self):
        user = self.context['request'].user
        new_password = self.validated_data.get("new_password")
        user.set_password(new_password)
        user.save()


class ForgotPasswordSerializer(serializers.Serializer):
    """
       ForgotPasswordSerializer serializer will be used when user forget the password 
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)

    def create(self, validated_data):
        instance = User.objects.filter(email=validated_data.get('email')).first()
        if not instance:
            raise serializers.ValidationError({"message": "User not found."})

        # Generate forgot password OTP
        otp = generate_otp()
        OTP.objects.update_or_create(user=instance,otp=otp,otp_type=3)
        print(otp,instance.email)
        try:
            send_verification_link(instance.email, otp)
        except BaseException:
            pass
        
        return True
    
class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Files
        fields = ['file_name', 'thumbnail', 'manufacturing_number', 'quantity', 'project_details', 'additional_details', 'recording', 'location', 'location_points']

class ProjectDetailSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    files = FileSerializer(source='project_files', many=True, read_only=True)

    class Meta:
        model = Project
        fields = ['project_name', 'project_number','created_by','created_at', 'files']

    def get_created_by(self, obj):
        return obj.created_by.full_name
    
    def get_files(self, obj):
        approved_files = obj.project_files.filter(is_admin_approved=True)
        return FileSerializer(approved_files, many=True).data


class FilesSerializer(serializers.ModelSerializer):
    manufacturer_name = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    #project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = Files
        fields = '__all__'