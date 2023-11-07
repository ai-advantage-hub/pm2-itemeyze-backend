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
    UserNotification

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

    def create(self, request, *args, **kwargs):
        """
            function to create project
        """
        project_name = request.data.get('project_name')
        user = request.user 
        if not project_name:
            return CustomResponse({"message": "Project name cannot be empty."}, status=status_code.HTTP_400_BAD_REQUEST)

        # Check if the project name is unique
        if Project.objects.filter(project_name=project_name).exists():
            return CustomResponse({"message": "Project with this name already exists."}, status=status_code.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=user)
        project = Project.objects.filter(id=serializer.instance.id).first()
        project.users.add(user)

        return CustomResponse(serializer.data, status=status_code.HTTP_201_CREATED)

    def search(self, request):
        """
            Method to list and search for the projects.
        """
        project_name = request.GET.get('project_name', None)
        page_size = request.GET.get('page_size', '')
        print("user====",request.user.id)
        projects = Project.objects.filter(
            users=request.user,
            is_admin_approved=True, is_marked_deleted=False
            ).values(
            'id', 'created_at', 'updated_at', 'project_name', 'project_description',
            'is_admin_approved', 'is_marked_deleted', 'project_number', 'created_by_id'
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
    
    
    
    
    # def list(self, request, id, *args, **kwargs):
    #     """
    #         function to give list of file
    #     """
    #     location = request.GET.get('location', None)
    #     manufacturer_name = request.GET.get('manufacturer_name', None)
    #     manufacturing_number = request.GET.get('manufacturing_number', None)
    #     user = Files.objects.filter(id=id).all().values('file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording')
    #     return CustomResponse(user)

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

    def user_saved_list(self, request, id):
        """
            function to give list of those files which are created by user and not submitted to admin
        """
        if not Project.objects.filter(id=id).exists():
            return CustomResponse({"message": "Project of this id does not exist"}, status=status_code.HTTP_400_BAD_REQUEST)
        files = Files.objects.filter(project_id = id, created_by=request.user, submitted_to_admin=False, is_marked_deleted=False).all().values('id','file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording', 'disapproved_reason')
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
        files = Files.objects.filter(project_id=id, created_by=request.user, is_admin_approved=True, submitted_to_admin=True).all().values('id','file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording', 'disapproved_reason')
        return CustomResponse(files)

        
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
                                        Q(manufacturer_name__full_name__icontains=location) |
                                        Q(manufacturing_number__icontains=location),
                                        project_id=pk, is_admin_approved=True, is_marked_deleted=False).order_by('-created_at')

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
            file = Files.objects.filter(id=id).update(manufacturer_name_id=new_user.id,thumbnail=thumbnail, manual_manufacturer_name=manual_manufacturer_name, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location, location_points=location_points,is_admin_approved=True)
            return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.filter(id=id).update(thumbnail=thumbnail, manufacturing_number=manufacturing_number, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_admin_approved=True)
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
                User.objects.filter(id=request.user.id).update(company_name=company_name, is_admin_approved=False)
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
                                        Q(manufacturer_name__full_name__icontains=search) |
                                        Q(manufacturing_number__icontains=search)).filter(Q(project__created_by_id=request.user.id) | Q(manufacturer_name=request.user) | Q(project__users__id=request.user.id)).filter(
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