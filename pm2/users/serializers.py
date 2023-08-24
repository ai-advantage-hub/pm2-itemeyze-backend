from rest_framework import serializers
from .models import User, Company, UserCompany, OTP, Project, Files
from custom_admin.models import ContentManagement
from core.common_utils import generate_otp, send_verification_email
from django.contrib.auth import authenticate
import re
from core.exception import CustomException
from django.utils import timezone
from django.db import transaction




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
    email = serializers.EmailField(min_length=5, max_length=50, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    company_id = serializers.IntegerField(write_only=True, required=True)
    full_name = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ("profile_pic", "full_name", "email", "password", "confirm_password", "company_id")

    @staticmethod
    def validate_email(email:str):
        """
            validate_email method to validate email
        """
        if User.objects.filter(email=email.lower()).exists():
            raise CustomException(status_code=400, message="This Email already exists.",
                                          location="LOCATION")
        return email.lower()
    
    # def validate_password(self, password):
    #     if not re.search(r'[A-Z]', password):
    #         # raise CustomException(status_code=400, message="Password must contain at least 1 uppercase letter.",
    #         #                       location="LOCATION")
    #         raise serializers.ValidationError("Password must contain at least 1 uppercase letter.")
    #     if not re.search(r'[a-z]', password):
    #         raise serializers.ValidationError("Password must contain at least 1 lowercase letter.")
    #     if not re.search(r'[0-9]', password):
    #         raise serializers.ValidationError("Password must contain at least 1 numeric character.")
    #     if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
    #         raise serializers.ValidationError("Password must contain at least 1 special character.")
    #     return password

    def validate(self, data):
        """
            validate method to validate passwords
        """
        password = data.get('password')
        confirm_password = data.pop('confirm_password', None)

        if password != confirm_password:
            raise CustomException(status_code=400, message="Passwords do not match.",
                                          location="LOCATION")
            # raise serializers.ValidationError("Passwords do not match.")

        return data
    
    def validate_company(self, request):
        data = request.data
        company_id = data.get('company_id')
        c = Company.objects.filter(id=company_id).first()
        if not c:
            raise CustomException(status_code=400, message="Company Not Found.",
                                          location="LOCATION")
           
        

    
    # def create(self, validated_data):
    #     """
    #         Create method to create user and generate otp
    #     """
    #     with transaction.atomic():
    #         self.validate_email(validated_data.get('email'))
    #         company_id = validated_data['company_id'] 
    #         user = User(email=validated_data['email'],full_name=validated_data['full_name'])
    #         user.set_password(validated_data['password'])
    #         user.save()
    #         UserCompany.objects.create(user=user, company_id=company_id)
    #         otp = generate_otp()
    #         OTP.objects.create(user=user,otp=otp,otp_type=1)
    #         send_verification_email(user.email, otp)
    #         return user

    def create(self, validated_data):
        """
        Create method to create user and generate otp
        """
        with transaction.atomic():
            self.validate_email(validated_data.get('email'))
            
            company_id = validated_data['company_id']
            c = Company.objects.filter(id=company_id).first()
            if not c:
                raise CustomException(status_code=400, message="Company Not Found.", location="LOCATION")
            
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
        user = authenticate(email=email.lower(), password=password)

        if user is None:
            raise CustomException(status_code=400, message="Invalid email or password.",
                                          location="Login")

        # if not user.is_active:
        #     raise serializers.ValidationError({"message": "User account is not active."})

        # if not user.is_admin_approved:
        #     raise serializers.ValidationError({"message": "User is not approved by admin."})

        if not user.is_email_verified:
            otp = generate_otp()
            OTP.objects.create(user=user,otp=otp,otp_type=1)
            send_verification_email(user.email, otp)
            raise CustomException(status_code=400, message= "User email is not verified. Please check your email inbox.", location="server")
        

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
    

#Home

class CreateProjectSerializer(serializers.ModelSerializer):
    """
        CreateProjectSerializer for project creating project
    """

    # def create(self, validated_data):
    #     """
    #     """
    #     instance = Project.objects.create(validated_data)
    #     instance.users.add()
    #     return instance

    class Meta:
        model = Project
        fields = ("id", "project_name", "created_by")


class CreateFileDetailsSerializer(serializers.ModelSerializer):
    """
         CreateFileDetailsSerializer to add the details of files
    """
    class Meta:
        model = Files
        fields = (
            "id", "manufacturer_name", "project_id", "file_name", "thumbnail",
            "manufacturing_number", "quantity", "project_details", "recording", "location", "location_points"
        )
        
    def validate(self, data):
        manufacturing_number = data.get("manufacturing_number")
        project_id = data.get("project_id")

        c = Files.objects.filter(manufacturing_number=manufacturing_number).first()
        if c is not None:
            a = c.manufacturing_number
            if Files.objects.filter(manufacturing_number=a).exists():
                raise serializers.ValidationError("A file with this manufacturing number already exists for the project.")
            else:
                print("No Files object found with the given manufacturing number.")
        return data
    
    def create(self, validated_data):
        # Retrieve the project_id from the context
        project_id = self.context.get("project_id")
        
        # Set the project_id while creating the Files object
        validated_data["project_id"] = project_id
        
        return super().create(validated_data)
    

class ProjectUserSerializer(serializers.ModelSerializer):
    """
        ProjectUserSerializer serializer to serilaize through user model
    """
    class Meta:
        model = User
        fields = ("full_name",)


class FilesSerializer(serializers.ModelSerializer):
    """
        FilesSerializer serializer to serialize through files model
    """
    class Meta:
        model = Files
        fields = ('__all__')


class ProjectDetailsViewSerializer(serializers.ModelSerializer):
    """
        ProjectDetailsViewSerializer serializer to serialize through project model
    """
    project_files = FilesSerializer(many=True)
    created_by = ProjectUserSerializer()
    class Meta:
        model = Project
        fields = ("project_name", "project_number", "created_by", "project_files",)


class ContentManagementSerializer(serializers.ModelSerializer):
    """
        ContentManagementSerializer to get the terms and conditions
    """
    class Meta:
        model = ContentManagement
        fields = ('content',)
    




