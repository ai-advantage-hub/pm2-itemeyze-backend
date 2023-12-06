from django.shortcuts import render
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from .models import (
    User, 
    OTP, 
    Project, 
    Files, 
    Company,
    UserCompany,
    UserNotification,
    Site,
    ManufacturerName

)
from custom_admin.models import ContentManagement
from .serializers import (
    SignupSerializer, 
    UserLoginSerializer, 
    ForgotPasswordSerializer, 
    ResetPasswordSerializer, 
    CreateProjectSerializer, 
    CreateFileDetailsSerializer, 
    ProjectDetailsViewSerializer, 
    ContentManagementSerializer, 
    UserListingSerializer, 
    CompanyNameSerializer, 
    ViewProfileSerializer, 
    UserChangePasswordSerializer,
    FilesSerializer,
    UserDeviceDetailSerializer,
    UserDeviceSerializer,
    NotificationListSerializer
    
)
from rest_framework.authtoken.models import Token
from core.common_utils import generate_otp, send_verification_email, send_notification_bulk, send_edit_profile_verification_email
from core.response import CustomResponse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework import status as status_code
from django.utils import timezone
from core.messages import SUCCESS_MESSAGES 
from django.utils.translation import gettext
from rest_framework.permissions import IsAuthenticated, AllowAny
from core.permissions import CheckUserRoleStatusPermission
from django.db.models import Q
from fcm_django.models import FCMDevice
from core.pagination import CustomPagination


#Onboarding

class SignUpViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """ 
        Signup view where user provides basic information and should be able to signup
    """
    serializer_class = SignupSerializer 

    def create(self, request, *args, **kwargs):
        """ 
            Method for user signup
        """
        data = request.data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('OTP_SENT'))}, status=status_code.HTTP_200_OK)
    

class ReSendOtpViewSet(viewsets.ViewSet):
    """
        ReSendOtpViewSet used for resending the otp on email  
    """
    def create(self, request):
        """
            method to resend otp
        """
        data = request.data
        email = data.get("email")
        if not email:
            return CustomResponse({"message": "Please enter email"})
        user = User.objects.filter(email=email.lower()).first()
        otp = generate_otp()
        OTP.objects.create(user=user, otp_type=1, otp=otp, is_used=False)
        try:
            send_verification_email(user.email, otp)
        except Exception as e:
            print(e)
        return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('RESEND_EMAIL_OTP')), "otp": otp}, status=status_code.HTTP_200_OK)
    

class VerifyOTPViewSet(viewsets.ViewSet):
    """
        VerifyOTPViewSet used for verifying the otp  
    """
    def create(self, request):
        """
            method to verify otp
        """
        data = request.data
        otp = data.get('otp')
        email = data.get('email')
        type = data.get('type')

        # will remove in future
        if otp == "1234":
            user = User.objects.filter(email=email.lower()).first()
            user.is_email_verified = True
            user.save()
            return CustomResponse({"message": "OTP Verified, User created Successfully", "user_id": user.id}, status=status_code.HTTP_200_OK)

        user = OTP.objects.filter(otp=otp, otp_type=type, is_used=False).first()
        if not user:
            return CustomResponse({"message": "Wrong OTP"})
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"})
        else:
            user_id = user.user_id
            User.objects.filter(email=email.lower()).update(is_email_verified=True)
            OTP.objects.filter(otp=otp, otp_type=type).update(is_used=True)
            return CustomResponse({"message": "OTP Verified, User created Successfully", "user_id": user_id}, status=status_code.HTTP_200_OK)


class UserLoginViewSet(viewsets.ViewSet):
    """
        UserLoginViewSet for User Login
    """ 
    def create(self, request):
        """
            method to login
        """
        serializer = UserLoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            is_email_verified = user.is_email_verified
            is_admin_approved = user.is_admin_approved

            response_data = {
                "is_email_verified": is_email_verified,
            }

            if not is_email_verified:
                response_data["msg"] = "User email is not verified. Please check your email inbox."
            else:
                response_data["is_admin_approved"] = is_admin_approved

                if is_email_verified and is_admin_approved:
                    if not UserCompany.objects.filter(user=user, company__is_active=True):
                        # The company exists for the user
                        response_data["msg"] = "User Company Does not Exist"
                        token, created = Token.objects.get_or_create(user=user)
                        response_data["token"] = token.key
                    else:
                        token, created = Token.objects.get_or_create(user=user)
                        response_data["token"] = token.key
                        return CustomResponse(response_data, status=status_code.HTTP_200_OK)
                else:
                    response_data["msg"] = "Your account has been sent to admin for approval."
                    response_data["is_admin_approved"] = False

            # This line will be executed when token is created
            return CustomResponse(response_data, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse({"msg": "Please provide valid Credentials"}, status=status_code.HTTP_400_BAD_REQUEST)

        
class ForgotPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
        ForgotPasswordViewSet for forget password
    """
    serializer_class = ForgotPasswordSerializer

    def create(self, request):
        """
            function for forgot password
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return CustomResponse({"message": "OTP Sent Successfully"}, status=status_code.HTTP_200_OK)
    

class ResetPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
       ResetPasswordViewSet will be used for reseting the password 
    """
    serializer_class = ResetPasswordSerializer

    def update(self, request):
        """
            function for reset password
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if not user:
            return CustomResponse({"message": "User not found."}, status=status_code.HTTP_400_BAD_REQUEST)
        serializer.update(user, serializer.validated_data)
        return CustomResponse({"message": "Password reset successfully."}, status=status_code.HTTP_200_OK)


class UserNameViewSet(viewsets.ViewSet):
    """
        UserNameViewSet to give the name of User
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def get(self, request, *args, **kwargs):
        """
            function to give the name of user
        """
        name = User.objects.filter(id=request.user.id).all().values('id', 'full_name')
        return CustomResponse(name, status=status_code.HTTP_200_OK) 


#Home

class ProjectViewSet(viewsets.ModelViewSet):
    """
        CreateProjectViewSet to create project
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)
    queryset = Project.objects.all()
    serializer_class = CreateProjectSerializer
    pagination_class = CustomPagination

    # def create(self, request, *args, **kwargs):
    #     """
    #         function to create project
    #     """
    #     project_name = request.data.get('project_name')
    #     user = request.user 
    #     if not project_name:
    #         return CustomResponse({"message": "Project name cannot be empty."}, status=status_code.HTTP_400_BAD_REQUEST)

    #     # Check if the project name is unique
    #     if Project.objects.filter(project_name=project_name).exists():
    #         return CustomResponse({"message": "Project with this name already exists."}, status=status_code.HTTP_400_BAD_REQUEST)

    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     serializer.save(created_by=user)
    #     project = Project.objects.filter(id=serializer.instance.id).first()
    #     project.users.add(user)

    #     return CustomResponse(serializer.data, status=status_code.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):
        """
            function to create project
        """
        project_name = request.data.get('project_name')
        site_name = request.data.get('site_name')
        if not project_name:
            return CustomResponse({"message": "Project name cannot be empty."}, status=status_code.HTTP_400_BAD_REQUEST)
        
        if not site_name:
            return CustomResponse({"message": "Site Name cannot be empty."}, status=status_code.HTTP_400_BAD_REQUEST)

        # Check if the project name is unique
        if Project.objects.filter(project_name=project_name).exists():
            return CustomResponse({"message": "Project with this name already exists."}, status=status_code.HTTP_400_BAD_REQUEST)
        # site = Site.objects.create(name=site_name)
        if Site.objects.filter(name=site_name.lower()).exists():
            site = Site.objects.filter(name=site_name.lower()).first()
            print("site", site)
        else:
            site = Site.objects.create(name=site_name.lower())
            print("site2", site)

        project = Project.objects.create(created_by = request.user, project_name=project_name, site_id_id=site.id)
        if site_name.lower()=='pm2':
            project.is_internal=True
            project.save()
        else:
            project.is_internal=False
            project.save()
        return CustomResponse({"message": "Project Created Successfully.","project_id":project.id,"project_name":project_name}, status=status_code.HTTP_200_OK)

        # serializer = self.get_serializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        # serializer.save(created_by=user)
        # project = Project.objects.filter(id=serializer.instance.id).first()
        # project.users.add(user)

        # return CustomResponse(serializer.data, status=status_code.HTTP_201_CREATED)

    def search(self, request):
        """
            Method to list and search for the projects.
        """
        project_name = request.GET.get('project_name', None)
        page_size = request.GET.get('page_size', '')
        print("user====",request.user.id)
        projects = Project.objects.filter(
            created_by=request.user,
            is_admin_approved=True, is_marked_deleted=False
            ).values(
            'id', 'created_at', 'updated_at', 'project_name', 'project_description',
            'is_admin_approved', 'is_marked_deleted', 'project_number', 'created_by_id',
            'site_id_id', 'site_id__name'
            ).order_by('-created_at')
        if project_name:
            projects = projects.filter(project_name__icontains=project_name)

        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(projects, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(projects)
        

class FileDetailsViewSet(viewsets.ModelViewSet):
    """
        CreateFileDetailsViewSet to add file details
    """
    queryset = Files.objects.all()
    serializer_class = CreateFileDetailsSerializer
    pagination_class = CustomPagination
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def perform_create(self, serializer):
        serializer.save(file_name="autogenerated_filename")

    # def create(self, request, *args, **kwargs):
    #     """
    #         function to create file
    #     """
    #     data = request.data
    #     manufacturer_name = data.get('manufacturer_name')
    #     manual_manufacturer_name = data.get('manual_manufacturer_name')
    #     project_id = data.get('project_id')
    #     thumbnail = data.get('thumbnail')
    #     manufacturing_number = data.get('manufacturing_number')
    #     quantity = data.get('quantity')
    #     project_details = data.get('project_details')
    #     additional_details = data.get('additional_details')
    #     recording = data.get('recording')
    #     location = data.get('location')
    #     location_points = data.get('location_points')
    #     if manual_manufacturer_name:
    #         new_user = User.objects.create(full_name=manual_manufacturer_name)
    #         file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_user.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points)
    #         c = str(project_id)+'_'+str(file.id)+'_'+'filename'
    #         b = Files.objects.filter(id=file.id).update(file_name=c)
    #         return CustomResponse({"message": "File Created with new user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)
    #     else:
    #         file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, file_name='autogenerated_filename')
    #         c = str(project_id)+'_'+str(file.id)+'_'+'filename'
    #         b = Files.objects.filter(id=file.id).update(file_name=c)
    #         return CustomResponse({"message": "File Created with existing user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)
    
        
    def list(self, request, id, *args, **kwargs):
        """
            function to give list of file
        """
        user = Files.objects.filter(id=id).all().values('file_name','thumbnail','name_manufacturer','manufacturer_name__name', 'manufacturer_name__id','manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording')
        return CustomResponse(user)

    def create(self, request, *args, **kwargs):
        """
            function to create file
        """
        data = request.data
        manufacturer_name = data.get('manufacturer_name')
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        project_id = data.get('project_id')
        thumbnail = data.get('thumbnail')
        manufacturing_number = data.get('manufacturing_number')
        quantity = data.get('quantity')
        project_details = data.get('project_details')
        additional_details = data.get('additional_details')
        recording = data.get('recording')
        location = data.get('location')
        location_points = data.get('location_points')
        if manual_manufacturer_name:
            new_user = User.objects.create(full_name=manual_manufacturer_name)
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_user.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with new user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)
        else:
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with existing user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)
        
    
    def manufacturer_list(self, request):
        """
            function to give list of manufacturers
        """
        name = request.GET.get('name', None)
        manufacturers = ManufacturerName.objects.all().values('id','name')
        if name:
            manufacturers = manufacturers.filter(name__icontains=name)
        return CustomResponse(manufacturers)
        
    
    def create_file(self, request, *args, **kwargs):
        """
            function to create file
        """
        data = request.data
        manufacturer_name = data.get('manufacturer_name')
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        project_id = data.get('project_id')
        thumbnail = data.get('thumbnail')
        manufacturing_number = data.get('manufacturing_number')
        quantity = data.get('quantity')
        project_details = data.get('project_details')
        additional_details = data.get('additional_details')
        recording = data.get('recording')
        location = data.get('location')
        location_points = data.get('location_points')
        if manual_manufacturer_name:
            print("in manual")
            new_manufacturer = ManufacturerName.objects.create(users = request.user,name=manual_manufacturer_name, added_by=2, is_read=False)
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            e = ManufacturerName.objects.filter(id=new_manufacturer.id).first()
            print("eee",e.name)
            b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
            
            return CustomResponse({"message": "File Created with new Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            e = ManufacturerName.objects.filter(id=manufacturer_name).first()
            print("eee",e.name)
            b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
            return CustomResponse({"message": "File Created with existing Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)

    def user_saved_list(self, request, id):
        """
            function to give list of those files which are created by user and not submitted to admin
        """
        if not Project.objects.filter(id=id).exists():
            return CustomResponse({"message": "Project of this id does not exist"}, status=status_code.HTTP_400_BAD_REQUEST)
        files = Files.objects.filter(project_id = id, created_by=request.user, submitted_to_admin=False, is_marked_deleted=False).all().values('id','file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason')
        return CustomResponse(files)
    
    def submit_to_admin(self, request):
        """
            function to submit files to admin
        """
        data = request.data
        file_id = data.get("file_id", [])
        if not file_id:
                return CustomResponse({"message": "Please select file"}, status=status_code.HTTP_400_BAD_REQUEST)
        # if not Files.objects.filter(id=file_id).exists():
        #     return CustomResponse({"message": "File Not Found"}, status=status_code.HTTP_400_BAD_REQUEST)
        for i in file_id:
            print("i",i)
            Files.objects.filter(id=i).update(submitted_to_admin=True)
        return CustomResponse({"message": "Files submitted to admin"}, status=status_code.HTTP_200_OK)
    
    def submitted_to_admin_list(self, request, id):
        """
            function to give list of those files which are submitted to admin
        """
        if not Project.objects.filter(id=id).exists():
            return CustomResponse({"message": "Project of this id does not exist"}, status=status_code.HTTP_400_BAD_REQUEST)
        files = Files.objects.filter(project_id=id, created_by=request.user, is_admin_approved=True, submitted_to_admin=True).all().values('id','file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason')
        return CustomResponse(files)
    
    def file_list(self, request, id):
        """
        function to give a list of files based on the provided filter
        """
        list_type = request.GET.get('list_type', None)
        name = request.GET.get('name', None)
        page_size = request.GET.get('page_size', '')
        if not Project.objects.filter(id=id).exists():
            return CustomResponse({"message": "Project of this id does not exist"}, status=status_code.HTTP_400_BAD_REQUEST)

        if list_type == '1':
            # files = Files.objects.filter(project_id = id, created_by=request.user, submitted_to_admin=False, is_marked_deleted=False).all().values('id','file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason')
            if name == None:
                files = Files.objects.filter(project_id=id, created_by=request.user,submitted_to_admin=False, is_marked_deleted=False).all().values('id','file_name','thumbnail','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason').order_by('-created_at')
            else:
                files = Files.objects.filter(Q(location__icontains=name) |
                                        Q(manufacturer_name__name__icontains=name) |
                                        Q(manufacturing_number__icontains=name),
                                        project_id=id, created_by=request.user,submitted_to_admin=False, is_marked_deleted=False).all().values('id','file_name','thumbnail','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason').order_by('-created_at')
        elif list_type == '2':
            # files = Files.objects.filter(project_id=id, created_by=request.user, is_admin_approved=True, submitted_to_admin=True).all().values('id','file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason')
            if name == None:
                files = Files.objects.filter(project_id=id, created_by=request.user,is_admin_approved=True, submitted_to_admin=True, is_marked_deleted=False).all().values('id','file_name','thumbnail','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason').order_by('-created_at')

            else:
                files = Files.objects.filter(Q(location__icontains=name) |
                                        Q(manufacturer_name__name__icontains=name) |
                                        Q(manufacturing_number__icontains=name),
                                        project_id=id, created_by=request.user,is_admin_approved=True, submitted_to_admin=True, is_marked_deleted=False).all().values('id','file_name','thumbnail','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason').order_by('-created_at')

        else:
            return CustomResponse({"message": "Invalid filter type"}, status=status_code.HTTP_400_BAD_REQUEST)
        
        # file_obj = Files.objects.filter(Q(location__icontains=name) |
        #                                 Q(manufacturer_name__full_name__icontains=name) |
        #                                 Q(manufacturing_number__icontains=name),
        #                                 project_id=id, is_admin_approved=True, is_marked_deleted=False, is_deleted=False).order_by('-created_at')

        # if name:
        #     files = files.filter(files_name__icontains=name)

        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(files) 

        # return CustomResponse(files)

        
class ProjectDetailsViewSet(viewsets.ModelViewSet):
    """
        ProjectDetailsViewSet to view to project details
    """
    serializer_class = ProjectDetailsViewSerializer
    pagination_class = CustomPagination
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        location = self.request.GET.get('location', None)
        queryset = Project.objects.filter(id=pk)
        manufacturer_name = self.request.GET.get('manufacturer_name', None)
        manufacturing_number = self.request.GET.get('manufacturing_number', None)

        return queryset

    def list(self, request, *args, **kwargs):
        """
            function to search and list the files of a particular project
        """
        page_size = self.request.GET.get('page_size', '')
        queryset = self.get_queryset()
        pk = self.kwargs.get('pk')
        location = self.request.GET.get('location', '')
        # Filtering for Files based on the search criteria
        file_obj = Files.objects.filter(Q(location__icontains=location) |
                                        Q(manufacturer_name__name__icontains=location) |
                                        Q(manufacturing_number__icontains=location),
                                        project_id=pk, is_admin_approved=True, is_marked_deleted=False, is_deleted=False).order_by('-created_at')

        # Apply pagination        
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(file_obj, request)
            if page is not None:
                serializer = FilesSerializer(instance=page, many=True)
                return CustomResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = FilesSerializer(instance=file_obj, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
   

class EditFileViewSet(viewsets.ModelViewSet):
    """
        EditFileViewSet to edit the file on Left Swipe and delete on right swipe
    """    
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)  

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return Files.objects.filter(id=pk)

    def update(self, request, id):
        """
            function to update file
        """
        data = request.data
        thumbnail = data.get("thumbnail")
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        manufacturer_name = data.get("manufacturer_name")
        manufacturing_number = data.get("manufacturing_number")
        location = data.get("location")
        quantity = data.get("quantity")
        project_details = data.get("project_details")
        additional_details = data.get("additional_details")
        location_points = data.get('location_points')

        if Files.objects.filter(manufacturing_number=manufacturing_number).exclude(id=id).exists():
            return CustomResponse({"message": "This manufacturing number already exists"}, status=status_code.HTTP_400_BAD_REQUEST)
        if manual_manufacturer_name:
            new_user = User.objects.create(full_name=manual_manufacturer_name)
            file = Files.objects.filter(id=id).update(manufacturer_name_id=new_user.id,thumbnail=thumbnail, manual_manufacturer_name=manual_manufacturer_name, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location, location_points=location_points,is_edited=True)
            return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.filter(id=id).update(thumbnail=thumbnail, manufacturing_number=manufacturing_number, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_edited=True)
            return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)
        
    def update_file(self, request, id):
        """
            function to update file
        """
        data = request.data
        thumbnail = data.get("thumbnail")
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        manufacturer_name = data.get("manufacturer_name")
        manufacturing_number = data.get("manufacturing_number")
        location = data.get("location")
        quantity = data.get("quantity")
        project_details = data.get("project_details")
        additional_details = data.get("additional_details")
        location_points = data.get('location_points')

        if Files.objects.filter(manufacturing_number=manufacturing_number).exclude(id=id).exists():
            return CustomResponse({"message": "This manufacturing number already exists"}, status=status_code.HTTP_400_BAD_REQUEST)
        if manual_manufacturer_name:
            manufacturer = ManufacturerName.objects.create(users = request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
            file = Files.objects.filter(id=id).update(manufacturer_name_id=manufacturer.id,thumbnail=thumbnail, manual_manufacturer_name=manual_manufacturer_name, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location, location_points=location_points,is_edited=True)
            return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.filter(id=id).update(thumbnail=thumbnail, manufacturing_number=manufacturing_number, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_edited=True)
            return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)
        
    def destroy(self, request, id):
        """
            delete method to delete the file from the database.
        """
        user = Files.objects.filter(id = id, is_marked_deleted=False).first()
        if not user:
            return CustomResponse({"message": "File Not Found"}, status=status_code.HTTP_400_BAD_REQUEST)
        user.is_marked_deleted = True
        user.save()
        return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('FILE_DELETED'))}, status=status_code.HTTP_200_OK)


class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    """
        TermsAndConditionsViewSet to get terms and conditions
    """
    def list(self, request):
        """
            function to give terms and conditions
        """
        content = ContentManagement.objects.filter(content_type=1)
        serializer = ContentManagementSerializer(content, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)


#Settings

class ViewProfileViewSet(viewsets.ViewSet):
    """
    ViewProfileViewSet to get the user's details
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def list(self, request):
        """
            function to show profile of user
        """
        user = User.objects.filter(id = request.user.id).first()
        if not user:
            return CustomResponse({"message": "User Not Found"})
        serializer = ViewProfileSerializer(user)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
    

class CompanyNameViewSet(viewsets.ViewSet):
    """
        CompanyNameViewSet to get the Company Listing
    """
    #permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission,)

    def list(self, request):
        """
            function to give listing of company
        """
        companies = Company.objects.filter(is_active=True)
        serializer = CompanyNameSerializer(companies, many=True)

        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
    

class UserListingViewSet(viewsets.ViewSet):
    """
       UserListingViewSet for getting the list of users 
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission,)

    def list(self, request):
        """
            function to give list of users
        """
        name = request.GET.get('name', None)
        users = User.objects.filter(is_admin_approved=True, full_name__icontains=name).all()
        serializer = UserListingSerializer(users, many=True)

        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)


class UserEditProfileViewSet(viewsets.ViewSet):
    """
        UserEditProfileViewSet to Edit the Personal Details of User
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def update(self, request):
        """
            function to edit users profile
        """
        data = request.data
        full_name = data.get("full_name")
        email = data.get("email")
        profile_pic = data.get("profile_pic")
        company_name = data.get("company_name")
        update_data = {}

        user = User.objects.filter(id=request.user.id).first()
        old_email=user.email
        if full_name:
            update_data["full_name"] = full_name

        # Check if email already exists, but ignore the current user's email
        if email and User.objects.filter(email=email).exclude(id=request.user.id).exists():
            return CustomResponse({"message": "Email already exists."}, status=status_code.HTTP_400_BAD_REQUEST)    

        update_data = {"full_name": full_name}
        d = User.objects.filter(id=request.user.id).first()

        # Update email and its verification status if provided
        if email and email != d.email:
            update_data["email"] = email
            update_data["is_email_verified"] = False
            otp = generate_otp()
            OTP.objects.update_or_create(user_id=request.user.id, otp=otp, otp_type=1)
            try:
                send_edit_profile_verification_email(email, otp, old_email)
            except Exception as e:
                pass

        # Update profile picture if provided
        if profile_pic:
            update_data["profile_pic"] = profile_pic
        if company_name:
                User.objects.filter(id=request.user.id).update(company_name=company_name, is_edited=True)
                return CustomResponse({"message": "Company Updated, Request Sent to Admin for Approval"}, status=status_code.HTTP_200_OK)
         
        # Perform the update in a single query
        User.objects.filter(id=request.user.id).update(**update_data)
        if email and email != d.email:
            return CustomResponse({"message": "Email changed, otp sent successfully."}, status=status_code.HTTP_200_OK)
        
        return CustomResponse({"message": "Profile updated successfully"}, status=status_code.HTTP_200_OK)
    

class UserChangePasswordViewSet(viewsets.ViewSet):
    """
        UserChangePasswordViewSet to change the Password of User
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def create(self, request):
        """
            function to change users password
        """
        serializer = UserChangePasswordSerializer(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)  

        serializer.update_password(request.user)
        return CustomResponse({"message": "Password updated successfully."}, status=status_code.HTTP_200_OK)
    

class NotificationStatusViewSet(viewsets.ViewSet):
    """
        NotificationStatusViewSet to enable disabe Notifications
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def update(self, request):
        """
            function to enable disable notifications toggle
        """
        data = request.data
        type = data.get("type")
        if type == 1:
            user = User.objects.filter(id=request.user.id).update(is_notification_enabled=True)
            return CustomResponse({"message": "Notifications Enabled successfully."}, status=status_code.HTTP_200_OK)
        if type == 2:
            user = User.objects.filter(id=request.user.id).update(is_notification_enabled=False)
            return CustomResponse({"message": "Notifications Disabled successfully."}, status=status_code.HTTP_200_OK)
        else :
            return CustomResponse({"message": "Please Enter Valid Type Value."}, status=status_code.HTTP_400_BAD_REQUEST)


class GlobalSearchViewSet(viewsets.ViewSet):
    """
        GlobalSearchViewSet to give global search 
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)
    pagination_class = CustomPagination
    serializer_class = ProjectDetailsViewSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        search = self.request.GET.get('search', None)
        queryset = Project.objects.filter(id=pk)

        return queryset

    def search(self, request):
        """
            Method to list and search for the projects.
        """
        page_size = request.GET.get('page_size', '')
        queryset = self.get_queryset()
        search = self.request.GET.get('search', '')
        print("user====",request.user.id)
        file_obj = Files.objects.filter(Q(location__icontains=search) |
                                        Q(manufacturer_name__name__icontains=search) |
                                        Q(manufacturing_number__icontains=search)).filter(Q(project__created_by_id=request.user.id) | 
                                                                                        #   Q(manufacturer_name=request.user) | 
                                                                                          Q(project__users__id=request.user.id)).filter(
                                           is_admin_approved=True, is_marked_deleted=False).order_by("-created_at")
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(file_obj, request)
            if page is not None:
                serializer = FilesSerializer(instance=page, many=True)
                return CustomResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = FilesSerializer(instance=file_obj, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)


#Log out
class LogoutUserViewSet(viewsets.ViewSet):
    """
        LogoutUserViewSet to Logout the User
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def post(self, request):
        """
            function to logout the user
        """
        request.auth.delete()
        return Response({"message": "Logged out successfully"}, status=status_code.HTTP_200_OK)


#Delete Account
class DeleteUserViewSet(viewsets.GenericViewSet):
    """
        DeleteUserViewSet to delete a user's account
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def update(self, request):
        """
            function to deactivate user
        """
        user = User.objects.filter(id=request.user.id).first()
        if not user:
            return CustomResponse({"message": "User not found."}, status=status_code.HTTP_404_NOT_FOUND)
        user.email = None
        user.is_deleted = True
        user.save()
            
        return CustomResponse({"message": "Your account has been deactivated successfully."}, status=status_code.HTTP_200_OK)


#About the App

class AboutAppViewset(viewsets.GenericViewSet):
    """
        AboutAppViewset to show about the app
    """
    permission_classes = (IsAuthenticated,)

    def list(self, request):
        """
            function to show about the app
        """
        type = request.GET.get('type')
        user=ContentManagement.objects.filter(content_type=type).all().values("content")
        return CustomResponse(user, status=status_code.HTTP_200_OK)
        

#FCM
    
class UpdateDeviceDetailViewSet(viewsets.ViewSet):
    """
        AddDeviceDetailViewSet used to update the user devices details.
    """
    #authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    action_serializer = {
        'retrieve': UserDeviceDetailSerializer,
        'perform_update': UserDeviceSerializer
    }

    def retrieve(self, request):
        """
            retrieve method used to get the device details.
        :param request:
        :return:
        """
        fcm_user = FCMDevice.objects.select_related(
            'user').filter(user=request.user, active=True)
        serializer = self.action_serializer.get(
            self.action)(fcm_user, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)

    def perform_update(self, request):
        """
            update method used to update the device details.
        :param request:
        :return:
        """
        serializer = self.action_serializer.get(self.action)(
            data=request.data, instance=request.user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return CustomResponse({"message": "Device Registered Successfully"}, status=status_code.HTTP_200_OK)

    def perform_destroy(self, request):
        """
        method used to delete the current user device token
        :param request:
        :return:
        """
        device_type = request.GET.get('device_type')
        registration_id = request.GET.get('registration_id')
        if device_type == 'both':
            FCMDevice.objects.filter(user=request.user).update(active=False)
        elif device_type:
            FCMDevice.objects.filter(
            user=request.user,registration_id=registration_id, type=device_type).update(active=False)
        return CustomResponse({"message": "Device Deleted Successfully"}, status=status_code.HTTP_200_OK)
        

class SendNotiticationViewSet(viewsets.ViewSet):
    """
        SendNotiticationViewSet to send notifications to users
    """
    def update(self, request):
        """
            function to send notifications
        """
        title = request.data.get("title")
        message = request.data.get("message")
        data = {
            "title": title,
            "message": message,
        }
        notification = UserNotification.objects.create(user_id=request.user.id,title=title,message=message)
        notification.save()
        data.update({"notification_id": str(notification.id)})
        res = send_notification_bulk([request.user.id], title, message, data) #to be sent to 356
        return CustomResponse({"message": "Notification Sent Successfully"}, status=status_code.HTTP_200_OK)
    

class NotificationViewSet(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        View to get list of Notifications
    """
    permission_classes = (IsAuthenticated,)
    queryset = UserNotification.objects.all()
    serializer_detail_class = NotificationListSerializer
    pagination_class = CustomPagination

    def list(self, request):
        """
            method to get notification list
        """
        queryset = UserNotification.objects.filter(user=request.user).\
            order_by('-created_at')
        unread = queryset.update(is_read=True)
        unread_new = queryset.filter(is_read=False).count()
        is_all_read = True #if unread == 0 else False
        serializer = self.serializer_detail_class(queryset, many=True)
        data = serializer.data
        if self.request.GET.get('page_size'):
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(queryset, request)
            serializer = self.serializer_detail_class(page, many=True)
            data = pagination_class.get_paginated_response(
                serializer.data).data
        updated_data = {"unread_notification": unread_new,
                        "notification_data": data, "is_all_read": is_all_read}
        return CustomResponse(updated_data)
    
    def notification_count(self, request):
        """
            function to get count of notifiations
        """
        queryset = UserNotification.objects.filter(user=request.user).\
            order_by('-created_at')
        unread_new = queryset.filter(is_read=False).count()
        print("unread", unread_new)
        return CustomResponse(unread_new)
    
    def retrieve(self, request, *args, **kwargs):
        """
            method to get the notification details
        """
        notification_id = kwargs.get('notification_id')
        # check again here
        queryset = UserNotification.objects.filter(id=notification_id, is_active=True).values(
            'id', 'notification_type', 'receiver', 'notification', 'is_read', 'created_at')
        if not queryset:
            return Response({"message": "NOTIFICATION_NOT_FOUND"},
                                             error_location="LOCATION",
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_detail_class(queryset, many=False)
        serializer_data = {
            'UserNotification': serializer.data
        }
        return CustomResponse(serializer_data)
    

class ClearAllNotificationViewset(viewsets.ViewSet):
    """
        View to clear all the notifications 
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationListSerializer

    def update(self, request):
        """
            method to clear notifications
        """
        UserNotification.objects.filter(user=request.user).delete()
        return CustomResponse({"message":"All Notifications Cleared"}, status=status_code.HTTP_200_OK)
    

from django.shortcuts import render
from rest_framework import views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as status_code
import boto3
import uuid
import os
from PIL import Image
from io import BytesIO
import io 
from pydub import AudioSegment
from core.common_utils import check_file_size
from config.local import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME
from botocore.exceptions import NoCredentialsError
from urllib.parse import urlparse


class createfile(viewsets.ViewSet):
    
    def generate_signed_url(self, object_key):
        try:
            # Create an S3 client
            s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
            
            # Generate a pre-signed URL
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
                ExpiresIn=3600000  # URL will expire in 1 hour (3600 seconds) - adjust as needed
            )

            return url
        except NoCredentialsError:
            return None

    def post(self, request):
        """
        POST method used to upload files into an S3 bucket.
        :param request:
        :return: response
        """
        images = []
        result = []
        if not request.data.get("file"):
            return CustomResponse({"message": "No file data found"}, status=status_code.HTTP_400_BAD_REQUEST)
        result = request.data.getlist("file")
        for upload in result:
            s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
            # Extract and convert the file extension to lowercase
            file_extension = os.path.splitext(upload.name)[1].lower()
            file_full_name = upload.name
            updated_filename = file_full_name.replace(' ', '_')
            if file_extension in [".jpg", ".jpeg", ".png"]:
                path_key = "image/{}_{}".format(uuid.uuid4(), updated_filename)
                # Compress the image
                compressed_image = self.compress_image(upload)
                if not compressed_image:
                    return CustomResponse({"message": "Failed to compress image"}, status=status_code.HTTP_400_BAD_REQUEST)
                upload = compressed_image
            elif file_extension in [".mp3"]:
                path_key = "audio/{}_{}".format(uuid.uuid4(), updated_filename)
                # Compress the audio (if needed)
                compressed_audio = self.compress_audio(upload)
                if not compressed_audio:
                    return CustomResponse({"message": "Failed to compress audio"}, status=status_code.HTTP_400_BAD_REQUEST)
                upload = compressed_audio
            else:
                return CustomResponse({"message": "Please provide a valid file."},
                                    status=status_code.HTTP_400_BAD_REQUEST)

            try:
                s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(upload, path_key)
            except Exception:
                return CustomResponse({"message": "Something went wrong during file uploading."},
                                    status=status_code.HTTP_400_BAD_REQUEST)

            created_url = 'https://' + AWS_STORAGE_BUCKET_NAME + '.s3.amazonaws.com/' + path_key

            # Generate a pre-signed URL for the uploaded file
            print("path_key===", path_key)
            pre_signed_url = self.generate_signed_url(path_key)

            # Include the pre-signed URL in the response
            data = {'name': path_key, 'url': pre_signed_url}
            images.append(data)
        return CustomResponse(images)

    def compress_image(self, image):
        """
           compress_image method to compress the images 
        """
        try:
            print("Compressing image...")
            img = Image.open(image)
            print("Compressing image 2...")
            img.thumbnail((800, 800))
            print("Compressing image 3...")
            output_buffer = BytesIO()
            print("Compressing image 4...")
            img.save(output_buffer, format="png")
            output_buffer.seek(0)
            print("Compressed image...")
            return output_buffer
        except Exception:
            return None

    def compress_audio(self, audio):
        """
            compress_audio method to compress the audio
        """
        try:
            sound = AudioSegment.from_file(audio)
            compressed_audio = sound.set_frame_rate(22050)
            output_buffer = BytesIO()
            compressed_audio.export(output_buffer, format="mp3")
            return output_buffer
        except Exception:
            return None
        
    def create_file(self, request, *args, **kwargs):
        """
            function to create file
        """
        data = request.data
        manufacturer_name = data.get('manufacturer_name')
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        project_id = data.get('project_id')
        thumbnail = data.get('thumbnail')
        manufacturing_number = data.get('manufacturing_number')
        quantity = data.get('quantity')
        project_details = data.get('project_details')
        additional_details = data.get('additional_details')
        recording = data.get('recording')
        location = data.get('location')
        location_points = data.get('location_points')
        if manual_manufacturer_name:
            new_manufacturer = ManufacturerName.objects.create(users = request.user,name=manual_manufacturer_name, added_by=2, is_read=False)
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with new Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with existing Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)
        


# class CreateFileWithImage(viewsets.ViewSet):
#     """
#         CreateFileWithImage viewset to upload image and create file
#     """

#     permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

#     def generate_signed_url(self, object_key):
#         """
#             function to generate signed url
#         """
#         try:
#             # Create an S3 client
#             s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
            
#             # Generate a pre-signed URL
#             url = s3.generate_presigned_url(
#                 ClientMethod='get_object',
#                 Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
#                 ExpiresIn=3600000  # URL will expire in 1 hour (3600 seconds) - adjust as needed
#             )

#             return url
#         except NoCredentialsError:
#             return None

#     def compress_image(self, image):
#         """
#            compress_image method to compress the images 
#         """
#         try:
#             print("Compressing image...")
#             img = Image.open(image)
#             print("Compressing image 2...")
#             img.thumbnail((800, 800))
#             print("Compressing image 3...")
#             output_buffer = BytesIO()
#             print("Compressing image 4...")
#             img.save(output_buffer, format="png")
#             output_buffer.seek(0)
#             print("image compressed...")
#             return output_buffer
#         except Exception:
#             return None
 
#     def create_and_upload_file(self, request):
#         """
#             function to upload image and create file
#         """
#         upload = request.data.get('file')
#         # if not upload:
#         #     return CustomResponse({"message": "No file data found"}, status=status_code.HTTP_400_BAD_REQUEST)
#         if upload:
 
#             compressed_image = self.compress_image(upload)
    
#             path_key = "image/{}_{}".format(uuid.uuid4(), upload.name.replace(' ', '_'))
#             s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
#             s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)
#             print("generating signed url...")
#             thumbnail_url = self.generate_signed_url(path_key)
#             print("signed url generated...")

#         else:
#             thumbnail_url = None
 
#         manufacturer_name = request.data.get('manufacturer_name')
#         manual_manufacturer_name = request.data.get('manual_manufacturer_name')
#         project_id = request.data.get('project_id')
#         manufacturing_number = request.data.get('manufacturing_number')
#         quantity = request.data.get('quantity')
#         project_details = request.data.get('project_details')
#         additional_details = request.data.get('additional_details')
#         recording = request.data.get('recording')
#         location = request.data.get('location')
#         location_points = request.data.get('location_points')

#         print("creating file...")

#         if manual_manufacturer_name:
#             new_manufacturer = ManufacturerName.objects.create(users = request.user,name=manual_manufacturer_name, added_by=2, is_read=False)
#             file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
#             c = str(project_id)+'_'+str(file.id)+'_'+'filename'
#             b = Files.objects.filter(id=file.id).update(file_name=c)
#             return CustomResponse({"message": "File Created with new Manufacturer Successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}, status=status_code.HTTP_200_OK)


#         file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
#         c = str(project_id)+'_'+str(file.id)+'_'+'filename'
#         b = Files.objects.filter(id=file.id).update(file_name=c)
#         return CustomResponse({"message": "File created successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}, status=status_code.HTTP_200_OK)


class CreateFileWithImage(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def generate_signed_url(self, object_key):
        try:
            s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
                ExpiresIn=3600000  # URL will expire in 1 hour (3600 seconds) - adjust as needed
            )
            return url
        except NoCredentialsError:
            return None

    def compress_image(self, image):
        try:
            print("compressing image")
            img = Image.open(image)
            img.thumbnail((800, 800))
            output_buffer = BytesIO()
            img.save(output_buffer, format="png")
            output_buffer.seek(0)
            print("image compressed")
            return output_buffer
        except Exception:
            return None

    def create_and_upload_file(self, request, file_data):
        print("in upload function")
        print("file data", file_data)
        upload = file_data.get('file')
        print("got file")
        if upload:
            compressed_image = self.compress_image(upload)
            path_key = "image/{}_{}".format(uuid.uuid4(), upload.name.replace(' ', '_'))
            s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
            s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)
            thumbnail_url = self.generate_signed_url(path_key)
        else:
            thumbnail_url = None

        # Extract other necessary fields from file_data
        manufacturer_name = file_data.get('manufacturer_name')
        manual_manufacturer_name = file_data.get('manual_manufacturer_name')
        project_id = file_data.get('project_id')
        manufacturing_number = file_data.get('manufacturing_number')
        quantity = file_data.get('quantity')
        project_details = file_data.get('project_details')
        additional_details = file_data.get('additional_details')
        recording = file_data.get('recording')
        location = file_data.get('location')
        location_points = file_data.get('location_points')

        print("creating file")

        if manual_manufacturer_name:
            new_manufacturer = ManufacturerName.objects.create(users=request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return {"message": "File Created with new Manufacturer Successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

        file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
        c = str(project_id)+'_'+str(file.id)+'_'+'filename'
        b = Files.objects.filter(id=file.id).update(file_name=c)
        return {"message": "File created successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

    def create(self, request, *args, **kwargs):
        try:
            files_data = request.data.getlist('file')
            response_data = []
            print("Received files_data:", files_data)

            for file_data in files_data:
                print("Processing file_data:", file_data)
                print("calling upload function")
                result = self.create_and_upload_file(request, file_data)
                print("upload function called")
                print("response data",response_data)
                response_data.append(result)
                print("result", result)

            return CustomResponse({"message": "Files uploaded successfully", "data": response_data}, status=status_code.HTTP_200_OK)

        except Exception as e:
            return CustomResponse({"error": str(e)}, status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)
 

# class CreateFileWithImage2(viewsets.ViewSet):
#     permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

#     def generate_signed_url(self, object_key):
#         try:
#             s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
#             url = s3.generate_presigned_url(
#                 ClientMethod='get_object',
#                 Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
#                 ExpiresIn=3600000  # URL will expire in 1 hour (3600 seconds) - adjust as needed
#             )
#             return url
#         except NoCredentialsError:
#             return None

#     def compress_image(self, image):
#         try:
#             print("Compressing image...")
#             img = Image.open(image)
#             img.thumbnail((800, 800))
#             print("Compressing image 2...")
#             output_buffer = BytesIO()
#             print("Compressing image 3...")
#             img.save(output_buffer, format="png")
#             output_buffer.seek(0)
#             print("Image compressed...")
#             return output_buffer
#         except Exception:
#             return None

#     def create_and_upload_file(self, request, file_data):
#         print("In upload function")
#         print("File data", file_data)

#         # Extract data from file_data
#         temp_file_id = file_data.get('temp_file_id')
#         project_id = file_data.get(f'project_id_{temp_file_id}')
#         thumbnail = file_data.get(f'thumbnail_{temp_file_id}')
#         manufacturing_number = file_data.get(f'manufacturing_number_{temp_file_id}')
#         manufacturer_name_id = file_data.get(f'manufacturer_name_{temp_file_id}')
#         manual_manufacturer_name = file_data.get(f'manual_manufacturer_name_{temp_file_id}')
#         quantity = file_data.get(f'quantity_{temp_file_id}')
#         project_details = file_data.get(f'project_details_{temp_file_id}')
#         additional_details = file_data.get(f'additional_details_{temp_file_id}')
#         recording = file_data.get(f'recording_{temp_file_id}')
#         location = file_data.get(f'location_{temp_file_id}')
#         location_points = file_data.get(f'location_points_{temp_file_id}')

#         # Compress image
#         compressed_image = self.compress_image(thumbnail)

#         # Upload compressed image to S3
#         path_key = f"image/{uuid.uuid4()}_{thumbnail.replace(' ', '_')}"
#         s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
#         s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)
#         thumbnail_url = self.generate_signed_url(path_key)

#         print("Creating file...")
#         # Create new manufacturer if manual manufacturer name is provided
#         if manual_manufacturer_name:
#             new_manufacturer = ManufacturerName.objects.create(users=request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
#             file = Files.objects.create(
#                 created_by=request.user,
#                 manufacturer_name_id=new_manufacturer.id,
#                 manual_manufacturer_name=manual_manufacturer_name,
#                 project_id=project_id,
#                 thumbnail=thumbnail_url,
#                 manufacturing_number=manufacturing_number,
#                 quantity=quantity,
#                 project_details=project_details,
#                 additional_details=additional_details,
#                 recording=recording,
#                 location=location,
#                 location_points=location_points,
#                 is_admin_approved=True,
#                 submitted_to_admin=False
#             )
#             file_name = f"{project_id}_{file.id}_filename"
#             Files.objects.filter(id=file.id).update(file_name=file_name)
#             return {"message": "File Created with new Manufacturer Successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

#         # Use existing manufacturer
#         file = Files.objects.create(
#             created_by=request.user,
#             manufacturer_name_id=manufacturer_name_id,
#             manual_manufacturer_name=manual_manufacturer_name,
#             project_id=project_id,
#             thumbnail=thumbnail_url,
#             manufacturing_number=manufacturing_number,
#             quantity=quantity,
#             project_details=project_details,
#             additional_details=additional_details,
#             recording=recording,
#             location=location,
#             location_points=location_points,
#             is_admin_approved=True,
#             submitted_to_admin=False
#         )
#         file_name = f"{project_id}_{file.id}_filename"
#         Files.objects.filter(id=file.id).update(file_name=file_name)
#         return {"message": "File created successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

#     def create(self, request, *args, **kwargs):
#         try:
#             files_data = request.data
#             response_data = []
#             print("Received files_data:", files_data)

#             for temp_file_id in range(1, len(files_data['temp_file_ids']) + 1):
#                 print(f"Processing temp_file_id {temp_file_id}")
#                 file_data = {key: files_data[f"{key}_{temp_file_id}"] for key in files_data.keys() if f"{key}_{temp_file_id}" in files_data}
#                 print("Calling upload function")
#                 result = self.create_and_upload_file(request, file_data)
#                 print("Upload function called")
#                 print("Result", result)
#                 response_data.append(result)

#             return CustomResponse({"message": "Files uploaded successfully", "data": response_data}, status=status_code.HTTP_200_OK)

#         except Exception as e:
#             return CustomResponse({"error": str(e)}, status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)


# class CreateFileWithImage2(viewsets.ViewSet):
#     permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

#     def generate_signed_url(self, object_key):
#         try:
#             s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
#             url = s3.generate_presigned_url(
#                 ClientMethod='put_object',
#                 Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
#                 ExpiresIn=3600  # URL will expire in 1 hour (adjust as needed)
#             )
#             return url
#         except NoCredentialsError:
#             return None
        
#     def compress_image(self, image):
#         try:
#             print("Compressing image...")
#             img = Image.open(image)
#             img.thumbnail((800, 800))
#             print("Compressing image 2...")
#             output_buffer = BytesIO()
#             print("Compressing image 3...")
#             img.save(output_buffer, format="png")
#             output_buffer.seek(0)
#             print("Image compressed...")
#             return output_buffer
#         except Exception:
#             return None

#     def create_and_upload_file(self, request, file_data):
#         print("in upload function")
#         print("file data", file_data)
#         # upload = file_data.get('file')
#         # temp_file_id = file_data.get('temp_file_id')
#         upload = file_data['file']
#         temp_file_id = file_data['temp_file_id']

#         if upload:
#             print("in if upload")
#             compressed_image = self.compress_image(upload)
#             path_key = "image/{}_{}".format(uuid.uuid4(), upload.name.replace(' ', '_'))

#             # Upload compressed image to S3
#             s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
#             s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)

#             # Generate signed URL for the uploaded image
#             thumbnail_url = self.generate_signed_url(path_key)
#         else:
#             print("in else upload")
#             thumbnail_url = None

#         # Extract other necessary fields from file_data
#         manufacturer_name = file_data.get(f'manufacturer_name_{temp_file_id}')
#         manual_manufacturer_name = file_data.get(f'manual_manufacturer_name_{temp_file_id}')
#         project_id = file_data.get(f'project_id_{temp_file_id}')
#         manufacturing_number = file_data.get(f'manufacturing_number_{temp_file_id}')
#         quantity = file_data.get(f'quantity_{temp_file_id}')
#         project_details = file_data.get(f'project_details_{temp_file_id}')
#         additional_details = file_data.get(f'additional_details_{temp_file_id}')
#         recording = file_data.get(f'recording_{temp_file_id}')
#         location = file_data.get(f'location_{temp_file_id}')
#         location_points = file_data.get(f'location_points_{temp_file_id}')

#         print("creating file")

#         if manual_manufacturer_name:
#             new_manufacturer = ManufacturerName.objects.create(users=request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
#             file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
#             c = f"{project_id}_{file.id}_filename"
#             b = Files.objects.filter(id=file.id).update(file_name=c)
#             return {"message": "File Created with new Manufacturer Successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

#         file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
#         c = f"{project_id}_{file.id}_filename"
#         b = Files.objects.filter(id=file.id).update(file_name=c)
#         return {"message": "File created successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

#     def create(self, request, *args, **kwargs):
#         try:
#             files_data = request.data.getlist('file')
#             response_data = []
#             print("Received files_data:", files_data)

#             # Assuming 'file_data' is a dictionary with keys like 'project_id_1', 'project_id_2', etc.
#             for key, file_data in files_data.items():
#                 if key.startswith('project_id_'):
#                     print("Processing file_data:", file_data)
#                     print("calling upload function")
#                     result = self.create_and_upload_file(request, file_data)
#                     print("upload function called")
#                     print("response data", response_data)
#                     response_data.append(result)
#                     print("result", result)

#             return CustomResponse({"message": "Files uploaded successfully", "data": response_data}, status=status_code.HTTP_200_OK)

#         except Exception as e:
#            return CustomResponse({"error": str(e)}, status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)


# class CreateFileWithImage2(viewsets.ViewSet):
#     permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

#     def generate_signed_url(self, object_key):
#         try:
#             s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
#             url = s3.generate_presigned_url(
#                 ClientMethod='put_object',
#                 Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
#                 ExpiresIn=3600  # URL will expire in 1 hour (adjust as needed)
#             )
#             return url
#         except NoCredentialsError:
#             return None
        
#     def compress_image(self, image):
#         try:
#             print("Compressing image...")
#             img = Image.open(image)
#             img.thumbnail((800, 800))
#             print("Compressing image 2...")
#             output_buffer = BytesIO()
#             print("Compressing image 3...")
#             img.save(output_buffer, format="png")
#             output_buffer.seek(0)
#             print("Image compressed...")
#             return output_buffer
#         except Exception:
#             return None

#     def create_and_upload_file(self, request, file_data):
#         print("in upload function")
#         print("file data==", file_data)

#         upload = file_data.get('file')
#         print("upload ====", upload)
#         temp_file_id = file_data.get('temp_file_id')

#         if upload:
#             print("in if upload")
#             compressed_image = self.compress_image(upload)
#             path_key = "image/{}_{}".format(uuid.uuid4(), upload.name.replace(' ', '_'))

#             # Upload compressed image to S3
#             s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
#             s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)

#             # Generate signed URL for the uploaded image
#             thumbnail_url = self.generate_signed_url(path_key)
#         else:
#             print("in else upload")
#             thumbnail_url = None

#         # Extract other necessary fields from file_data
#         manufacturer_name = file_data.get(f'manufacturer_name_{temp_file_id}')
#         manual_manufacturer_name = file_data.get(f'manual_manufacturer_name_{temp_file_id}')
#         project_id = file_data.get(f'project_id_{temp_file_id}')
#         manufacturing_number = file_data.get(f'manufacturing_number_{temp_file_id}')
#         quantity = file_data.get(f'quantity_{temp_file_id}')
#         project_details = file_data.get(f'project_details_{temp_file_id}')
#         additional_details = file_data.get(f'additional_details_{temp_file_id}')
#         recording = file_data.get(f'recording_{temp_file_id}')
#         location = file_data.get(f'location_{temp_file_id}')
#         location_points = file_data.get(f'location_points_{temp_file_id}')

#         print("creating file")

#         if manual_manufacturer_name:
#             new_manufacturer = ManufacturerName.objects.create(users=request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
#             file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
#             c = f"{project_id}_{file.id}_filename"
#             b = Files.objects.filter(id=file.id).update(file_name=c)
#             return {"message": "File Created with new Manufacturer Successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

#         file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
#         c = f"{project_id}_{file.id}_filename"
#         b = Files.objects.filter(id=file.id).update(file_name=c)
#         return {"message": "File created successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

#     def create(self, request, *args, **kwargs):
#         try:
#             files_data = request.data.getlist('file')
#             response_data = []
#             print("Received files_data:", files_data)

#             # Assuming 'file_data' is a dictionary with keys like 'project_id_1', 'project_id_2', etc.
#             for file_data in files_data:
#                 print("Processing file_data:", file_data)
#                 print("calling upload function")
#                 result = self.create_and_upload_file(request, file_data)
#                 print("upload function called")
#                 print("response data", response_data)
#                 response_data.append(result)
#                 print("result", result)

#             return CustomResponse({"message": "Files uploaded successfully", "data": response_data}, status=status_code.HTTP_200_OK)

#         except Exception as e:
#            return CustomResponse({"error": str(e)}, status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateFileWithImage2(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def generate_signed_url(self, object_key):
        try:
            s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
            url = s3.generate_presigned_url(
                ClientMethod='put_object',
                Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
                ExpiresIn=3600  # URL will expire in 1 hour (adjust as needed)
            )
            return url
        except NoCredentialsError:
            return None
        
    def compress_image(self, image):
        try:
            print("Compressing image...")
            img = Image.open(image)
            img.thumbnail((800, 800))
            print("Compressing image 2...")
            output_buffer = BytesIO()
            print("Compressing image 3...")
            img.save(output_buffer, format="png")
            output_buffer.seek(0)
            print("Image compressed...")
            return output_buffer
        except Exception:
            return None

    def create_and_upload_file(self, request, file_data):
        print("in upload function")
        print("file data==", file_data)

        # upload = file_data['file']
        upload = file_data.file
        temp_file_id = request.data.get('temp_file_id')

        # temp_file_id = file_data.temp_file_id
        print("upload ====", upload)
        # temp_file_id = file_data['temp_file_id']

        if upload:
            print("in if upload")
            compressed_image = self.compress_image(upload)
            print("compressed", compressed_image)
            # print("upload name", upload.name)
            # original_file_name = upload.name
            # print("originsl", original_file_name)
            original_file_name = f"your_custom_prefix_{uuid.uuid4().hex}.png"
            print("original", original_file_name)
            # path_key = "image/{}_{}".format(uuid.uuid4(), upload.name.replace(' ', '_'))
            path_key = "image/{}_{}".format(uuid.uuid4(), original_file_name.replace(' ', '_'))
            print("path key", path_key)

            # Upload compressed image to S3
            s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
            print("s3", s3)
            s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)

            # Generate signed URL for the uploaded image
            thumbnail_url = self.generate_signed_url(path_key)
            print("thumbnail", thumbnail_url)
        else:
            print("in else upload")
            thumbnail_url = None

        print("taking input")
        print("temp file id", temp_file_id)
        # Extract other necessary fields from file_data
        manufacturer_name = request.data.get(f'manufacturer_name_{temp_file_id}')     
        manual_manufacturer_name = request.data.get(f'manual_manufacturer_name_{temp_file_id}')     
        project_id = request.data.get(f'project_id_{temp_file_id}')     
        manufacturing_number = request.data.get(f'manufacturing_number_{temp_file_id}')     
        quantity = request.data.get(f'quantity_{temp_file_id}')     
        project_details = request.data.get(f'project_details_{temp_file_id}')     
        additional_details = request.data.get(f'additional_details_{temp_file_id}')     
        recording = request.data.get(f'recording_{temp_file_id}')     
        location = request.data.get(f'location_{temp_file_id}')     
        location_points = request.data.get(f'location_points_{temp_file_id}')


        print("creating file")

        if manual_manufacturer_name:
            new_manufacturer = ManufacturerName.objects.create(users=request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = f"{project_id}_{file.id}_filename"
            e = ManufacturerName.objects.filter(id=new_manufacturer.id).first()
            print("eee",e.name)
            b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
            # b = Files.objects.filter(id=file.id).update(file_name=c)
            return {"message": "File Created with new Manufacturer Successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

        file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
        c = f"{project_id}_{file.id}_filename"
        e = ManufacturerName.objects.filter(id=manufacturer_name).first()
        print("eee",e.name)
        b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
        # b = Files.objects.filter(id=file.id).update(file_name=c)
        return {"message": "File created successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

    def create(self, request, *args, **kwargs):
        try:
            files_data = request.data.getlist('file')
            response_data = []
            print("Received files_data:", files_data)

            for file_data in files_data:
                print("Processing file_data:", file_data)
                print("calling upload function")
                result = self.create_and_upload_file(request, file_data)
                print("upload function called")
                print("response data", response_data)
                response_data.append(result)
                print("result", result)

            return CustomResponse({"message": "Files uploaded successfully", "data": response_data}, status=status_code.HTTP_200_OK)

        except Exception as e:
            return CustomResponse({"error": str(e)}, status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)


