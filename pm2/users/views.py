from django.shortcuts import render
from rest_framework import mixins, viewsets, generics, filters
from rest_framework.response import Response
from .models import User, OTP, Project, Files, Company
from custom_admin.models import ContentManagement
from .serializers import SignupSerializer, UserLoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer, CreateProjectSerializer, CreateFileDetailsSerializer, ProjectDetailsViewSerializer, ContentManagementSerializer
from rest_framework.authtoken.models import Token
from core.common_utils import generate_otp, send_verification_email
from core.response import CustomResponse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework import status as status_code
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from core.messages import SUCCESS_MESSAGES 
from django.utils.translation import gettext
from rest_framework.permissions import IsAuthenticated
from core.permissions import CheckUserRoleStatusPermission

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
    def create(self,request):
        data = request.data
        email=data.get("email")
        if not email:
            return CustomResponse({"message": "Please enter email"})
        user=User.objects.filter(email=email).first()
        print("ddfgfregvrf",user)
        otp = generate_otp()
        OTP.objects.update(user=user,otp=otp,otp_type=1)
        try:
            send_verification_email(user.email, otp)
        except Exception as e:
            print(e)
        pass
        return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('RESEND_EMAIL_OTP')), "otp":otp}, status=status_code.HTTP_200_OK)
    

class VerifyOTPViewSet(viewsets.ViewSet):
    """
        VerifyOTPViewSet used for verifying the otp  
    """
    def create(self,request):
        data=request.data
        otp=data.get('otp')
        email=data.get('email')
        type = data.get('type')

        # will remove in future
        if otp == "1234":
            user = User.objects.filter(email=email.lower()).first()
            user.is_email_verified=True
            user.save()
            return CustomResponse({"message" : "OTP Verified, User created Successfully" , "user_id": user.id}, status=status_code.HTTP_200_OK)


        user = OTP.objects.filter(otp=otp, otp_type=type, is_used=False).first()
        if not user:
            return CustomResponse({"message" : "Wrong OTP"})
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"})
        else:
            user_id = user.user_id
            User.objects.filter(email=email).update(is_email_verified=True)
            OTP.objects.filter(otp=otp, otp_type=type).update(is_used=True)
            return CustomResponse({"message" : "OTP Verified, User created Successfully" , "user_id": user_id}, status=status_code.HTTP_200_OK)


class UserLoginViewSet(viewsets.ViewSet):
    """
        UserLoginViewSet for User Login
    """
    def create(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return CustomResponse({"token": token.key}, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse({"msg": "Please provide valid Credentials"}, status=status_code.HTTP_200_OK)
        

class ForgotPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
        ForgotPasswordViewSet for forget password
    """
    serializer_class = ForgotPasswordSerializer

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

    def update(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if not user:
            return CustomResponse({"message": "User not found."}, status=status_code.HTTP_400_BAD_REQUEST)
        serializer.update(user, serializer.validated_data)
        return CustomResponse({"message": "Password reset successfully."}, status=status_code.HTTP_200_OK)


#Home


class ProjectViewSet(viewsets.ModelViewSet):
    """
        CreateProjectViewSet to create project
    """
    permission_classes = (IsAuthenticated,)
    queryset = Project.objects.all()
    serializer_class = CreateProjectSerializer

    def create(self, request, *args, **kwargs):
        project_name = request.data.get('project_name')
        user = request.user 
        if not project_name:
            return CustomResponse({"message": "Project name cannot be empty."})

        # Check if the project name is unique
        if Project.objects.filter(project_name=project_name).exists():
            return CustomResponse({"message": "Project with this name already exists."})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=user)

        return CustomResponse(serializer.data, status=status_code.HTTP_201_CREATED)

    def search(self, request):
        project_name = request.GET.get('project_name', None)
        project = Project.objects.all().values()
        if project_name:
            project=project.filter(project_name__icontains=project_name)
            if not project:
                return CustomResponse({"message": "No Data Found."})
            return CustomResponse(project, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse(project, status=status_code.HTTP_200_OK)
    
#
# class ListProjectViewSet(viewsets.ModelViewSet):
#     """
#         ListProjectViewSet to get the list of projects
#     """
#     def list(self, request, *args, **kwargs):
#         user = Project.objects.filter(user_id=request.user.id).all().values()
#         return CustomResponse(user)
#


class FileDetailsViewSet(viewsets.ModelViewSet):
    """
        CreateFileDetailsViewSet to add file details
    """
    queryset = Files.objects.all()
    serializer_class = CreateFileDetailsSerializer

    def perform_create(self, serializer):
        serializer.save(file_name="autogenerated_filename")

    def create(self, request, *args, **kwargs):
        request_data = request.data.copy()
        request_data["manufacturer_name"] = self.request.user.id
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.context["project_id"] = request_data["project_id"]
        self.perform_create(serializer)
        return CustomResponse(serializer.data, status=status_code.HTTP_201_CREATED)

    def list(self, request):
        location = request.GET.get('location', None)
        manufacturer_name = request.GET.get('manufacturer_name', None)
        manufacturing_number = request.GET.get('manufacturing_number', None)
        user = Files.objects.all().values()
        if location:
            user = user.filter(location__icontains=location)
            return CustomResponse(user, status=status_code.HTTP_200_OK)
        if manufacturer_name:
            user = user.filter(manufacturer_name__icontains=manufacturer_name)
            return CustomResponse(user, status=status_code.HTTP_200_OK)
        if manufacturing_number:
            user = user.filter(manufacturing_number__icontains=manufacturing_number)
            return CustomResponse(user, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse(user, status=status_code.HTTP_200_OK)
    

# class ListFileDetailsViewSet(viewsets.ModelViewSet):
#     """
#         ListFileDetailsViewSet to list and search file details
#     """
#     def list(self, request):
#         location = request.GET.get('location', None)
#         manufacturer_name = request.GET.get('manufacturer_name', None)
#         manufacturing_number = request.GET.get('manufacturing_number', None)
#         user = Files.objects.all().values()
#         if location:
#             user = user.filter(location__icontains=location)
#             return CustomResponse(user)
#         if manufacturer_name:
#             user = user.filter(manufacturer_name__icontains=manufacturer_name)
#             return CustomResponse(user)
#         if manufacturing_number:
#             user = user.filter(manufacturing_number__icontains=manufacturing_number)
#             return CustomResponse(user)
#         else:
#             return CustomResponse(user)

        
class ProjectDetailsViewSet(viewsets.ModelViewSet):
    """
        ProjectDetailsViewSet to view to project details
    """
    serializer_class = ProjectDetailsViewSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return Project.objects.filter(id=pk)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
        

class EditFileViewSet(viewsets.ModelViewSet):
    """
        EditFileViewSet to edit the file on Left Swipe and delete on right swipe
    """      
    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return Files.objects.filter(id=pk)
    
    def update(self, request, pk=None):
        """
            update method to update the file details.
        """
        queryset = self.get_queryset()
        obj = queryset.get(pk=pk)
        serializer = CreateFileDetailsSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            #return CustomResponse({'message': 'File details edited successfully.'})
            return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('FILE_UPDATED'))}, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse(serializer.errors, status=status_code.HTTP_200_OK)
        
    def destroy(self, request, pk=None):
        """
            delete method to delete the file from the database.
        """
        queryset = self.get_queryset()
        obj = queryset.get(pk=pk)
        obj.delete()
        #return CustomResponse({'message': 'File deleted successfully.'})
        return CustomResponse({"message": gettext(SUCCESS_MESSAGES.get('FILE_DELETED'))}, status=status_code.HTTP_400_BAD_REQUEST)


class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    """
        TermsAndConditionsViewSet to get terms and conditions
    """
    def list(self, request):
        content = ContentManagement.objects.all()
        serializer = ContentManagementSerializer(content, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)


#Settings

class ViewProfileViewSet(viewsets.ModelViewSet):
    """
        ViewProfileViewSet to get the users details
    """
    def list(self, request, id):
        user = User.objects.filter(id=id).all().values('full_name', 'email', 'profile_pic')
        if not user:
            return CustomResponse({"message" : "User Not Found"})
        return CustomResponse(user)
    

class CompanyNameViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission,)
    
    def list(self, request):
        user=Company.objects.all().values('id','name')
        return CustomResponse(user)
    

class UserListingViewSet(viewsets.ViewSet):
    #permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission,)
    
    def list(self, request):
        user=User.objects.all().values('id','full_name')
        return CustomResponse(user)