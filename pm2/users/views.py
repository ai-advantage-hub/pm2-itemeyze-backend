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
from django.db.models import Q, Case, Value, When, CharField
from fcm_django.models import FCMDevice
from core.pagination import CustomPagination
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
                response_data["id"] = user.id
                response_data["full_name"] = user.full_name

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

from django.http import JsonResponse


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

        # site = Site.objects.create(name=site_name)
        if Site.objects.filter(name__iexact=site_name).exists():
            site = Site.objects.filter(name__iexact=site_name).first()
            print("site", site)
        else:
            site = Site.objects.create(name=site_name)
            print("site2", site)

        if Project.objects.filter(project_name=project_name,site_id_id=site.id).exists():
            return CustomResponse({"message": "Project with this site name already exists."}, status=status_code.HTTP_400_BAD_REQUEST)

        project = Project.objects.create(created_by = request.user, project_name=project_name, site_id_id=site.id)
        if site_name=='PM2':
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
            Q(created_by=request.user)|Q(users__id=request.user.id),
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
    #         c = str(project_id)+'_'+str(file.id)
    #         b = Files.objects.filter(id=file.id).update(file_name=c)
    #         return CustomResponse({"message": "File Created with new user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)
    #     else:
    #         file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, file_name='autogenerated_filename')
    #         c = str(project_id)+'_'+str(file.id)
    #         b = Files.objects.filter(id=file.id).update(file_name=c)
    #         return CustomResponse({"message": "File Created with existing user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)


    def list(self, request, id, *args, **kwargs):
        """
            function to give list of file
        """
        user = Files.objects.filter(id=id).all().values('file_name','thumbnail','name_manufacturer','manufacturer_name__name', 'manufacturer_name__id','manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','secondary_image')
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
            c = str(project_id)+'_'+str(file.id)
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with new user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)
        else:
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with existing user Successfully", "file_id": file.id}, status=status_code.HTTP_201_CREATED)


    def manufacturer_list(self, request):
        """
            function to give list of manufacturers
        """
        name = request.GET.get('name', None)
        manufacturers = ManufacturerName.objects.all()

        if name:
            manufacturers = manufacturers.filter(name__icontains=name).annotate(
                is_na=Case(
                    When(name="NA", then=Value(1)),
                    default=Value(0),
                    output_field=CharField(),
                )
            ).order_by('-is_na', 'name')
        else:
            manufacturers = manufacturers.order_by('name')

        return CustomResponse(manufacturers.values('id', 'name'))


    def create_file(self, request, *args, **kwargs):
        """
            function to create file
        """
        data = request.data
        manufacturer_name = data.get('manufacturer_name')
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        project_id = data.get('project_id')
        thumbnail = data.get('thumbnail')
        secondary_image = data.get('secondary_image')
        manufacturing_number = data.get('manufacturing_number')
        quantity = data.get('quantity')
        project_details = data.get('project_details')
        additional_details = data.get('additional_details')
        recording = data.get('recording')
        location = data.get('location')
        location_points = data.get('location_points')
        # if manufacturer_name:
        #     if not ManufacturerName.objects.filter(name=manufacturer_name).exists():
        #         return CustomResponse({"message": "This manufacturer name does not exist"}, status=status_code.HTTP_400_BAD_REQUEST)
        if manual_manufacturer_name:
            if ManufacturerName.objects.filter(name = manual_manufacturer_name).exists():
                return CustomResponse({"message": "This manufacturer name already exists, please select from list"}, status=status_code.HTTP_400_BAD_REQUEST)
            print("in manual")
            new_manufacturer = ManufacturerName.objects.create(users = request.user,name=manual_manufacturer_name, added_by=2, is_read=False)
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False,secondary_image=secondary_image)
            c = str(project_id)+'_'+str(file.id)
            e = ManufacturerName.objects.filter(id=new_manufacturer.id).first()
            print("eee",e.name)
            b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
            file_created = Files.objects.filter(id=file.id).all().values().first()
            file_details = {
                "message" : "File Created with new Manufacturer Successfully",
                "file_id": file.id,
                "file_details": file_created,
                "status" : status_code.HTTP_200_OK,

            }
            return JsonResponse(file_details)
            # return CustomResponse({"message": "File Created with new Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False,secondary_image=secondary_image)
            c = str(project_id)+'_'+str(file.id)
            e = ManufacturerName.objects.filter(id=manufacturer_name).first()
            print("eee",e.name)
            b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
            file_created = Files.objects.filter(id=file.id).all().values().first()
            file_details = {
                "message" : "File Created with existing Manufacturer Successfully",
                "file_id": file.id,
                "file_details": file_created,
                "status" : status_code.HTTP_200_OK,

            }
            return JsonResponse(file_details)
            # return CustomResponse({"message": "File Created with existing Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)

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
        data = request.data
        file_id = data.get("delete_file_id", [])
        if not Project.objects.filter(id=id).exists():
            return CustomResponse({"message": "Project of this id does not exist"}, status=status_code.HTTP_400_BAD_REQUEST)

        if file_id:
            print("file id", file_id)
            for id2 in file_id:
                print("id", id2)
                file = Files.objects.filter(id=id2).update(is_marked_deleted=True, deleted_at=timezone.now())

        def build_query(base_filters, name=None):
            filters = base_filters
            if name:
                filters = filters & Q(location__icontains=name) | \
                                  Q(manufacturer_name__name__icontains=name) | \
                                  Q(manufacturing_number__icontains=name)
            return filters

        def get_files(list_type, id, name=None):
            base_filters =  (Q(is_marked_deleted=False) & \
                            Q(is_deleted=False)) & \
                          Q(project_id=id)

            if list_type == '1':
                # master type and submitted to admin
                base_filters &= Q(submitted_to_admin=True)
            elif list_type == '2':
                # type  2 for those files which are not submitted to admin and created by requested user
                base_filters &= Q(is_admin_approved=False) & \
                                 Q(submitted_to_admin=False) & \
                                 Q(created_by_id=request.user)
            elif list_type == '3':
                # type  3 for those files which are submitted to admin and created by requested user
                base_filters &= Q(submitted_to_admin=True) & Q(created_by_id=request.user)
            else:
                return CustomResponse({"message": "Invalid filter type"}, status=status_code.HTTP_400_BAD_REQUEST)

            query = build_query(base_filters, name)
            files = Files.objects.filter(query).values('id', 'file_name', 'created_at', 'thumbnail', 'name_manufacturer', 'manufacturer_name__name', 'manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording', 'is_file_disapproved', 'disapproved_reason', 'submitted_to_admin', 'disapproved_file_is_edited', 'secondary_image','created_by').order_by('-is_file_disapproved','-created_at')
            return files

        # Usage
        files = get_files(list_type, id, name)


        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)

        if page is not None:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(files)


    def file_list2(self, request, id):
        """
        function to give a list of files based on the provided filter
        """
        list_type = request.GET.get('list_type', None)
        name = request.GET.get('name', None)
        page_size = request.GET.get('page_size', '')
        data = request.data
        file_id = data.get("delete_file_id", [])

        if not Project.objects.filter(id=id).exists():
            return CustomResponse({"message": "Project of this id does not exist"}, status=status_code.HTTP_400_BAD_REQUEST)

        if file_id:
            print("file id", file_id)
            for id2 in file_id:
                print("id", id2)
                Files.objects.filter(id=id2).update(is_marked_deleted=True)

        print("list type", list_type)
        if list_type == '1':
            # type one for only created files that are not submitted to admin
            if name == None:
                files = Files.objects.filter(project_id=id, created_by=request.user,submitted_to_admin=False, is_marked_deleted=False).all().values('id','file_name','thumbnail','name_manufacturer','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason','submitted_to_admin').order_by('-created_at')
            else:
                files = Files.objects.filter(Q(location__icontains=name) |
                                        Q(manufacturer_name__name__icontains=name) |
                                        Q(manufacturing_number__icontains=name),
                                        project_id=id, created_by=request.user,submitted_to_admin=False, is_marked_deleted=False).all().values('id','file_name','thumbnail','name_manufacturer','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason','submitted_to_admin').order_by('-created_at')

        elif list_type == '2':
            # type 2 for those files which are submitted to admin
            if name == None:
                files = Files.objects.filter(project_id=id, created_by=request.user,is_admin_approved=True, submitted_to_admin=True, is_marked_deleted=False).all().values('id','file_name','thumbnail','name_manufacturer','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason','submitted_to_admin').order_by('-created_at')

            else:
                files = Files.objects.filter(Q(location__icontains=name) |
                                        Q(manufacturer_name__name__icontains=name) |
                                        Q(manufacturing_number__icontains=name),
                                        project_id=id, created_by=request.user,is_admin_approved=True, submitted_to_admin=True, is_marked_deleted=False).all().values('id','file_name','thumbnail','name_manufacturer','manufacturer_name__name','manufacturer_name__id', 'manufacturing_number', 'location', 'quantity', 'project_details', 'additional_details', 'recording','is_file_disapproved', 'disapproved_reason','submitted_to_admin').order_by('-created_at')

        else:
            return CustomResponse({"message": "Invalid filter type"}, status=status_code.HTTP_400_BAD_REQUEST)

        print("files", files)

        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

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

        if manual_manufacturer_name:
            new_user = User.objects.create(full_name=manual_manufacturer_name)
            Files.objects.filter(id=id).update(manufacturer_name_id=new_user.id,thumbnail=thumbnail, manual_manufacturer_name=manual_manufacturer_name, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location, location_points=location_points,is_edited=True)
            return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)
        else:
            Files.objects.filter(id=id).update(thumbnail=thumbnail, manufacturing_number=manufacturing_number, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_edited=True)
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
        recording = data.get('recording')
        secondary_image = data.get("secondary_image")

        if manual_manufacturer_name:

            if ManufacturerName.objects.filter(name = manual_manufacturer_name).exists():
                file = Files.objects.filter(id=id).update(thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location, location_points=location_points,is_edited=True, submitted_to_admin=False,recording=recording,secondary_image=secondary_image)
                # return CustomResponse({"message": "This manufacturer name already exists, please select from list"}, status=status_code.HTTP_400_BAD_REQUEST)
            else:

                manufacturer = ManufacturerName.objects.create(users = request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
                file = Files.objects.filter(id=id).update(manufacturer_name_id=manufacturer.id,thumbnail=thumbnail, manual_manufacturer_name=manual_manufacturer_name, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location, location_points=location_points,is_edited=True, submitted_to_admin=False, recording=recording,secondary_image=secondary_image)
                e = ManufacturerName.objects.filter(id=manufacturer.id).first()
                print("eee",e.name)
                b = Files.objects.filter(id=id).update(name_manufacturer= e.name)
            c = Files.objects.filter(id=id).first()
            print("c id",c.is_file_disapproved)
            if c.is_file_disapproved==True:
                c.disapproved_file_is_edited=True
                c.disapproved_status=2
                c.save()
            file_created = Files.objects.filter(id=id).all().values().first()
            file_details = {
                "message" : "File updated with new Manufacturer Successfully",
                "file_id": id,
                "file_details": file_created,
                "status" : status_code.HTTP_200_OK,

            }
            return JsonResponse(file_details)
            # return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)
        elif manufacturer_name:
            file = Files.objects.filter(id=id).update(thumbnail=thumbnail, manufacturing_number=manufacturing_number, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_edited=True, submitted_to_admin=False,recording=recording,secondary_image=secondary_image)
            e = ManufacturerName.objects.filter(id=manufacturer_name).first()
            print("eee",e.name)
            b = Files.objects.filter(id=id).update(name_manufacturer= e.name)
            c = Files.objects.filter(id=id).first()
            if c.is_file_disapproved==True:
                c.disapproved_file_is_edited=True
                c.disapproved_status=2
                c.save()
            file_created = Files.objects.filter(id=id).all().values().first()
            file_details = {
                "message" : "File updated with existing Manufacturer Successfully",
                "file_id": id,
                "file_details": file_created,
                "status" : status_code.HTTP_200_OK,

            }
            return JsonResponse(file_details)
            # return CustomResponse({"message": "File updated Successfully"}, status=status_code.HTTP_200_OK)

        else:
            file = Files.objects.filter(id=id).update(thumbnail=thumbnail, manufacturing_number=manufacturing_number, location=location, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_edited=True, submitted_to_admin=False, recording=recording,secondary_image=secondary_image)
            # e = ManufacturerName.objects.filter(id=manufacturer_name).first()
            # print("eee",e.name)
            # b = Files.objects.filter(id=id).update(name_manufacturer= e.name)
            c = Files.objects.filter(id=id).first()
            print("c id",c.is_file_disapproved)
            if c.is_file_disapproved==True:
                c.disapproved_file_is_edited=True
                c.disapproved_status=2
                c.save()
            file_created = Files.objects.filter(id=id).all().values().first()
            file_details = {
                "message" : "File updated with existing Manufacturer Successfully",
                "file_id": id,
                "file_details": file_created,
                "status" : status_code.HTTP_200_OK,

            }
            return JsonResponse(file_details)


    def destroy(self, request, id):
        """
            delete method to delete the file from the database.
        """
        user = Files.objects.filter(id = id, is_marked_deleted=False).first()
        if not user:
            return CustomResponse({"message": "File Not Found"}, status=status_code.HTTP_400_BAD_REQUEST)
        if user.submitted_to_admin == False:
            user.delete()
        else:
            user.is_marked_deleted = True
            user.deleted_at = timezone.now()
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
            c = str(project_id)+'_'+str(file.id)
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with new Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
            c = str(project_id)+'_'+str(file.id)
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return CustomResponse({"message": "File Created with existing Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)



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
            c = str(project_id)+'_'+str(file.id)
            b = Files.objects.filter(id=file.id).update(file_name=c)
            return {"message": "File Created with new Manufacturer Successfully", "file_id": file.id, "thumbnail_url": thumbnail_url}

        file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)
        c = str(project_id)+'_'+str(file.id)
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


class CreateFileWithImage2(viewsets.ViewSet):
    """
        Class to upload offline created files to server
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def generate_signed_url(self, object_key):
        """
            function to generate signed url
        """
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

    def compress_image(self, image):
        """
            function to compress image
        """
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

    def create_and_upload_file(self, request, temp_file_id):
        """
            function to upload files
        """
        print("in create_and_upload_file function")
        print("temp file id:", temp_file_id)

        def process_image(image):
            if image:
                compressed_image = self.compress_image(image)
                original_file_name = f"your_custom_prefix_{uuid.uuid4().hex}.png"
                path_key = "image/{}_{}".format(uuid.uuid4(), original_file_name.replace(' ', '_'))

                # Upload compressed image to S3
                s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
                s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)

                # Generate signed URL for the uploaded image
                thumbnail_url = self.generate_signed_url(path_key)
                print("thumbnail", thumbnail_url)
                return thumbnail_url
            else:
                print("No image provided.")
                return None

        upload = request.data.get(f'file_{temp_file_id}')
        secondary_img = request.data.get(f'secondary_image_{temp_file_id}')

        thumbnail = process_image(upload)
        secondary_image = process_image(secondary_img)

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
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=True,secondary_image=secondary_image)
            c = f"{project_id}_{file.id}_filename"
            e = ManufacturerName.objects.filter(id=new_manufacturer.id).first()
            print("eee",e.name)
            b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
            # b = Files.objects.filter(id=file.id).update(file_name=c)
            return {"message": "File Created with new Manufacturer Successfully","temp_file_id": temp_file_id ,"file_id": file.id, "thumbnail_url": thumbnail,'secondary_image': secondary_image}
        elif manufacturer_name:
            file = Files.objects.create(created_by=request.user, manufacturer_name_id=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=True,secondary_image=secondary_image)
            c = f"{project_id}_{file.id}_filename"
            e = ManufacturerName.objects.filter(id=manufacturer_name).first()
            print("eee",e.name)
            b = Files.objects.filter(id=file.id).update(file_name=c, name_manufacturer= e.name)
            # b = Files.objects.filter(id=file.id).update(file_name=c)
            return {"message": "File created with existing Manufacturer Successfully","temp_file_id": temp_file_id ,"file_id": file.id, "thumbnail_url": thumbnail,'secondary_image': secondary_image}

    def create(self, request, *args, **kwargs):
        """
            function to get temp file id
        """
        try:
            temp_file_ids = request.data.getlist('temp_file_id')
            response_data = []
            print("Received temp_file_ids:", temp_file_ids)

            for temp_file_id in temp_file_ids:
                print("Processing temp_file_id:", temp_file_id)
                print("calling create_and_upload_file function")
                result = self.create_and_upload_file(request, temp_file_id)
                print("create_and_upload_file function called")
                print("response data", response_data)
                response_data.append(result)
                print("result", result)

            return CustomResponse({"message": "Files uploaded successfully", "data": response_data}, status=status_code.HTTP_200_OK)

        except Exception as e:
            return CustomResponse({"error": str(e)}, status=status_code.HTTP_400_BAD_REQUEST)



class CreateEditFileWithImage(viewsets.ViewSet):
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
        file_id = request.data.get(f'file_id_{temp_file_id}')
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

        b = Files.objects.filter(id=file_id)
        print("file_id",file_id)
        if b.exists():
            print("editing")
            if thumbnail_url:
                b.update(created_by=request.user, manufacturer_name=manufacturer_name, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, thumbnail=thumbnail_url, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location=location, location_points=location_points, is_admin_approved=True, submitted_to_admin=False)

                return {"message": "File updated succesfully with thumbnail", "file_id": file_id, "thumbnail_url": thumbnail_url}


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



class UpdateFileWithImage(viewsets.ViewSet):
    """
        class to update offline edited files
    """
    permission_classes = (IsAuthenticated, CheckUserRoleStatusPermission)

    def generate_signed_url(self, object_key):
        """
            function to generate signed url
        """
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

    def compress_image(self, image):
        """
            function to compress image
        """
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
        """
            function to upload updated files to server
        """
        try:
            print("in upload function")
            upload = file_data['image']
            print("image", upload)
            thumbnail_null = file_data['image_null']
            thumbnail_url = file_data['image']
            secondary_image = file_data['secondary_image']
            print("thumbnail_null", thumbnail_null)

            if upload:
                print("in if upload")
                compressed_image = self.compress_image(upload)
                original_file_name = f"your_custom_prefix_{uuid.uuid4().hex}.png"
                path_key = "image/{}_{}".format(uuid.uuid4(), original_file_name.replace(' ', '_'))

                # Upload compressed image to S3
                s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
                s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)

                # Generate signed URL for the uploaded image
                thumbnail_url = self.generate_signed_url(path_key)
                print("thumbnail", thumbnail_url)

            if thumbnail_null:
                print("in if thumbnail null")
                thumbnail_url = None

            if secondary_image:
                print("in if upload")
                compressed_image = self.compress_image(secondary_image)
                original_file_name = f"your_custom_prefix_{uuid.uuid4().hex}.png"
                path_key = "image/{}_{}".format(uuid.uuid4(), original_file_name.replace(' ', '_'))

                # Upload compressed image to S3
                s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
                s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(compressed_image, path_key)

                # Generate signed URL for the uploaded image
                secondary_image = self.generate_signed_url(path_key)
                print("thumbnail", thumbnail_url)

            else:
                print("in if thumbnail null")
                secondary_image = None

            print("taking input")
            # Extract other necessary fields from file_data
            file_id = file_data['file_id']
            manufacturer_name = file_data['manufacturer_name']
            manual_manufacturer_name = file_data['manual_manufacturer_name']
            project_id = file_data['project_id']
            manufacturing_number = file_data['manufacturing_number']
            quantity = file_data['quantity']
            project_details = file_data['project_details']
            additional_details = file_data['additional_details']
            recording = file_data['recording']
            location = file_data['location']

            is_file_disapproved = file_data['is_file_disapproved']

            print("updating file")
            file_instance = Files.objects.get(id=file_id)
            print("file_instance name", file_instance.file_name)

            if manual_manufacturer_name:
                print("manual manufacturer")
                new_manufacturer = ManufacturerName.objects.create(users=request.user, name=manual_manufacturer_name, added_by=2, is_read=False)
                # file_instance.name_manufacturer = new_manufacturer.id
                file_instance.manual_manufacturer_name = manual_manufacturer_name
                if upload:
                    print("thumbnail", thumbnail_url)
                    file_instance.thumbnail = thumbnail_url
                if thumbnail_null:
                    print("thumbnail null", thumbnail_null)
                    file_instance.thumbnail = thumbnail_url
                if secondary_image:
                    file_instance.secondary_image=secondary_image
                if manufacturing_number:
                    file_instance.manufacturing_number = manufacturing_number
                if quantity:
                    file_instance.quantity = quantity
                if project_details:
                    file_instance.project_details = project_details
                if additional_details:
                    file_instance.additional_details = additional_details
                if recording:
                    file_instance.recording = recording
                if location:
                    file_instance.location = location

                if is_file_disapproved:
                    file_instance.submitted_to_admin=True
                    file_instance.is_edited=True
                    file_instance.disapproved_status=2

                file_instance.save()

                z = Files.objects.filter(id=file_id).first()
                if z.is_file_disapproved==True:
                    z.disapproved_file_is_edited=True

                    z.save()

                c = f"{project_id}_{file_instance.id}_filename"
                e = ManufacturerName.objects.filter(id=new_manufacturer.id).first()
                print("eee", e.name)
                Files.objects.filter(id=file_instance.id).update(file_name=c, name_manufacturer=e.name, manual_manufacturer_name=e.name, manufacturer_name_id=new_manufacturer.id)
                if upload:

                    return {"message": "File updated with new Manufacturer Successfully", "file_id": file_instance.id, "thumbnail_url": thumbnail_url,"secondary_image": secondary_image}
                else:
                    return {"message": "File updated with new Manufacturer Successfully", "file_id": file_instance.id}

            elif manufacturer_name:

                print("existing manufacturer")
                # file_instance.manufacturer_name = manufacturer_name
                manufacturer_instance = ManufacturerName.objects.get(id=manufacturer_name)
                file_instance.manufacturer_name = manufacturer_instance
                # file_instance.manual_manufacturer_name = manual_manufacturer_name
                if upload:
                    print("thumbnail", thumbnail_url)
                    file_instance.thumbnail = thumbnail_url
                if thumbnail_null:
                        print("thumbnail null", thumbnail_null)
                        file_instance.thumbnail = thumbnail_url
                if secondary_image:
                    file_instance.secondary_image=secondary_image
                if manufacturing_number:
                    file_instance.manufacturing_number = manufacturing_number
                if quantity:
                    file_instance.quantity = quantity
                if project_details:
                    file_instance.project_details = project_details
                if additional_details:
                    file_instance.additional_details = additional_details
                if recording:
                    file_instance.recording = recording
                if location:
                    file_instance.location = location

                if is_file_disapproved:
                    file_instance.submitted_to_admin=True
                    file_instance.is_deleted=True
                    file_instance.disapproved_status=2

                file_instance.save()

                z = Files.objects.filter(id=file_id).first()
                if z.is_file_disapproved==True:
                    z.disapproved_file_is_edited=True
                    z.save()

                c = f"{project_id}_{file_instance.id}_filename"
                e = ManufacturerName.objects.filter(id=manufacturer_name).first()
                print("eee", e.name)
                Files.objects.filter(id=file_instance.id).update(file_name=c, name_manufacturer=e.name, manufacturer_name_id=manufacturer_name)

                if upload:
                    return {"message": "File updated with existing Manufacturer successfully", "file_id": file_instance.id, "thumbnail_url": thumbnail_url,"secondary_image": secondary_image}
                else:
                    return {"message": "File updated with existing Manufacturer Successfully", "file_id": file_instance.id}

            else:
                # file_instance.manufacturer_name = manufacturer_instance
                # file_instance.manual_manufacturer_name = manual_manufacturer_name
                if upload:
                    print("thumbnail", thumbnail_url)
                    file_instance.thumbnail = thumbnail_url
                if thumbnail_null:
                        print("thumbnail null", thumbnail_null)
                        file_instance.thumbnail = thumbnail_url
                if secondary_image:
                    file_instance.secondary_image=secondary_image
                if manufacturing_number:
                    file_instance.manufacturing_number = manufacturing_number
                if quantity:
                    file_instance.quantity = quantity
                if project_details:
                    file_instance.project_details = project_details
                if additional_details:
                    file_instance.additional_details = additional_details
                if recording:
                    file_instance.recording = recording
                if location:
                    file_instance.location = location

                if is_file_disapproved:
                    file_instance.submitted_to_admin=True
                    file_instance.is_deleted=True
                    file_instance.disapproved_status=2

                file_instance.save()

                z = Files.objects.filter(id=file_id).first()
                if z.is_file_disapproved==True:
                    z.disapproved_file_is_edited=True
                    z.save()

                if upload:
                    return {"message": "File updated with successfully", "file_id": file_instance.id, "thumbnail_url": thumbnail_url,"secondary_image": secondary_image}
                else:
                    return {"message": "File updated with Successfully", "file_id": file_instance.id}


        except Exception as e:
            return {"error": str(e)}

    def update(self, request, *args, **kwargs):
        """
            functio to take updated file from user
        """
        try:
            file_ids = request.data.getlist('file_id')
            response_data = []
            print("Received file_ids:", file_ids)

            for file_id in file_ids:
                print("Processing file_id:", file_id)
                # Convert file_id to integer
                file_id = int(file_id)

                # Construct key names for each file in form data
                image_key = f"image_{file_id}"
                image_null_key = f"image_null_{file_id}"
                manufacturer_name_key = f"manufacturer_name_{file_id}"
                manual_manufacturer_name_key = f"manual_manufacturer_name_{file_id}"
                project_id = "project_id"
                manufacturing_number_key = f"manufacturing_number_{file_id}"
                quantity_key = f"quantity_{file_id}"
                project_details_key = f"project_details_{file_id}"
                additional_details_key = f"additional_details_{file_id}"
                recording_key = f"recording_{file_id}"
                location_key = f"location_{file_id}"
                secondary_image = f"secondary_image_{file_id}"

                is_file_disapproved_key = f"is_file_disapproved_{file_id}"

                # ... (similarly for other fields)

                # Create a dictionary with form data for the current file
                file_data = {
                    'file_id': file_id,
                    'image': request.data.get(image_key),
                    'image_null': request.data.get(image_null_key),
                    'manufacturer_name': request.data.get(manufacturer_name_key),
                    'manual_manufacturer_name': request.data.get(manual_manufacturer_name_key),
                    'project_id': request.data.get(project_id),
                    'manufacturing_number': request.data.get(manufacturing_number_key),
                    'quantity': request.data.get(quantity_key),
                    'project_details': request.data.get(project_details_key),
                    'additional_details': request.data.get(additional_details_key),
                    'recording': request.data.get(recording_key),
                    'location': request.data.get(location_key),

                    'is_file_disapproved': request.data.get(is_file_disapproved_key),
                    'secondary_image': request.data.get(secondary_image)

                    # ... (similarly for other fields)
                }

                result = self.create_and_upload_file(request, file_data)
                print("upload function called")
                print("response data", response_data)
                response_data.append(result)
                print("result", result)

            return CustomResponse({"message": "Files updated successfully", "data": response_data}, status=status_code.HTTP_200_OK)

        except Exception as e:
            return CustomResponse({"error": str(e)}, status=status_code.HTTP_400_BAD_REQUEST)

