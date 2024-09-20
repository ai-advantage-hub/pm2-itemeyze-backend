from datetime import datetime, timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers
from fcm_django.models import FCMDevice

from .models import (
    User, 
    Company, 
    UserCompany, 
    OTP, 
    Project, 
    Files, 
    UserNotification, 
    Site, 
    ManufacturerName, 
    Settings
)
from custom_admin.models import ContentManagement
from core.common_utils import (
    generate_otp, 
    send_verification_email, 
    update_or_create_fcm_detail, 
    send_reset_password_email
)
from core.exception import CustomException


class UserSerializer():
    """Serializer to serialize user fields"""

    class Meta:
        """meta class"""

        model = User
        fields = ("email", "id", "phone_number", "full_name", "verification_code",)


class SignupSerializer(serializers.ModelSerializer):
    """
    Serializer for Signup
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    company_name = serializers.CharField(required=True)
    full_name = serializers.CharField(required=True)
    profile_pic = serializers.CharField(max_length=254, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ("profile_pic", "full_name", "email", "password", "confirm_password", "company_name")

    @staticmethod
    def validate_email(email: str):
        """
        validate_email method to validate email
        """
        user = User.all_objects.filter(email=email.lower()).first()
        if user:
            if not user.is_active:
                raise CustomException(status_code=400, message="This account has been deactivated by the admin.", location="LOCATION")
            raise CustomException(status_code=400, message="This Email already exists.", location="LOCATION")
        return email.lower()
    

    def validate(self, data):
        """
        validate method to validate passwords
        """
        password = data.get('password')
        confirm_password = data.pop('confirm_password', None)

        if password != confirm_password:
            raise CustomException(status_code=400, message="Passwords do not match.", location="LOCATION")

        return data

    def create(self, validated_data):
        """
        Create method to create user and generate otp
        """
        with transaction.atomic():
            self.validate_email(validated_data.get('email'))

            company_name = validated_data['company_name']
            user = User(email=validated_data['email'], full_name=validated_data['full_name'],
                        profile_pic=validated_data['profile_pic'])
            user.set_password(validated_data['password'])
            user.save()
            if Company.objects.filter(name=company_name).exists():
                c = Company.objects.filter(name=company_name).first()
                UserCompany.objects.create(company=c, user_id=user.id)
            else:
                user.company_name=company_name
                user.save()
            otp = generate_otp()
            OTP.objects.create(user=user, otp=otp, otp_type=1)
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
        log_user = User.all_objects.filter(email=email.lower(), is_active=False).exists()

        if User.all_delete_objects.filter(email=email.lower(), user_role=2, is_deleted=True).exists():
            raise CustomException(status_code=400, message="User is Deleted.", location="Login")

        if log_user:
            raise CustomException(status_code=400, message="Your Account has been Deactivated by Admin", location="Login")

        if user is None:
            raise CustomException(status_code=400, message="Invalid email or password.", location="Login")

        if not user.is_active:
            raise CustomException(status_code=400, message="User account is not active.", location="Login")

        if user.user_role != 2:
            raise CustomException(status_code=400, message="User Does not Exist", location="Login")

        data['is_email_verified'] = user.is_email_verified
        data['is_admin_approved'] = user.is_admin_approved
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
            raise CustomException(status_code=400, message="User Not Found.", location="LOCATION")

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
            raise CustomException(status_code=400, message="Passwords do not match.", location="LOCATION")
        send_reset_password_email(email)
        user = User.objects.filter(email=email.lower()).first()

        data['user'] = user 
        return data

    def update(self, instance, validated_data):
        user = validated_data['user']
        new_password = validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user
    

# Home

class SiteSerializer(serializers.ModelSerializer):
    """
    Serializer for Site model
    """

    class Meta:
        model = Site
        fields = ('id', 'name')


class CreateProjectSerializer(serializers.ModelSerializer):
    """
        CreateProjectSerializer for project creating project
    """
    site_id = serializers.PrimaryKeyRelatedField(queryset=Site.objects.all(), required=True)
    class Meta:
        model = Project
        fields = ("id", "project_name", "created_by", "site_id")


class CreateFileDetailsSerializer(serializers.ModelSerializer):
    """
         CreateFileDetailsSerializer to add the details of files
    """
    manual_manufacturer_name = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Files
        fields = (
            "id", "manufacturer_name", "manual_manufacturer_name", "project_id", "file_name", "thumbnail",
            "manufacturing_number", "quantity", "project_details", "recording", 
            "location", "location_points", "additional_details",
        )
        
    def validate(self, data):
        manufacturing_number = data.get("manufacturing_number")
        project_id = data.get("project_id")

        c = Files.objects.filter(manufacturing_number=manufacturing_number).first()
        if c is not None:
            return data
        return data    
    
    def create(self, validated_data):
        # Retrieve the project_id from the context
        project_id = self.context.get("project_id")
        
        # Set the project_id while creating the Files object
        validated_data["project_id"] = project_id
        
        return super().create(validated_data)
    

class ProjectUserSerializer(serializers.ModelSerializer):
    """
        ProjectUserSerializer serializer to serialize through user model
    """
    class Meta:
        model = User
        fields = ("id", "full_name")


class ProjectManufacturerSerializer(serializers.ModelSerializer):
    """
        ProjectUserSerializer serializer to serialize through user model
    """
    class Meta:
        model = ManufacturerName
        fields = ("id", "name")


class FilesSerializer(serializers.ModelSerializer):
    """
        FilesSerializer serializer to serialize through files model
    """
    manufacturer_name = ProjectManufacturerSerializer()
    manufacturer_name__name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    site_name = serializers.SerializerMethodField()

    class Meta:
        model = Files
        fields = ('id', 'manufacturer_name','manufacturer_name__name','name_manufacturer', 'thumbnail', 'file_name', 'manufacturing_number', 'location', 
                  'quantity', 'project_details', 'is_marked_deleted', 'additional_details', 'is_file_disapproved','disapproved_reason','submitted_to_admin','is_edited','disapproved_file_is_edited','created_at','created_by',
                  'recording', 'is_admin_approved', 'is_marked_deleted','secondary_image','project_name','site_name')
        
    def get_manufacturer_name__name(self, obj):
        # Retrieve the manufacturer name from the related ManufacturerName model
        return obj.manufacturer_name.name if obj.manufacturer_name else None

    def get_project_name(self, obj):
        return obj.project.project_name

    def get_site_name(self, obj):
        return obj.project.site_id.name if obj.project.site_id else None


class ProjectDetailsViewSerializer(serializers.ModelSerializer):
    """
        ProjectDetailsViewSerializer serializer to serialize through project model
    """
    #project_files = FilesSerializer(many=True)
    created_by = ProjectUserSerializer()

    class Meta:
        model = Project
        fields = ("project_name", "project_number", "created_by")


class ContentManagementSerializer(serializers.ModelSerializer):
    """
        ContentManagementSerializer to get the terms and conditions
    """
    class Meta:
        model = ContentManagement
        fields = ('content',)


class ViewUserCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('name',)


class UserCompanySerializer(serializers.ModelSerializer):
    company = ViewUserCompanySerializer()

    class Meta:
        model = UserCompany
        fields = ('id', 'company')


class ViewProfileSerializer(serializers.ModelSerializer):
    # user_company = UserCompanySerializer(many=True)
    user_company = serializers.SerializerMethodField()
    os_versions = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('full_name', 'email', 'profile_pic', 'user_company', 'os_versions')

    def get_user_company(self, obj):
        print("validate")
        a = UserCompany.objects.filter(user=obj).values_list('company_id', flat=True)
        print("a===", a)
        company_list = []
        for i in a:
            company = Company.objects.filter(id=i, is_active=True).first()
            if company:
                company_list.append({'id': company.id, 'name': company.name})
        return company_list
    
    def get_os_versions(self, obj):
        settings = Settings.objects.filter(Q(name='ios') | Q(name='android')).values("name", "value")
        return settings


class UserListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'full_name')


class CompanyNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('id', 'name')
        

class UserChangePasswordSerializer(serializers.Serializer):
    """
        UserChangePasswordSerializer to change the password of user
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
            raise CustomException(status_code=400, message="User Not Found.", location="LOCATION")

        if not check_password(old_password, user.password):
            raise CustomException(status_code=400, message="Incorrect Old Password.", location="LOCATION")

        if new_password != confirm_password:
            raise CustomException(status_code=400, message="New Password and Confirm Password Should be Same.", location="LOCATION")

        return data

    def update_password(self, user):
        new_password = self.validated_data.get("new_password")
        user.set_password(new_password)
        user.save()


# FCM Device

class UserDeviceDetailSerializer(serializers.ModelSerializer):
    """
        UserDeviceDetailSerializer used to get the user details.
    """
    class Meta:
        model = FCMDevice
        fields = ('id', 'user', 'registration_id', 'type',)


class UserDeviceSerializer(serializers.Serializer):
    """
        UserDeviceSerializer used to save the user details.
    """
    DEVICE_CHOICE = (
        'ios', 'ios',
        'android', 'android',
        'web', 'web'
    )

    device_type = serializers.ChoiceField(choices=DEVICE_CHOICE, required=True)
    registration_id = serializers.CharField(required=True, min_length=10)

    def update(self, instance, validated_data):
        """
            method used to update the fcm details.
        """
        print("printttt")
        with transaction.atomic():
            update_or_create_fcm_detail(instance, validated_data.get('registration_id'),
                                        validated_data.get('device_type'))
            return True
        

class NotificationListSerializer(serializers.ModelSerializer):
    """
        NotificationSerializer used to get list of Notification.
    """
    #data = serializers.SerializerMethodField()

    def get_data(self, obj):
        data_dict = eval(str(obj.data))
        return data_dict

    class Meta:
        model = UserNotification
        fields = ('id', 'user', 'title',
                  'message', 'is_read', 'created_at')
