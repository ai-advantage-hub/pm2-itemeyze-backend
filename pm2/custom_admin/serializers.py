from rest_framework import serializers
from users.models import *
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import check_password
from core.common_utils import generate_otp, send_verification_email, send_verification_link
from django.contrib.gis.geos import Point
from core.exception import CustomException


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data['email']
        password = data['password']
        user = authenticate(email=email.lower(), password=password)
        log_user = User.all_objects.filter(email=email.lower(), is_active=False, user_role=3).exists()

        if User.all_delete_objects.filter(email=email.lower(), user_role=3, is_deleted=True).exists():
            raise CustomException(status_code=400, message= "Subadmin is Deleted.", location="Login")
        
        if log_user:
            raise CustomException(status_code=400, message= "Subadmin is Inactive.", location="Login")
        
        if user is None:
            raise CustomException(status_code=400, message = "Invalid email or password.", location="Login")

        if user.user_role == 2 or user.is_email_verified is False:
            raise CustomException(status_code=400, message= "User is not an admin.", location="Login")
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
        fields = ['id', 'file_name', 'thumbnail', 'manufacturing_number', 'quantity', 'project_details', 'additional_details', 'recording', 'location', 'location_points','created_at', 'is_file_disapproved', 'disapproved_reason']


class ProjectDetailSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site_id.name', read_only=True)
    created_by = serializers.SerializerMethodField()
    files = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id','project_name', 'project_number','created_by','created_at','site_id_id','site_name', 'files']

    def get_created_by(self, obj):
        try:
            return obj.created_by.full_name
        except AttributeError:            
            return None
    
    def get_files(self, obj):
        approved_files = obj.project_files.filter(is_marked_deleted=False, is_deleted=False, is_admin_approved=True)
        return FileSerializer(approved_files, many=True).data


class FilesSerializer(serializers.ModelSerializer):
    manufacturer_name = serializers.PrimaryKeyRelatedField(queryset=ManufacturerName.objects.all())
    #project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = Files
        fields = '__all__'
    
    def update(self, instance, validated_data):
        validated_data['is_admin_approved'] = True
        validated_data['is_marked_deleted'] = False

        return super().update(instance, validated_data)
    
    
class FilesPointSerializer(serializers.ModelSerializer):
    """
       Serializer for view file details
    """

    location_points = serializers.SerializerMethodField()
    
    class Meta:
        model = Files
        fields = '__all__'

    def get_location_points(self, obj):
        if obj.location_points:
            return {'longitude': obj.location_points.x, 'latitude': obj.location_points.y}
        return None
    

#Manage Users 

class UserListCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('name',)

class UserListProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('project_name',)

class UserListUserCompanySerializer(serializers.ModelSerializer):
    company_user = UserListCompanySerializer()
    class Meta:
        model = UserCompany
        fields = ('company_name', 'company_user')

class UserListAdminSerializer(serializers.ModelSerializer):
    # total_projects = serializers.SerializerMethodField()
    # company = UserListCompanySerializer(source='user_company')
    company = UserListUserCompanySerializer()  # Assuming ForeignKey relationship named 'company'
    total_projects = serializers.IntegerField(source='project_set.count', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'total_projects', 'company')

    def get_total_projects(self, obj):
        return Project.objects.filter(created_by=obj).count()
    

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


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ['id','name']


class ProjectSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site_id.name', read_only=True)
    class Meta:
        model = Project
        fields = ['id', 'project_name', 'created_at','site_id','site_name']

class UserDetailSerializer(serializers.ModelSerializer):
    company_names = serializers.SerializerMethodField()
    assigned_projects = ProjectSerializer(many=True)
    created_by_project = ProjectSerializer(many=True)

    class Meta:
        model = User
        fields = ['id','full_name', 'email','profile_pic','modules_accessible','created_at','company_names', 'assigned_projects','created_by_project']

    def get_company_names(self, obj):
        return [uc.company.name for uc in obj.user_company.all()]
    
    

class UserListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'full_name', 'email')