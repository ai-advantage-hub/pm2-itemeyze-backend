from django.shortcuts import render
from rest_framework import mixins, viewsets, generics, filters
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
from core.common_utils import generate_otp, send_verification_email, send_notification_bulk
from core.response import CustomResponse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework import status as status_code
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from core.messages import SUCCESS_MESSAGES 
from django.utils.translation import gettext
from rest_framework.permissions import IsAuthenticated
from core.permissions import CheckUserRoleStatusPermission
from django.db.models import Q
from fcm_django.models import FCMDevice
from core.pagination import CustomPagination
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


#Onboarding

class SignUpViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """ 
        Signup view where user provides basic information and should be able to signup
    """
    serializer_class = SignupSerializer 

    def create(self, request, *args, **kwargs):
        """ Method for user signup"""
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
        data = request.data
        email = data.get("email")
        if not email:
            return CustomResponse({"message": "Please enter email"})
        user = User.objects.filter(email=email.lower()).first()
        otp = generate_otp()
        OTP.objects.update(user=user,otp=otp,otp_type=1)
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
    # def create(self, request):
    #     serializer = UserLoginSerializer(data=request.data)
    #     # serializer.is_valid(raise_exception=True)
    #     # serializer.save()
    #     # user = serializer.validated_data['user']
    #     # token, created = Token.objects.get_or_create(user=user)
    #     # return CustomResponse({"token": token.key}, status=status_code.HTTP_200_OK)
    #     if serializer.is_valid():
    #         user = serializer.validated_data['user']
    #         token, created = Token.objects.get_or_create(user=user)
    #         # return CustomResponse({"token": token.key}, status=status_code.HTTP_200_OK)
    #         response_data = {
    #             "token": token.key,
    #             "is_email_verified": user.is_email_verified  # Include is_email_verified in the response
    #         }
    #         return CustomResponse(response_data, status=status_code.HTTP_200_OK)
    #     else:
    #         return CustomResponse({"msg": "Please provide valid Credentials"}, status=status_code.HTTP_200_OK)

    def create(self, request):
        serializer = UserLoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            is_email_verified = user.is_email_verified

            response_data = {
                "is_email_verified": is_email_verified,
            }

            if is_email_verified:
                token, created = Token.objects.get_or_create(user=user)
                response_data["token"] = token.key
            else:
                #response_data["token"] = None
                response_data["msg"] = "User email is not verified. Please check your email inbox."

            return CustomResponse(response_data, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse({"msg": "Please provide valid Credentials"}, status=status_code.HTTP_200_OK)






        

class ForgotPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
        ForgotPasswordViewSet for forget password
    """
    serializer_class = ForgotPasswordSerializer
    #permission_classes = (IsAuthenticated,)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return CustomResponse({"message": "OTP Sent Successfully"}, status=status_code.HTTP_200_OK)
    

class ResetPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
       ResetPasswordViewSet will be used for reseting the password 
    """
    serializer_class = ResetPasswordSerializer
    #permission_classes = (IsAuthenticated,)

    def update(self, request):
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

        return CustomResponse(serializer.data, status=status_code.HTTP_201_CREATED)

    # def search(self, request):

    #     project_name = request.GET.get('project_name', None)
    #     page = request.GET.get('page', 1)  # Get the requested page number from the request
    #     per_page = request.GET.get('per_page', 10)  # Get the requested number of items per page    
    #     projects = Project.objects.filter(created_by=request.user, is_admin_approved=True)    
    #     if project_name:
    #         projects = projects.filter(project_name__icontains=project_name)    
    #     # Pagination
    #     paginator = Paginator(projects, per_page)   
    #     try:
    #         paginated_projects = paginator.page(page)
    #     except PageNotAnInteger:
    #         paginated_projects = paginator.page(1)
    #     except EmptyPage:
    #         #paginated_projects = paginator.page(paginator.num_pages)  
    #         return CustomResponse({"message": "There are no more Projects."}, status=status_code.HTTP_404_NOT_FOUND)  
    #     if not paginated_projects:
    #         return CustomResponse({"message": "No Data Found."}, status=status_code.HTTP_400_BAD_REQUEST)    
    #     # Return paginated results
    #     results = {
    #         "data": list(paginated_projects.object_list.values()),           
    #     }    
    #     return CustomResponse(results, status=status_code.HTTP_200_OK)
    
    def search(self, request):
        """
        Method to list and search for the projects.
        """
        project_name = request.GET.get('project_name', None)
        page_size = request.GET.get('page_size', '')
        print("user====",request.user.id)
        # projects = Project.objects.filter(created_by=request.user, is_admin_approved=False).values('id', 'created_at', 'updated_at', 'project_name', 'project_description', 'is_admin_approved', 'is_marked_deleted', 'project_number', 'created_by_id')
        projects = Project.objects.filter(
            Q(created_by=request.user) | Q(users=request.user),
            is_admin_approved=True
            ).values(
            'id', 'created_at', 'updated_at', 'project_name', 'project_description',
            'is_admin_approved', 'is_marked_deleted', 'project_number', 'created_by_id'
            )
        # if project_name:
        #     projects = projects.filter(name__icontains=project_name)
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
    #     request_data = request.data.copy()
    #     request_data["manufacturer_name"] = self.request.user.id
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     serializer.context["project_id"] = request_data["project_id"]
    #     self.perform_create(serializer)
    #     return CustomResponse(serializer.data, status=status_code.HTTP_201_CREATED)
    
    def create(self, request, *args, **kwargs):
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
            print("newwwwww", new_user.id)
            file = Files.objects.create(manufacturer_name_id=new_user.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points)
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            print("ccccccccc",c)
            b = Files.objects.filter(id=file.id).update(file_name=c)
            print("new filleeeee", file)
            return CustomResponse({"message": "File Created with new user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)
        else:
            file = Files.objects.create(manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, file_name='autogenerated_filename')
            c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            print("ccccccccc",c)
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with existing user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)

    # def create(self, request, *args, **kwargs):
    #     data = request.data
    #     serializer = CreateFileDetailsSerializer(data=data)

    #     if serializer.is_valid():
    #         manufacturer_name = serializer.validated_data.get('manufacturer_name')
    #         manual_manufacturer_name = serializer.validated_data.get('manual_manufacturer_name', '')
    #         project_id = serializer.validated_data.get('project_id')
    #         manufacturing_number = serializer.validated_data.get('manufacturing_number')
    #         quantity = serializer.validated_data.get('quantity')
    #         project_details = serializer.validated_data.get('project_details')
    #         additional_details = serializer.validated_data.get('additional_details')
    #         recording = serializer.validated_data.get('recording')
    #         location = serializer.validated_data.get('location')
    #         location_points = serializer.validated_data.get('location_points')

    #         if manual_manufacturer_name:
    #             new_user = User.objects.create(full_name=manual_manufacturer_name)
    #             print("newwwwww", new_user.id)
    #             file = Files.objects.create(manufacturer_name_id=new_user.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points)
    #             print("new filleeeee", file)
    #             return CustomResponse({"message": "File Created with a new user Successfully"}, status=status_code.HTTP_201_CREATED)
    #         else:
    #             Files.objects.create(manufacturer_name_id=manufacturer_name, project_id=project_id, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points)
    #             return CustomResponse({"message": "File Created with an existing user Successfully"}, status=status_code.HTTP_201_CREATED)
    #     else:
    #         return CustomResponse(serializer.errors, status=status_code.HTTP_400_BAD_REQUEST)

    def list(self, request, id, *args, **kwargs):
        location = request.GET.get('location', None)
        manufacturer_name = request.GET.get('manufacturer_name', None)
        manufacturing_number = request.GET.get('manufacturing_number', None)
        user = Files.objects.filter(id=id).all().values('file_name','thumbnail','manufacturer_name__full_name', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording')
        return CustomResponse(user)

        
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

    # def list(self, request, *args, **kwargs):

    #     queryset = self.get_queryset()
    #     pk = self.kwargs.get('pk')
    #     location = self.request.GET.get('location', '')
    #     # Filtering for Files based on the search criteria
    #     file_obj = Files.objects.filter(Q(location__icontains=location) |
    #                                     Q(manufacturer_name__full_name__icontains=location) |
    #                                     Q(manufacturing_number__icontains=location),
    #                                     project_id=pk)
    #     # file_obj = Files.objects.filter(Q(location__icontains=location) |
    #     #                                 Q(manufacturer_name__full_name__icontains=location) |
    #     #                                 Q(manufacturing_number__icontains=location),
    #     #                                 project_id=pk,
    #     #                                 is_admin_approved=True)  We will use this when we want to show only those files which are approved by admin
    #     # Apply pagination to the file_obj
    #     page = request.GET.get('page', 1)
    #     per_page = request.GET.get('per_page', 10)  # Use a default value for per_page, or adjust as needed    
    #     paginator = Paginator(file_obj, per_page)    
    #     try:
    #         paginated_files = paginator.page(page)
    #     except PageNotAnInteger:
    #         paginated_files = paginator.page(1)
    #     except EmptyPage:
    #         #paginated_files = paginator.page(paginator.num_pages)   
    #         return CustomResponse({"message": "There are no more Files."}, status=status_code.HTTP_404_NOT_FOUND) 
    #     # Serialize data
    #     file_serializer = FilesSerializer(paginated_files, many=True)
    #     project_serializer = self.get_serializer(queryset, many=True, context={"search": location})    
    #     data = {
    #         'project_details': project_serializer.data,
    #         'project_files': file_serializer.data,
    #         "total": paginator.count,
    #         "per_page": paginator.per_page,
    #         "current_page": int(page),
    #         "total_pages": paginator.num_pages,
    #     }    
    #     return CustomResponse(data, status=status_code.HTTP_200_OK)
    
    # def list(self, request, *args, **kwargs):
    #     queryset = self.get_queryset()
    #     pk = self.kwargs.get('pk')
    #     location = self.request.GET.get('location', '')

    #     # Filtering for Files based on the search criteria
    #     file_obj = Files.objects.filter(Q(location__icontains=location) |
    #                                     Q(manufacturer_name__full_name__icontains=location) |
    #                                     Q(manufacturing_number__icontains=location),
    #                                     project_id=pk)

    #     # Apply pagination
    #     page_size = self.request.GET.get('page_size', None)
    #     paginator = self.pagination_class()

    #     if page_size:
    #         paginated_files = paginator.paginate_queryset(file_obj, self.request)
    #         serializer = FilesSerializer(instance=paginated_files, many=True)
    #         return paginator.get_paginated_response(serializer.data)

    #     serializer = FilesSerializer(instance=file_obj, many=True)
    #     return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        page_size = self.request.GET.get('page_size', '')
        queryset = self.get_queryset()
        pk = self.kwargs.get('pk')
        location = self.request.GET.get('location', '')
        # Filtering for Files based on the search criteria
        file_obj = Files.objects.filter(Q(location__icontains=location) |
                                        Q(manufacturer_name__full_name__icontains=location) |
                                        Q(manufacturing_number__icontains=location),
                                        project_id=pk, is_admin_approved=True)

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
    
    # def update(self, request, pk=None):
    #     """
    #         update method to update the file details.
    #     """
    #     queryset = self.get_queryset()
    #     obj = queryset.get(pk=pk)
    #     serializer = CreateFileDetailsSerializer(obj, data=request.data)
    #     # serializer.is_valid(raise_exception=True)
    #     # serializer.save()
    #     # return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('FILE_UPDATED'))}, status=status_code.HTTP_200_OK)
    #     if serializer.is_valid():
    #         serializer.save()
    #         #return CustomResponse({'message': 'File details edited successfully.'})
    #         return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('FILE_UPDATED'))}, status=status_code.HTTP_200_OK)
    #     else:
    #         return CustomResponse(serializer.errors, status=status_code.HTTP_200_OK)

    def update(self, request, id):
        data = request.data
        thumbnail = data.get("thumbnail")
        file_name = data.get("file_name")
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
        # if Files.objects.filter(file_name=file_name).exclude(id=id).exists():
        #     return CustomResponse({"message": "This File Name already exists"}, status=status_code.HTTP_400_BAD_REQUEST)
        if manual_manufacturer_name:
            new_user = User.objects.create(full_name=manual_manufacturer_name)
            print("newwwwww", new_user.id)
            file = Files.objects.filter(id=id).update(manufacturer_name_id=new_user.id, manual_manufacturer_name=manual_manufacturer_name, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location,file_name=file_name, location_points=location_points,is_admin_approved=True)
            # c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            # print("ccccccccc",c)
            # b = Files.objects.filter(id=file.id).update(file_name=c)
            # print("new filleeeee", file)
            return CustomResponse({"message": "File updated with new User Successfully"}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.filter(id=id).update(file_name=file_name, thumbnail=thumbnail, manufacturing_number=manufacturing_number, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_admin_approved=True)
            return CustomResponse({"message": "File updated successfully"}, status=status_code.HTTP_200_OK)
        
    def destroy(self, request, pk):
        """
            delete method to delete the file from the database.
        """
        # queryset = self.get_queryset()
        # obj = queryset.get(pk=pk)
        # obj.delete()
        # #return CustomResponse({'message': 'File deleted successfully.'})
        # return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('FILE_DELETED'))}, status=status_code.HTTP_400_BAD_REQUEST)
        user = Files.objects.filter(id = pk, is_marked_deleted = False).first()
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
        user = User.objects.filter(id = request.user.id).first()
        if not user:
            return CustomResponse({"message": "User Not Found"})
        print("user-====", user.profile_pic)

        serializer = ViewProfileSerializer(user)
        
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
    

class CompanyNameViewSet(viewsets.ViewSet):
    """
        CompanyNameViewSet to get the Company Listing
    """
    #permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission,)

    def list(self, request):
        companies = Company.objects.filter(is_active=True)
        serializer = CompanyNameSerializer(companies, many=True)

        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
    

class UserListingViewSet(viewsets.ViewSet):
    """
       UserListingViewSet for getting the list of users 
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission,)

    def list(self, request):
        name = request.GET.get('name', None)
        users = User.objects.filter(is_admin_approved=True, full_name__icontains=name).all()
        serializer = UserListingSerializer(users, many=True)

        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)

            
# class UserEditProfileViewSet(viewsets.ViewSet):
#     """
#         UserEditProfileViewSet to Edit the Personal Details of User
#     """
#     permission_classes = (IsAuthenticated,)

#     def update(self, request):
#         data = request.data
#         email = data.get('email')
#         serializer = UserEditProfileSerializer(
#             instance=request.user, data=request.data, partial=True
#         )

#         serializer.is_valid(raise_exception=True)

#         serializer.save()
#         if email:
#             if email and User.objects.filter(email=email).exclude(id=request.user.id).exists():
#                 return CustomResponse({"message": "Email already exists."})
#             else:
#                 return CustomResponse({"message": "OTP sent successfully"}, status=status_code.HTTP_200_OK)
#         else:
#             return CustomResponse({"message": "Profile information updated successfully"}, status=status_code.HTTP_200_OK)
    
class UserEditProfileViewSet(viewsets.ViewSet):
    """
        UserEditProfileViewSet to Edit the Personal Details of User
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    # def update(self, request):
    #     serializer = UserEditProfileSerializer(
    #         instance=request.user, data=request.data, partial=True
    #     )

    #     if serializer.is_valid():
    #         instance = serializer.save()
    #         message = "Profile information updated successfully"

    #         # Check if the email field was modified
    #         if serializer.email_changed:
    #             otp = generate_otp()
    #             OTP.objects.update_or_create(user_id=instance.id, otp=otp, otp_type=1)
    #             instance.otp = otp
    #             instance.is_email_verified = False
    #             instance.save()

    #             try:
    #                 send_verification_email(instance.email, otp)
    #                 message = "OTP sent successfully."
    #             except Exception as e:
    #                 message = f"Profile information updated successfully. Failed to send OTP: {str(e)}"

    #         return Response({"message": message}, status=status_code.HTTP_200_OK)
        
    #     return Response(serializer.errors, status=status_code.HTTP_400_BAD_REQUEST)

    def update(self, request):
        data = request.data
        full_name = data.get("full_name")
        email = data.get("email")
        profile_pic = data.get("profile_pic")
        company_id = data.get("company_id")

        # Validate full name
        if not full_name:
            return CustomResponse({"message": "Please provide full name."}, status=status_code.HTTP_400_BAD_REQUEST)

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
                send_verification_email(email, otp)
            except Exception as e:
                pass

        # Update profile picture if provided
        if profile_pic:
            update_data["profile_pic"] = profile_pic
        if company_id:
            UserCompany.objects.filter(user=request.user).update(company_id=company_id)
         
        # Perform the update in a single query
        User.objects.filter(id=request.user.id).update(**update_data)
        if email and email != d.email:
            return CustomResponse({"message": "Email changed, otp sent successfully."}, status=status_code.HTTP_200_OK)
        
        return CustomResponse({"message": "Profile updated successfully"}, status=status_code.HTTP_200_OK)
    
# class UserEditProfileViewSet(viewsets.ViewSet):
#     """
#         UserEditProfileViewSet to Edit the Personal Details of User
#     """
#     permission_classes = (IsAuthenticated,)

#     def update(self, request):
#         serializer = UserEditProfileSerializer(
#             instance=request.user, data=request.data, partial=True
#         )

#         serializer.is_valid(raise_exception=True)

#         serializer.save()
#         return CustomResponse({"message": "Profile information updated successfully"}, status=status_code.HTTP_200_OK)

class UserChangePasswordViewSet(viewsets.ViewSet):
    """
        UserChangePasswordViewSet to change the Password of User
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def create(self, request):
        serializer = UserChangePasswordSerializer(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)  

        serializer.update_password(request.user)
        return CustomResponse({"message": "Password updated successfully."}, status=status_code.HTTP_200_OK)


class GlobalSearchViewSet(viewsets.ViewSet):
    """
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
                                           is_admin_approved=True).order_by("-created_at")
        # file_serializer = FilesSerializer(file_obj, many=True)
        # serializer = self.get_serializer(queryset, many=True, context = {"search": search})
        # data = dict()
        # data['project_details'] = serializer.data
        # data['project_files'] = file_serializer.data
        # return CustomResponse(data, status=status_code.HTTP_200_OK)
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(file_obj, request)
            if page is not None:
                serializer = FilesSerializer(instance=page, many=True)
                return CustomResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = FilesSerializer(instance=file_obj, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
        # page = None
        # if page_size:
        #     pagination_class = self.pagination_class()
        #     page = pagination_class.paginate_queryset(file_obj, request)
        # if page is not None:
        #     return CustomResponse(pagination_class.get_paginated_response(page).data)
        # return CustomResponse(file_obj)


#Log out
class LogoutUserViewSet(viewsets.ViewSet):
    """
        LogoutUserViewSet to Logout the User
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def post(self, request):
        request.auth.delete()
        return Response({"message": "Logged out successfully"}, status=status_code.HTTP_200_OK)


#Delete Account
class DeleteUserViewSet(viewsets.GenericViewSet):
    """
        DeleteUserViewSet to delete a user's account
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def update(self, request):
        user = User.objects.filter(id=request.user.id).first()
        if not user:
            return CustomResponse({"message": "User not found."}, status=status_code.HTTP_404_NOT_FOUND)
        user.email = None
        user.is_deleted = True
        user.save()
            
        return CustomResponse({"message": "Your account has been deactivated successfully."}, status=status_code.HTTP_200_OK)


#About the App

class AboutAppViewset(viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)

    def list(self, request):
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
        # device_type = request.query_params.get('device_type')
        # registration_id = request.query_params.get('registration_id')
        # data = {'device_type': device_type, 'registration_id': registration_id}

        serializer = self.action_serializer.get(self.action)(
            data=request.data, instance=request.user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return CustomResponse({"message": "Device Registered Successfully"}, status=status_code.HTTP_200_OK)

    # def perform_destroy(self, request):
    #     """
    #         method used to delete the current user device token
    #     :param request:
    #     :return:
    #     """
    #     device_type = request.GET.get('device_type', 'ios')
    #     registration_id = request.GET.get('registration_id')
    #     if device_type == 'both':
    #         FCMDevice.objects.filter(user=request.user).delete()
    #     elif device_type:
    #         FCMDevice.objects.filter(user=request.user,
    #                                  type=device_type, registration_id=registration_id).delete()
    #     return CustomResponse({"message": "DEVICE_DELETED_SUCCESSFULLY"})
    def perform_destroy(self, request):
        """
        method used to delete the current user device token
        :param request:
        :return:
        """
        device_type = request.GET.get('device_type')
        if device_type == 'both':
            FCMDevice.objects.filter(user=request.user).update(active=False)
        elif device_type:
            FCMDevice.objects.filter(
            user=request.user, type=device_type).update(active=False)
            return CustomResponse({"message": "Device Deleted Successfully"}, status=status_code.HTTP_200_OK)
        

class SendNotiticationViewSet(viewsets.ViewSet):
    """
        SendNotiticationViewSet to send notifications to users
    """
    def update(self, request):
        """
            function to send notifications
        """
        data = {"screen":"home"}
        res = send_notification_bulk([164], "title", "messages", data)
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
        """method to get notification list"""
        queryset = UserNotification.objects.filter(user=request.user).\
            order_by('-created_at')
        unread = queryset.filter(is_read=False).count()
        is_all_read = True if unread == 0 else False
        serializer = self.serializer_detail_class(queryset, many=True)
        data = serializer.data
        if self.request.GET.get('page_size'):
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(queryset, request)
            serializer = self.serializer_detail_class(page, many=True)
            data = pagination_class.get_paginated_response(
                serializer.data).data
        updated_data = {"unread_notification": unread,
                        "notification_data": data, "is_all_read": is_all_read}
        return CustomResponse(updated_data)

    def retrieve(self, request, *args, **kwargs):
        """method to get the notification details"""
        notification_id = kwargs.get('notification_id')
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