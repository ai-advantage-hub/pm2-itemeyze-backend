from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins
from custom_admin.serializers import AdminLoginSerializer,AdminResetPasswordSerializer, CreateFileDetailsSerializer, ForgotPasswordSerializer, ProjectDetailSerializer,FilesSerializer,FilesPointSerializer, UserListAdminSerializer,UserDetailSerializer, UserListingSerializer
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from users.models import Company, UserCompany, User,Project,Files, UserNotification, Site, ManufacturerName
from django.contrib.auth.hashers import check_password
from custom_admin.models import *
from core.response import CustomResponse
from django.db.models import Count
from core.common_utils import generate_otp, send_verification_email, send_subadmin_credentials, send_notification_bulk, logged_out_users, subadmin_deleted, send_updated_subadmin_credentials
from core.permissions import CheckAdminRoleStatusPermission, CheckAdminOrSubAdminRoleStatusPermission
from rest_framework.permissions import IsAuthenticated
from users.models import OTP
from django.utils import timezone
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
import pandas as pd
from rest_framework.decorators import action
import os
import csv
from config.local import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
import boto3
import uuid
from rest_framework import status as status_code
from django.db.models import Q
from core.pagination import CustomPagination
from django.db import transaction
from django.db.models import Count, F, IntegerField, ExpressionWrapper
from django.db.models.functions import TruncMonth, TruncDate
from calendar import monthrange
from datetime import date, timedelta
import logging
log = logging.getLogger(__name__)


class AdminLoginView(viewsets.ViewSet):
    """
        AdminLoginView view for admin to login
    """

    def create(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return CustomResponse({"token": token.key, "user_role": user.user_role, "modules_accessible": user.modules_accessible}, status=status.HTTP_200_OK)
        else:
            return CustomResponse({"msg": "Please provide valid Credentials"}, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
        ForgotPasswordViewSet for forget password
    """
    serializer_class = ForgotPasswordSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return CustomResponse({"message": "OTP Sent Successfully"})


class ResetPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
        ResetPasswordViewSet to reset password
    """

    def create(self, request):
        data = request.data
        otp = data.get("otp")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")
        if not otp:
            return CustomResponse({"message": "Please provide otp"}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return CustomResponse({"message": "Please provide new_password"}, status=status.HTTP_400_BAD_REQUEST)
        if not confirm_password:
            return CustomResponse({"message": "Please provide confirm_password"}, status=status.HTTP_400_BAD_REQUEST)        
        user = OTP.objects.filter(otp=otp,otp_type=3).first()
        if not user:
            return CustomResponse({"message": "Wrong OTP"}, status=status.HTTP_400_BAD_REQUEST)
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
        if not user:
            return CustomResponse({"message": "OTP incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return CustomResponse({"message": "Both Password are not same"}, status=status.HTTP_400_BAD_REQUEST)
        admin_user = User.objects.filter(id=user.user_id).first()
        admin_user.set_password(confirm_password)
        admin_user.is_email_verified = True 
        admin_user.save()
        return CustomResponse({"message": "Password Changed successfully"}, status=status.HTTP_200_OK)


class AdminProfileViewSet(viewsets.ViewSet):
    """
    this view is for admin profile listing, admin profile update and admin change password
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)

    def list(self, request):
        user = User.objects.filter(id=request.user.id).all().values("full_name", "email", "profile_pic")
        print(user)
        return CustomResponse(user)

    def update(self, request):
        data = request.data
        full_name = data.get("full_name")
        email = data.get("email")
        profile_pic = data.get("profile_pic")
        if not full_name:
            return CustomResponse({"message": "Please provide full name."}, status=status.HTTP_400_BAD_REQUEST)
        if email and User.objects.filter(email=email).exclude(id=request.user.id).exists():
            return CustomResponse({"message": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)    

        update_data = {"full_name": full_name}
        requested_user = User.objects.filter(id=request.user.id).first()

        if email and email != requested_user.email:
            update_data["email"] = email
            update_data["is_email_verified"] = False
            otp = generate_otp()
            OTP.objects.update_or_create(user_id=request.user.id, otp=otp, otp_type=1)
            try:
                send_verification_email(email, otp)
            except Exception as e:
                pass

        if profile_pic:
            update_data["profile_pic"] = profile_pic

        User.objects.filter(id=request.user.id).update(**update_data)
        return CustomResponse({"message": "Profile updated successfully"}, status=status.HTTP_200_OK)
    
    def validate(self, request):
        data = request.data
        otp = data.get("otp")
        if not otp:
            return CustomResponse({"message": "Please provide otp"}, status=status.HTTP_400_BAD_REQUEST)
        user = OTP.objects.filter(otp_type=1, is_used=False, otp=otp).first()
        if not user:
            return CustomResponse({"message": "Wrong OTP"}, status=status.HTTP_400_BAD_REQUEST)
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
        if not user:
            return CustomResponse({"message": "OTP incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            User.objects.filter(id=user.user_id).update(is_email_verified=True)
            OTP.objects.filter(otp_type=1, otp=otp).update(is_used=True)
            return CustomResponse({"message": "Email Verified Successfully"}, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = AdminResetPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.update_password()
            return CustomResponse({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
        else:
            error_message = serializer.errors.get('message', ['Error Occurred'])[0]
            return CustomResponse({"message": error_message}, status=status.HTTP_400_BAD_REQUEST)


class ContentManagementViewSet(viewsets.ViewSet):
    """
    this view is for content management like view content,update content,and delete content
    """

    def list(self, request):
        type = request.GET.get('type')
        user=ContentManagement.objects.filter(content_type=type).all().values("content")
        return CustomResponse(user, status=status.HTTP_200_OK)
    
    def update(self, request):
        data = request.data
        type = data.get("type")
        content = data.get("content")
        if not content:
            return CustomResponse({"message": "Please provide content."}, status=status.HTTP_400_BAD_REQUEST)
        query_set = ContentManagement.objects.filter(content_type=type).update(content=content)
        if not query_set:
            ContentManagement.objects.create(content_type=type, content=content)
        return CustomResponse({"message": "Details Updated Successfully."}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        data = request.data
        type = data.get("type")
        ContentManagement.objects.filter(content_type=type).delete()
        return CustomResponse({"message": "Details deleted successfully."}, status=status.HTTP_200_OK)

    
class CompanyNameView(viewsets.ViewSet):

    def create(self, request):
        user = Company.objects.all().values('id', 'name')
        return CustomResponse(user)
    

class ManageCompanyView(viewsets.ViewSet):
    """
        This view is of crud operations for manage company
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination
    
    def create(self, request):
        """
            method to create the company
        """
        data = request.data
        company_title = data.get("company_title")
        if not company_title:
            return CustomResponse({"message": "Please provide company name"}, status=status.HTTP_400_BAD_REQUEST)
        if Company.objects.filter(name=company_title).exists():
            return CustomResponse({"message": "this company name already registered"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            company = Company.objects.create(name=company_title)
            return CustomResponse({
                "message": "company added successfully",
                "company_id": company.id
        })
    
    def update(self, request):
        """
            method to update the company details.
        """
        data = request.data
        id = data.get("id")
        company_title = data.get("company_title")
        if not company_title:
            return CustomResponse({"message": "Please provide company name"}, status=status.HTTP_400_BAD_REQUEST)
        if Company.objects.filter(name=company_title).exists():
            return CustomResponse({"message": "this company name already registered"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            Company.objects.filter(id=id).update(name=company_title)
            return CustomResponse({"message": "company name updated"})

    def delete(self, request):
        """
            delete method to permanently delete the company.
        """
        id = request.GET.get('id')
        company = Company.objects.filter(id=id).first()
        if not company:
            return CustomResponse({"message": "company Does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        Company.objects.filter(id=id).delete()
        return CustomResponse({"message": "company Deleted successfully"})

    def search(self, request):
        """
            Method to list and search for the company.
        """
        company_name = request.GET.get('company_name', None)
        is_active = request.GET.get('is_active', None)
        page_size = request.GET.get('page_size', '')
        companies = Company.objects.annotate(num_users=Count('company')).values('id', 'name', 'num_users', 'is_active').order_by('-created_at')
        if company_name:
            companies = companies.filter(name__icontains=company_name)
        if is_active:
            if is_active == "true":
                companies = companies.filter(is_active=True)
            elif is_active == "false":
                companies = companies.filter(is_active=False)
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(companies, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(companies)
            
    def status(self, request):
        """
            method to change status for the company.
        """
        data = request.data
        id = data.get("id")
        status_value = data.get("status_value")
        company = Company.objects.filter(id=id).first()
        if not company:
            return CustomResponse({"message": "Company dont exist for this ID"}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 1:
            Company.objects.filter(id=id).update(is_active=True)
            return CustomResponse({"message": "Status Activated successfully"}, status=status.HTTP_200_OK)
        if status_value == 2:
            Company.objects.filter(id=id).update(is_active=False)
            return CustomResponse({"message": "Status deactivated successfully"}, status=status.HTTP_200_OK)


class ManageProjectViewSet(viewsets.ViewSet):

    """
        This view is of crud operations for manage Project
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def search(self, request):
        """
            method to search and list projects
        """
        name = request.GET.get('name', None)
        page_size = request.GET.get('page_size', '')

        projects = Project.objects.filter(is_admin_approved=True, is_marked_deleted=False).annotate(
            num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
        ).values('id', 'project_name', 'created_by__full_name', 'num_files').order_by("-created_at")

        if name:
            projects = projects.filter(project_name__icontains=name)

        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(projects, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(projects)   
    queryset = Project.objects.all()

    def retrieve(self, request, pk=None):  
        """
            method to retrieve project
        """
        project = get_object_or_404(self.queryset, pk=pk)
        serializer = ProjectDetailSerializer(project)

        return CustomResponse(serializer.data)
    
    def destroy(self, request, id):
        """
            method to delete project
        """
        try:
            instance = Project.objects.get(id=id)
            instance.is_marked_deleted=True
            instance.deleted_at = timezone.now()
            instance.save()
            return Response({'message': 'Project deleted successfully'}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({'message': 'Project not found'}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        """
            method to create project
        """
        data = request.data
        project_name = data.get("project_name")
        project_number = data.get("project_number")
        assigned_to = data.get("assigned_to", [])  # Default to an empty list if not provided

        # Validations
        if not project_name:
            return CustomResponse({"message": "Please provide project_name"}, status=status.HTTP_400_BAD_REQUEST)
        if not project_number:
            return CustomResponse({"message": "Please provide project_number"}, status=status.HTTP_400_BAD_REQUEST)
       
        if Project.objects.filter(project_name=project_name).exists():
            return CustomResponse({"message": "Project of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if Project.objects.filter(project_number=project_number).exists():
            return CustomResponse({"message": "Project Number already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # Create project without assigning users
        project = Project.objects.create(project_name=project_name, project_number=project_number, created_by_id=request.user.id,is_admin_approved=True)

        # Assign users to the project
        for email in assigned_to:
            user = User.objects.filter(email=email).first()
            if user:
                project.users.add(user)  
            print(email)

        return CustomResponse({"message": "Project created successfully", "project_id": project.id}, status=status.HTTP_200_OK)
    
    def file_create(self, request):
        """
            method to create file
        """
        data = request.data
        thumbnail = data.get("thumbnail")
        file_name = data.get("file_name")
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        manufacturer_name = data.get("manufacturer_name")
        manufacturing_number = data.get("manufacturing_number")
        project_id = data.get("project_id")
        location = data.get("location")
        quantity = data.get("quantity")
        project_details = data.get("project_details")
        recording = data.get('recording')
        additional_details = data.get("additional_details")
        location_points = data.get('location_points')

        if Files.objects.filter(manufacturing_number=manufacturing_number).exists():
             return CustomResponse({"message": "This manufacturing number already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if manual_manufacturer_name:
            new_user = User.objects.create(full_name=manual_manufacturer_name)
            print("newwwwww", new_user.id)
            file = Files.objects.create(manufacturer_name_id=new_user.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location,file_name=file_name, recording=recording, location_points=location_points,is_admin_approved=True)
            return CustomResponse({"message": "File Created with new user Successfully", "file_id": file.id})
        else:
            file = Files.objects.create(file_name=file_name, thumbnail=thumbnail, manufacturing_number=manufacturing_number, project_id=project_id, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location_points=location_points, is_admin_approved=True)
            return CustomResponse({"message": "File created successfully", "file_id": file.id})
    
    def un_approved_project_count(self, request):
        """
            method to get count of unapproved projects
        """
        projects = Project.objects.filter(is_admin_approved=False).count()
        return CustomResponse(projects)

    # def un_approved_project(self, request):
    #     unapproved_projects = Project.objects.filter(is_admin_approved=False).annotate(num_files=Count('project_files')).values('id','project_name', 'created_by__full_name', 'num_files','created_at')
    #     count = unapproved_projects.count()
    #     response_data = {
    #         "unapproved_projects": list(unapproved_projects),
    #         "count": count
    #     }
    #     return CustomResponse(response_data)

    # def approve_project(self, request):
    #     data = request.data
    #     project_id = data.get("project_id")
    #     project_name = data.get("project_name")
    #     project_number = data.get("project_number")
    #     assigned_to = data.get("assigned_to", [])
    #     status_value = data.get("status_value")

    #     # if status == 2:
    #     #     Project.objects.filter(id=project_id).delete()
    #     #     return CustomResponse({"message": "Project deleted"})
    #     if not Project.objects.filter(id=project_id).first():
    #         return CustomResponse({"message": "Project of this id dont exists"}, status=status.HTTP_400_BAD_REQUEST)
        
    #     if status_value == 2:
    #         Project.objects.filter(id=project_id).delete()
    #         return CustomResponse({"message": "Project deleted"}, status=status_code.HTTP_200_OK)
        
    #     if not project_name:
    #         return CustomResponse({"message": "Please provide project_name"}, status=status.HTTP_400_BAD_REQUEST)
    #     if not project_number:
    #         return CustomResponse({"message": "Please provide project_number"}, status=status.HTTP_400_BAD_REQUEST)
        
    #     # if status_value == 2:
    #     #     Project.objects.filter(id=project_id).delete()
    #     #     return CustomResponse({"message": "Project deleted"})
        
    #     if status_value == 1:
        
    #         if Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).exists():
    #             if assigned_to:
    #                 project = Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).first()
    #                 # user = User.objects.filter(email=assigned_to).first()
    #                 # project.users.add(user)
    #                 # project.is_admin_approved=True
    #                 # project.save()
    #                 for email in assigned_to:
    #                     user = User.objects.filter(email=email).first()
    #                     print(f"User for email {email}:", user)
    #                     if user:
    #                         project.users.add(user)
    #                         project.is_admin_approved = True
    #                         project.save() 
    #                 return CustomResponse({"message": "Project approved successfully"})
    #             else:
    #                 project=Project.objects.filter(id=project_id).first()
    #                 project.is_admin_approved = True
    #                 project.save()
    #                 return CustomResponse({"message": "Project approved successfully"})

    #         else:
    #             if Project.objects.filter(project_name=project_name).exclude(id=project_id).exists():
    #                 return CustomResponse({"message": "Project of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
    #             elif Project.objects.filter(project_number=project_number).exclude(id=project_id).exists():
    #                 return CustomResponse({"message": "Project Number of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
    #             else:
    #                 if assigned_to:
    #                     project = Project.objects.filter(id=project_id).update(project_name=project_name, project_number=project_number)
    #                     project = Project.objects.filter(id=project_id).first()
    #                     # user = User.objects.filter(email=assigned_to).first()
    #                     # project.users.add(user)
    #                     # project.is_admin_approved=True
    #                     # project.save()
    #                     for email in assigned_to:
    #                         user = User.objects.filter(email=email).first()
    #                         if user:
    #                             project.users.add(user)
    #                             project.is_admin_approved = True
    #                             project.save()
    #                     return CustomResponse({"message": "Project approved successfully"})
    #                 else:
    #                     project=Project.objects.filter(id=project_id).update(project_name=project_name, project_number=project_number)
    #                     project=Project.objects.filter(id=project_id).first()
    #                     project.is_admin_approved = True
    #                     project.save()
    #                     return CustomResponse({"message": "Project approved successfully"})

    def approve_project(self, request):
        """
            method to approve projects
        """
        data = request.data
        project_id = data.get("project_id")
        project_name = data.get("project_name")
        project_number = data.get("project_number")
        assigned_to = data.get("assigned_to", [])
        status_value = data.get("status_value")

        if not Project.objects.filter(id=project_id).first():
            return CustomResponse({"message": "Project of this id don't exists"}, status=status.HTTP_400_BAD_REQUEST)

        if status_value == 2:
            Project.objects.filter(id=project_id).delete()
            return CustomResponse({"message": "Project deleted"}, status=status_code.HTTP_200_OK)

        if not project_name:
            return CustomResponse({"message": "Please provide project_name"}, status=status.HTTP_400_BAD_REQUEST)
        if not project_number:
            return CustomResponse({"message": "Please provide project_number"}, status=status.HTTP_400_BAD_REQUEST)

        if status_value == 1:
            if Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).exists():
                if assigned_to:
                    project = Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).first()
                    for email in assigned_to:
                        user = User.objects.filter(email=email).first()
                        if user:
                            project.users.add(user)
                            project.is_admin_approved = True
                            project.save()

                            # Push Notification to users who created the project
                            title = f"Project Approved by Admin"
                            message = f"Hello!! Your project '{project_name}' has been approved by Admin."
                            data = {
                                "title": title,
                                "message": message,
                            }

                            notifyer = user
                            if notifyer.is_notification_enabled == True:
                                notification = UserNotification.objects.create(user=user, title=title, message=message)
                                notification.save()
                                data.update({"notification_id": str(notification.id)})

                                send_notification_bulk(
                                    user_ids=[user.id], title=title, message=message, data=data)

                    return CustomResponse({"message": "Project approved successfully"})
                else:
                    project = Project.objects.filter(id=project_id).first()
                    project.is_admin_approved = True
                    project.save()

                    # Push Notification to users who created the project
                    title = f"Project Approved by Admin"
                    message = f"Hello!! Your project '{project_name}' has been approved by Admin."
                    data = {
                        "title": title,
                        "message": message,
                    }

                    notifyer = project.created_by
                    if notifyer.is_notification_enabled == True:
                        notification = UserNotification.objects.create(user=notifyer, title=title, message=message)
                        notification.save()
                        data.update({"notification_id": str(notification.id)})

                        send_notification_bulk(
                            user_ids=[notifyer.id], title=title, message=message, data=data)

                    return CustomResponse({"message": "Project approved successfully"})
            else:
                if Project.objects.filter(project_name=project_name).exclude(id=project_id).exists():
                    return CustomResponse({"message": "Project of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
                elif Project.objects.filter(project_number=project_number).exclude(id=project_id).exists():
                    return CustomResponse({"message": "Project Number of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    if assigned_to:
                        project = Project.objects.filter(id=project_id).update(project_name=project_name, project_number=project_number)
                        project = Project.objects.filter(id=project_id).first()
                        for email in assigned_to:
                            user = User.objects.filter(email=email).first()
                            if user:
                                project.users.add(user)
                                project.is_admin_approved = True
                                project.save()
                                # Push Notification to users who created the project
                                title = f"Admin Assigned you a Project"
                                message = f"Hello!! Admin Assigned you a project named '{project_name}'."
                                data = {
                                    "title": title,
                                    "message": message,
                                }

                                # notifyer = user
                                # if notifyer.is_notification_enabled == True:
                                notification = UserNotification.objects.create(user=user, title=title, message=message)
                                notification.save()
                                data.update({"notification_id": str(notification.id)})

                                send_notification_bulk(
                                    user_ids=[user.id], title=title, message=message, data=data)
                        return CustomResponse({"message": "Project approved successfully"})
                    else:
                        log.info("comes")
                        project=Project.objects.filter(id=project_id).update(project_name=project_name, project_number=project_number)
                        project=Project.objects.filter(id=project_id).first()
                        project.is_admin_approved = True
                        created_by_id = project.created_by
                        project.save()
                        # Push Notification to users who created the project
                        title = f"Project Approved by Admin"
                        message = f"Hello!! Your project '{project_name}' has been approved by Admin."
                        data = {
                            "title": title,
                            "message": message,
                        }

                        # notifyer = user
                        # if notifyer.is_notification_enabled == True:
                        c = Project.objects.filter(id=project_id).first()
                        print("c===", c.created_by.id)
                        notifyer = User.objects.filter(id=c.created_by.id).first()
                        notification = UserNotification.objects.create(user=created_by_id, title=title, message=message)
                        log.info("notification")
                        log.info(notification)
                        notification.save()
                        data.update({"notification_id": str(notification.id)})
                        log.info("Data")
                        log.info(data)
                        print("aaaaaaaa", notifyer.is_notification_enabled)
                        if notifyer.is_notification_enabled == True:
                            send_notification_bulk(
                                user_ids=[created_by_id.id], title=title, message=message, data=data)
                        return CustomResponse({"message": "Project approved successfully"})                        

    def un_approved_file(self, request, id):
        """
            method to get unapproved files  list
        """
        page_size = request.GET.get('page_size', '')        
        files = Files.objects.filter(project_id=id, is_admin_approved=False).all().values('file_name', 'id', 'thumbnail', 'created_at')        
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(files)

    def un_approved_project(self, request):
        """
            methof to get list of unapproved projects
        """
        page_size = request.GET.get('page_size', '')
        projects = Project.objects.filter(is_admin_approved=False).annotate(num_files=Count('project_files')).values('id', 'project_name', 'created_by__full_name', 'num_files','created_at').order_by('-created_at')
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(projects, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(projects)
    
    def un_approved_files_count(self, request, id):
        """
            method to get count of unapproved files
        """
        file = Files.objects.filter(project_id=id, is_admin_approved=False).count()
        return CustomResponse(file)
    
    def view_file(self, request, id):
        """
            method to retrieve file
        """
        file = Files.objects.filter(id=id)
        if not file.exists():
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        serialized_file = FilesPointSerializer(file, many=True).data
        return CustomResponse(serialized_file)
    
    def destroy_file(self, request, id):
        """
            method to delete file
        """
        file = Files.objects.filter(id=id).first()
        if not file:
            return CustomResponse({"message": "File not found"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            file.is_marked_deleted=True
            file.deleted_at = timezone.now()
            file.save()
            return CustomResponse({"message": "File deleted successfully"}, status=status.HTTP_200_OK)
        
    def update_file(self, request, *args, **kwargs):
        """
            method to update file
        """
        queryset = Files.objects.all()
        pk = self.kwargs.get('pk')
        instance = queryset.filter(pk=pk).first()
        if instance is None:
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = FilesSerializer(instance, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            response_data = {
                "message": "File updated successfully",
                "data": serializer.data
            }
            return CustomResponse(response_data, status=status.HTTP_200_OK)
        else:
            return CustomResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def approve_file(self, request):
        """
            method to approve files
        """
        data = request.data
        id = data.get("id")
        status_value = data.get("status_value")
        file = Files.objects.filter(id=id).first()
        if not file:
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 2:
            file.delete()
            return CustomResponse({"message": "File deleted successfully"}, status=status_code.HTTP_200_OK)
        else:
            file.is_admin_approved = True
            file.save()
            # Push Notification
            title = f"File Approved by Admin"
            message = f"Hello!! Your file has been approved by Admin."
            data = {
                "title": title,
                "message": message,
            }
            print("createddddd", file.created_by, file.created_by.id)
            notifyer = User.objects.filter(id=file.created_by.id).first()
            notification = UserNotification.objects.create(user_id=file.created_by.id,title=title,message=message)
            print("createddddd2", file.created_by, file.created_by.id)
            notification.save()
            data.update({"notification_id": str(notification.id)})
            if notifyer.is_notification_enabled==True:
                send_notification_bulk(
                    user_ids=[file.created_by.id], title=title, message=message, data=data)
                print("createddddd3", file.created_by, file.created_by.id)
            return CustomResponse({"message": "File approved by the admin"}, status=status_code.HTTP_200_OK)
        
    def delete_file_list(self, request, id):
        """
            method to get the list of deleted files
        """
        file = Files.objects.filter(project_id=id, is_marked_deleted=True).all().values("id", "file_name")
        return CustomResponse(file)
    
    def delete_file_admin(self, request):
        """
            method to delete file by admin
        """
        data = request.data
        id = data.get("id")
        status_value = data.get("status_value")
        file = Files.objects.filter(id=id).first()
        if not file:
            return CustomResponse({"message": "File dont exist"}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 1:
            file.delete()
            return CustomResponse({"message": "File deleted successfully"}, status=status_code.HTTP_200_OK)
        else:
            file.is_marked_deleted = False
            file.save()
            return CustomResponse({"message": "File delete denied by admin"}, status=status_code.HTTP_200_OK)
    
    def view_file_unapproved(self, request, id):
        """
            method to view unapproved files
        """
        file = Files.objects.filter(id=id)
        if not file.exists():
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        serialized_file = FilesPointSerializer(file, many=True).data
        return CustomResponse(serialized_file)   
        
    @action(detail=True, methods=['get'])
    def save_to_csv(self, request, pk=None):
        """
            method to export csv
        """
        # Retrieve the serialized data
        queryset = Project.objects.all()
        project = get_object_or_404(queryset, pk=pk)
        serializer = ProjectDetailSerializer(project)
        project_data = serializer.data
        files_data = project_data.pop('files')
        all_data = []
        for file_data in files_data:
            combined_data = {**project_data, **file_data}
            all_data.append(combined_data) 
        df = pd.DataFrame(all_data)
        # Create a directory to store the CSV temporarily
        export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        csv_path = os.path.join(export_dir, f'project_detail_{pk}.csv')
        df.to_csv(csv_path, index=False)
        # Upload the CSV to AWS S3
        s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
        file_name = f'project_detail_{pk}.csv'
        path_key = f"csv/{uuid.uuid4()}_{file_name}"
        try:
            with open(csv_path, 'rb') as csv_file:
                s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(csv_file, path_key)
            # After successful upload, delete local CSV (optional)
            os.remove(csv_path)
        except Exception:
            return CustomResponse({"message": "Something went wrong during file uploading."},
                                  status=status_code.HTTP_400_BAD_REQUEST)
        created_url = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{path_key}'
        return CustomResponse({"file_path": created_url})
    

class ManageSubadminViewSet(viewsets.ViewSet):
    """
        ManageSubadminViewSet to manage Subadmins
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def search(self, request):
        """
            method for list and search subadmin
        """
        query = request.GET.get('query', None)
        is_active = request.GET.get('is_active', None)
        page_size = request.GET.get('page_size', '')
        users_query = User.all_objects.filter(user_role=3).values('id', 'full_name', 'email', 'is_active', 'phone_number', 'modules_accessible').order_by("-created_at")
        if query:
            users_query = users_query.filter(full_name__icontains=query)
        if is_active:
            if is_active == "true":
                users_query = users_query.filter(is_active=True)
            elif is_active == "false":
                users_query = users_query.filter(is_active=False)    
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(users_query, request)    
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        data = {
            "users": users_query
        }
        return CustomResponse(data)
    
    def retrieve(self, request, id):
        """
            function to retrieve subadmin
        """
        sub_admin=User.all_objects.filter(id=id, user_role=3).all().values('full_name', 'email', 'phone_number', 'created_at', 'modules_accessible')
        if not sub_admin:
            return CustomResponse({"Message": "Subadmin not found."}, status=status.HTTP_400_BAD_REQUEST)
        return CustomResponse(sub_admin, status=status.HTTP_200_OK)
    
    def subadmin_status(self, request):
        """
            function to change status for the Subadmin.
        """
        data = request.data
        id = data.get("id")
        status_value = data.get("status_value")
        sub_admin = User.all_objects.filter(id=id, user_role=3).first()
        if not sub_admin:
            return CustomResponse({"message": "This subadmin does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 1:
            User.all_objects.filter(id=id, user_role=3).update(is_active=True)
            return CustomResponse({"message": "Subadmin Activated successfully"}, status=status.HTTP_200_OK)
        if status_value == 2:
            User.all_objects.filter(id=id, user_role=3).update(is_active=False)
            Token.objects.filter(user=sub_admin).delete()
            return CustomResponse({"message": "Subadmin deactivated successfully"}, status=status.HTTP_200_OK)

    def create(self, request):
        """
            function to create subadmin
        """
        data = request.data
        full_name = data.get('full_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        temporary_password = data.get('temporary_password')
        modules_accessible = data.get("modules_accessible", [])

        if not full_name:
            return CustomResponse({"message": "Full Name is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not email:
            return CustomResponse({"message": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not phone_number or len(str(phone_number)) < 8:
            return CustomResponse({"message": "Minimum 8 digits of Phone Number required"}, status=status.HTTP_400_BAD_REQUEST)
        if not temporary_password:
            return CustomResponse({"message": "Temporary Password is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not modules_accessible or len(modules_accessible)==0:
            return CustomResponse({"message": "Please add modules accessible"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return CustomResponse({"message": "Email Already Exists"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone_number=phone_number).exists():
            return CustomResponse({"message": "Phone Number Already Exists"}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            sub_admin = User.objects.create(full_name=full_name, email=email.lower(), phone_number=phone_number, user_role=3, is_admin_approved=True, is_email_verified=True)
            sub_admin.set_password(temporary_password)
            sub_admin.save()
            c = sub_admin.id
            d = User.objects.filter(id=c).first()
            if d.modules_accessible is None:
                d.modules_accessible = []
            for x in modules_accessible:            
                d.modules_accessible.append(x)
            d.save()
            send_subadmin_credentials(email, temporary_password)
            return CustomResponse({"message": "Subadmin created Successfully", "id":d.id}, status=status.HTTP_200_OK)
        
    def edit_subadmin(self, request, id):
        """
            function to edit details of subadmin
        """
        data = request.data
        full_name = data.get('full_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        modules_accessible = data.get("modules_accessible", [])

        c = User.objects.filter(id=id).first()

        if email:
            if User.objects.filter(email=email).exclude(id=c.id).exists():
                return CustomResponse({"message": "Email Already Exists"}, status=status.HTTP_400_BAD_REQUEST)

        sub_admin = User.all_objects.filter(id=id, user_role=3).first()
        if not sub_admin:
            return CustomResponse({"message": "Subadmin not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if phone_number and len(phone_number) < 8:
            return CustomResponse({"message": "Minimum 8 digits of Phone Number required"}, status=status.HTTP_400_BAD_REQUEST)
            
        # send_updated_subadmin_credentials(sub_admin.email)
        old_cred = User.all_objects.filter(id=id, user_role=3).first()
        old_email = old_cred.email
        if full_name:
            sub_admin.full_name = full_name
        if email:
            sub_admin.email = email.lower()
        if phone_number:
            sub_admin.phone_number = phone_number
        if modules_accessible:
            sub_admin.modules_accessible = modules_accessible

        sub_admin.save()
        if full_name or email or phone_number or modules_accessible:
            print("oldemail===",old_email)
            send_updated_subadmin_credentials(old_email, email)
            print("old2", old_email)
        return CustomResponse({"message": "Subadmin details updated successfully"}, status=status.HTTP_200_OK)
    
    def update(self, request):
        """
            function to delete the subadmin
        """
        data = request.data
        user_id = data.get('user_id')
        sub_admin = User.all_objects.filter(id=user_id, user_role=3).first()
        if not sub_admin:
            return CustomResponse({"message": "Subadmin not found."}, status=status_code.HTTP_404_NOT_FOUND)
        subadmin_deleted(sub_admin.email)
        sub_admin.is_deleted = True
        sub_admin.save()
        Token.objects.filter(user=sub_admin).delete()            
        return CustomResponse({"message": "Subadmin Deleted Successfully."}, status=status_code.HTTP_200_OK)

        
class DashBoardViewSet(viewsets.ViewSet):
    """
        This view is of Dashboard
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def get(self, request, *args, **kwargs):
        month = self.request.query_params.get('month', None)
        year = self.request.query_params.get('year', None)

        filters = {}
        if month:
            filters['created_at__month'] = int(month)
        if year:
            filters['created_at__year'] = int(year)

        total_users = User.all_objects.filter(is_admin_approved=True, is_email_verified=True, user_role=User.USER, **filters).count()
        total_subadmins = User.all_objects.filter(user_role=User.SUB_ADMIN, **filters).count()
        total_projects = Project.objects.filter(**filters).count()
        total_companies = Company.objects.filter(**filters).count()

        data = {
            'total_users': total_users,
            'total_subadmins': total_subadmins,
            'total_projects': total_projects,
            'total_companies': total_companies
        }

        return CustomResponse(data)


class UseremailViewSet(viewsets.ViewSet):
    """
        UseremailViewSet to give listing of users email
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def get(self, request, *args, **kwargs):
        search_query = request.query_params.get('search', None)        
        users_query = User.objects.filter(user_role=2)        
        if search_query:
            users_query = users_query.filter(email__icontains=search_query)        
        users = users_query.values('id', 'email')        
        return CustomResponse(users)

        
class AdminNameViewset(viewsets.ViewSet):
    """
        AdminNameViewset to give the name of Loggedin Admin
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def get(self, request, *args, **kwargs):
        name = User.objects.filter(id=request.user.id).all().values('id', 'full_name')
        return CustomResponse(name)              
     

#Manage Users

class  ManageUserAdminViewSet(viewsets.ViewSet):
    """
        UserListAdminViewSet to Manage Users
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def list(self, request):
        """
            function to get the list of users
        """
        name = request.GET.get('name', '')
        page_size = request.GET.get('page_size', '')
        is_active = request.GET.get('is_active', None)
        users = (
            User.all_objects.filter(is_admin_approved=True,user_role=2, full_name__icontains=name).annotate(
                approved_project_count=Count(
                    'created_by_project',
                    filter=Q(created_by_project__is_admin_approved=True),
                    distinct=True
                ),
                assigned_project_count=Count(
                    'assigned_projects__id',
                     filter=Q(assigned_projects__is_admin_approved=True),  
                    distinct=True
                )
            ).annotate(
                total_project_count=ExpressionWrapper(
                    F('approved_project_count') + F('assigned_project_count'),
                    output_field=IntegerField()
                )
            ).values('id','full_name','email', 'assigned_project_count', 'user_company', 'user_company__company__name', 'is_active').order_by("-created_at")
        )

        if is_active:
            if is_active == "true":
                users = users.filter(is_active=True)
            elif is_active == "false":
                users = users.filter(is_active=False)
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(users, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(users, status=status_code.HTTP_200_OK)  
    
    def change_status(self, request):
        """
            function to change the status of users
        """
        data = request.data
        user_id = data.get('user_id')
        status_value = data.get('status_value')
        user = User.all_objects.filter(id=user_id).first()
        if not user:
            return CustomResponse({"message": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 1:
            User.all_objects.filter(id=user_id).update(is_active=True)
            return CustomResponse({"message": "User Activated Successfully"}, status=status_code.HTTP_200_OK)
        if status_value == 2:
            User.all_objects.filter(id=user_id).update(is_active=False)
            try:
                token = Token.objects.get(user=user)
                token.delete()
            except Token.DoesNotExist:
                pass
            return CustomResponse({"message": "User Deactivated Successfully"}, status=status_code.HTTP_200_OK)

    
    def retrieve(self, request, id):
        """
            function to retrieve a particular user using user id
        """
        approved_projects = Project.objects.filter(users__id=id, is_admin_approved=True, is_marked_deleted=False)
        prefetch = Prefetch('assigned_projects', queryset=approved_projects)
        user = get_object_or_404(User.all_objects.prefetch_related(prefetch).filter(id=id))
        serializer = UserDetailSerializer(user)
        return CustomResponse(serializer.data)
            
    def unapproved_users(self, request):
        """
            function to get the list of unapproved users
        """
        page_size = request.GET.get('page_size', '')
        # edit_request = request.GET.get('edit_request', None)
        # user = User.objects.filter(is_admin_approved=False, is_email_verified=True, user_role=2).all().values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name').exclude(email=None).distinct('id')
        # user = user.order_by('-created_at')
        # print("edit request", edit_request)
        # print("edit 2")
        user = (
                User.objects
                .filter(is_admin_approved=False, is_email_verified=True, user_role=2)
                .exclude(email=None)
                .order_by('-id', '-created_at')
                .distinct('id')
                .values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name')
            )
        # print("edit3")
        # if edit_request=='1':
        #     print("edit4")
        #     user = (
        #         User.objects
        #         .filter(is_admin_approved=False, is_email_verified=True, user_role=2)
        #         .exclude(email=None)
        #         .order_by('-id', '-created_at')
        #         .distinct('id')
        #         .values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name')
        #     )

        # if edit_request=='2':
        #     print("edit5")
        #     user = (
        #         User.objects
        #         .filter(is_edited=True, is_email_verified=True, user_role=2)
        #         .exclude(email=None)
        #         .order_by('-id', '-created_at')
        #         .distinct('id')
        #         .values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name')
        #     )

        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(user, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(user, status=status_code.HTTP_200_OK)
    
    def unapproved_users_count(self, request):
        """
            function to give count og unapproved users
        """
        user = User.objects.filter(is_admin_approved=False,user_role=2, is_email_verified=True).count()
        return CustomResponse(user)
    
    def approve_users(self, request):
        """
            function to approve the users
        """
        data = request.data
        user_id = data.get("user_id")
        status_value = data.get("status_value")
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse({"message": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 2:
            user.delete()
            return CustomResponse({"message": "User Denied Successfully"}, status=status_code.HTTP_200_OK)
        elif status_value == 1:
            user.is_admin_approved = True
            user.save()
            # Push Notification
            title = f"Account Approved by Admin"
            message = f"Hello!! Your Account has been Approved by Admin, Now you can Login."
            data = {
                "title": title,
                "message": message,
            }
            notification = UserNotification.objects.create(user_id=user_id,title=title,message=message)
            notification.save()
            data.update({"notification_id": str(notification.id)})

            send_notification_bulk(
                user_ids=[user_id], title=title, message=message, data=data)
            return CustomResponse({"message": "User Approved by Admin"}, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse({"message": "Please give right value in status value"},status=status.HTTP_400_BAD_REQUEST)

    def project_list(self, request, id):
        """
            function to list and search the projects of a particular user.
        """
        page_size = request.GET.get('page_size', '')
        user = User.all_objects.filter(id=id).first()
        if not user:
            return CustomResponse({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
        projects = Project.objects.filter(users__id=id, is_admin_approved=True, is_marked_deleted=False).values("id","project_name", "created_at")
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(projects, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(projects)
    
    queryset = Project.objects.all()
    def retrieve_user_project(self, request, pk=None): 
        """
            function to retrieve users project
        """ 
        project = get_object_or_404(self.queryset, pk=pk)
        serializer = ProjectDetailSerializer(project)

        return CustomResponse(serializer.data)

    def delete_user_admin(self, request,id):
        """
            function to delete a user
        """
        user = User.all_objects.filter(id=id).first()
        if not user:
            return CustomResponse({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)
        user.is_deleted=True
        user.save()
        Token.objects.filter(user=user).delete()
        return CustomResponse({"message": "User deleted sucessfully by Admin"}, status=status_code.HTTP_200_OK)

    def view_file_admin(self, request, id):
        """
            function to view file of a user
        """
        file = Files.objects.filter(id=id)
        if not file.exists():
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        serialized_file = FilesPointSerializer(file, many=True).data
        return CustomResponse(serialized_file)
    
    def delete_file_user(self, request,id):
        """
            Function to delete file of a user
        """        
        file = Files.objects.filter(id=id).first()
        if not file:
            return CustomResponse({"message": "File dont exist"}, status=status.HTTP_400_BAD_REQUEST)
        
        file.delete()
        return CustomResponse({"message": "File deleted successfully"})

    @action(detail=True, methods=['get'])
    def admin_user_csv(self, request, pk=None):
        """
            function to export csv
        """
        # Retrieve the serialized data
        queryset = Project.objects.all()
        project = get_object_or_404(queryset, pk=pk)
        serializer = ProjectDetailSerializer(project)
        project_data = serializer.data
        files_data = project_data.pop('files')
        all_data = []
        for file_data in files_data:
            combined_data = {**project_data, **file_data}
            all_data.append(combined_data) 
        df = pd.DataFrame(all_data)
        # Create a directory to store the CSV temporarily
        export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        csv_path = os.path.join(export_dir, f'project_detail_{pk}.csv')
        df.to_csv(csv_path, index=False)
        # Upload the CSV to AWS S3
        s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
        file_name = f'project_detail_{pk}.csv'
        path_key = f"csv/{uuid.uuid4()}_{file_name}"
        try:
            with open(csv_path, 'rb') as csv_file:
                s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(csv_file, path_key)
            # After successful upload, delete local CSV (optional)
            os.remove(csv_path)
        except Exception:
            return CustomResponse({"message": "Something went wrong during file uploading."},
                                  status=status_code.HTTP_400_BAD_REQUEST)
        created_url = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{path_key}'
        return CustomResponse({"file_path": created_url})
    
    def get_queryset(self):
        pk = self.kwargs.get('pk')
        return Files.objects.filter(id=pk)
    
    def update_file_admin(self, request, pk=None):
        """
            update method to update the file details.
        """
        queryset = self.get_queryset()
        obj = queryset.get(pk=pk)
        serializer = CreateFileDetailsSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse({"message": "File updated sucessfully"}, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse(serializer.errors, status=status_code.HTTP_200_OK)
    
    def remove_user_from_project(self, request):
        """
            function to remove user from a project
        """
        user_id = request.query_params.get('user_id')
        project_id = request.query_params.get('project_id')
        try:
            
            project = Project.objects.get(id=project_id)
            user = User.all_objects.get(id=user_id)
            project.users.remove(user)
            return CustomResponse(f"User {user} removed from project {project}")
        except Project.DoesNotExist:
            return CustomResponse("Project not found!")
        except User.DoesNotExist:
            return CustomResponse("User not found!")    

    def project_graph(self, request, id):
        """
            function to give graph of users project
        """
        year = request.GET.get('year')
        month = request.GET.get('month')
        selected_project_id = request.GET.get('project_id', None)
        
        user = User.all_objects.filter(id=id).first()
        if not user:
            return CustomResponse({"message": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

        file_query = Files.objects.filter(project__users__id=id)
        if selected_project_id:
            file_query = file_query.filter(project_id=selected_project_id)

        if year and not month:
            # If a year is given but no month, show counts for each month of the year
            start_date = date(int(year), 1, 1)
            end_date = date(int(year), 12, 31)
            
            monthly_files_count = (file_query.filter(created_at__range=[start_date, end_date])
                                .annotate(month=TruncMonth('created_at'))
                                .values('month')
                                .annotate(files_count=Count('id'))
                                .order_by('month'))
            
            # Fill in months with zero count
            result = []
            for m in range(1, 13):
                dt = date(int(year), m, 1)
                count = next((item for item in monthly_files_count if item['month'].month == m), None)
                result.append({'month': dt, 'files_count': count['files_count'] if count else 0})
            
            return CustomResponse(result)
        
        elif month and year:
            # If both year and month are given, show counts for each day of the month
            last_day = monthrange(int(year), int(month))[1]
            start_date = date(int(year), int(month), 1)
            end_date = date(int(year), int(month), last_day)
            
            daily_files_count = (file_query.filter(created_at__range=[start_date, end_date])
                                .annotate(day=TruncDate('created_at'))
                                .values('day')
                                .annotate(files_count=Count('id'))
                                .order_by('day'))
            
            # Fill in days with zero count
            result = []
            current_day = start_date
            while current_day <= end_date:
                count = next((item for item in daily_files_count if item['day'] == current_day), None)
                result.append({'day': current_day, 'files_count': count['files_count'] if count else 0})
                current_day += timedelta(days=1)
            
            return CustomResponse(result)
        
        else:
            # Original code for when neither year nor month is specified
            monthly_files_count = (file_query
                                .annotate(month=TruncMonth('created_at'))
                                .values('month')
                                .annotate(files_count=Count('id')))
            
            return CustomResponse(monthly_files_count)

                

# CR Points

class DeletedProjectsViewSet(viewsets.ViewSet):
    """
        DeletedProjectsViewSet to get the list and restore deleted projects
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def list(self, request):
        """
            function to give list of deleted Projects
        """
        page_size = request.GET.get('page_size', '')
        projects = Project.objects.filter(is_marked_deleted=True).annotate(
            num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
        ).values('id', 'project_name', 'created_by__full_name', 'num_files', 'deleted_at').order_by("-created_at")
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(projects, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(projects)   

    def restore(self, request, id):
        """
            function to restore deleted projects
        """
        project = Project.objects.filter(id=id).first()
        if not project:
            return CustomResponse({"Message": "Project Not Found"}, status=status_code.HTTP_400_BAD_REQUEST)
        # Restore project
        Project.objects.filter(id=id).update(is_marked_deleted=False)
        # Restore associated files
        Files.objects.filter(project=project, is_marked_deleted=True).update(is_marked_deleted=False)
        return CustomResponse({"Message": "Project and associated files restored successfully"}, status=status_code.HTTP_200_OK)
    

class DeletedFilesViewSet(viewsets.ViewSet):
    """
        DeletedFilesViewSet to get the list and restore deleted files
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def list(self, request, id):
        """
            function to give list of deleted files
        """
        page_size = request.GET.get('page_size', '')
        files = Files.objects.filter(project_id=id, is_deleted=True).values('id', 'file_name', 'deleted_at').order_by("-created_at")
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(files)   

    def restore(self, request):
        """
            function to restore deleted files
        """
        # files = Files.objects.filter(id=id).first()
        data = request.data
        file_id = data.get("file_id", [])
        if not file_id:
                return CustomResponse({"message": "Please select file"}, status=status_code.HTTP_400_BAD_REQUEST)
        for i in file_id:
            print("i",i)        
            Files.objects.filter(id=i).update(is_deleted=False, is_admin_approved=True , submitted_to_admin=True, is_edited=False, disapproved_count=0)
        return CustomResponse({"Message": "File Restored Successfully"}, status=status_code.HTTP_200_OK)


class EditUserCompanyViewSet(viewsets.ViewSet):
    """
        EditUserCompanyViewSet to edit the company of user while approving
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)

    def approve_user(self, request):
        """
            Function to approve the users
        """
        data = request.data
        user_id = data.get("user_id")
        status_value = data.get("status_value")
        new_company = data.get("new_company")

        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse({"message": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        if status_value == 2:
            user.delete()
            return CustomResponse({"message": "User Denied Successfully"}, status=status_code.HTTP_200_OK)
        elif status_value == 1:
            user.is_admin_approved = True
            user.save()
            
            c = User.objects.filter(id=user_id).first()
            if c.company_name!=None:
                e = Company.objects.filter(name=c.company_name).exists()
                if e:
                    f = Company.objects.filter(name=c.company_name).first()
                    UserCompany.objects.filter(user_id=user_id).update(company_id=f.id)
                else:
                    if new_company==None:
                        d = Company.objects.create(name=c.company_name)
                    if UserCompany.objects.filter(user_id=user_id).exists():
                        UserCompany.objects.filter(user_id=user_id).update(company_id=d.id)
                    # else:
                    #     UserCompany.objects.create(user_id=user_id, company_id=d.id)
                    #     c.company_name=None
                    #     c.save()

            if new_company:
                if not Company.objects.filter(name=new_company).exists():
                    created_company = Company.objects.create(name = new_company)
                    UserCompany.objects.filter(user_id=user_id).update(company_id=created_company.id)
                else:
                    c = Company.objects.filter(name=new_company).first()
                    UserCompany.objects.filter(user_id=user_id).update(company_id=c.id)
            
            # Push Notification
            title = f"Account Approved by Admin"
            message = f"Hello!! Your Account has been Approved by Admin, Now you can Login."
            data = {
                "title": title,
                "message": message,
            }
            notification = UserNotification.objects.create(user_id=user_id, title=title, message=message)
            notification.save()
            data.update({"notification_id": str(notification.id)})

            send_notification_bulk(
                user_ids=[user_id], title=title, message=message, data=data)
            return CustomResponse({"message": "User Approved by Admin"}, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse({"message": "Please give the right value in status value"}, status=status.HTTP_400_BAD_REQUEST)       

                
class DeactivateCompanyViewSet(viewsets.ViewSet):
    """
        DeactivateCompanyViewSet to logout users if a company is deactivated
    """    
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)        
    def update(self, request):
        """
            function to deactivate the status of a company
        """
        data = request.data
        id = data.get("id")
        status_value = data.get("status_value")
        company = Company.objects.filter(id=id).first()
        if not company:
            return CustomResponse({"message": "Company dont exist for this ID"}, status=status.HTTP_400_BAD_REQUEST)
        # Get all users associated with the company
        users_to_logout = UserCompany.objects.filter(company=company).all().values_list('user_id', flat=True)
        list = []
        for i in range(0,len(users_to_logout)):
            user = User.objects.filter(id=users_to_logout[i]).first()
            list.append(user)
        if status_value == 1:
            Company.objects.filter(id=id).update(is_active=True)
            return CustomResponse({"message": "Status Activated successfully"}, status=status.HTTP_200_OK)
        if status_value == 2:
            # Deactivate the company
            Company.objects.filter(id=id).update(is_active=False)
            # Force logout all associated users
            if UserCompany.objects.filter(company_id=id).count()==0:
                return CustomResponse({"message": "Status deactivated successfully."}, status=status.HTTP_200_OK)
            list1=[]
            if None in list:
                list1=[]
                for i in range(0,len(list)):
                    if list[i]!=None:
                        list1.append(list[i])
            if len(list1)!=0:
                for user in list1:
                    Token.objects.filter(user=user).delete()
                    logged_out_users(user.email)
                return CustomResponse({"message": "Status deactivated successfully. Users associated with this company have been logged out."}, status=status.HTTP_200_OK)
            else:
                for user in list:
                    Token.objects.filter(user=user).delete()
                    logged_out_users(user.email)
                return CustomResponse({"message": "Status deactivated successfully. Users associated with this company have been logged out."}, status=status.HTTP_200_OK)




class UserListingViewSet(viewsets.ViewSet):
    """
       UserListingViewSet for getting the list of users 
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)

    def list(self, request):
        name = request.GET.get('name')
        if name is not None:
            users = User.objects.filter(is_admin_approved=True, full_name__icontains=name).all()
        else:
            users = User.objects.filter(is_admin_approved=True).all()
        serializer = UserListingSerializer(users, many=True)
        return CustomResponse(serializer.data, status=status_code.HTTP_200_OK)
            
   
class TotalUserCountViewSet(viewsets.ViewSet):
    def list(self, request):
        total_users = User.all_objects.filter(user_role=User.USER).count()
        total_deleted_users = User.all_delete_objects.filter(user_role=User.USER).count()
        total_active_users = User.objects.filter(user_role=User.USER).count()
        total_deactivated_users = User.all_objects.filter(is_active=False,user_role=User.USER).count()
        approved_users = User.all_objects.filter(is_admin_approved=True,user_role=2).count()
        active_unapproved_users = User.all_objects.filter(is_admin_approved=False,user_role=2, is_active=True).count()
        inactive_unapproved_users = User.all_objects.filter(is_admin_approved=False,user_role=2, is_active=True, is_email_verified=True).count()
        unverified_unapproved_users = User.all_objects.filter(is_admin_approved=False,user_role=2, is_active=True, is_email_verified=False).count()
        data = {
            "total_users":total_users,
            "total_deleted_users":total_deleted_users,
            "total_active_users":total_active_users,
            "total_deactivated_users":total_deactivated_users,
            "approved_users":approved_users,
            "active_unapproved_users":active_unapproved_users,
            "inactive_unapproved_users":inactive_unapproved_users,
            "unverified_unapproved_users":unverified_unapproved_users

        }
        return CustomResponse(data)
    

#CR 2 Points

class ApprovedFilesListingViewSet(viewsets.ViewSet):
    """
        ApprovedFilesListingViewSet to get the listing of approved files
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def approved_files_list(self, request, id):
        """
            function to get list of approved files
        """
        page_size = request.GET.get('page_size', '')
        approved_files = Files.objects.filter(project_id=id, is_edited=False, is_deleted=False, submitted_to_admin=True).all().values('id','file_name', 'thumbnail','created_at','is_file_disapproved').order_by('-created_at')
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(approved_files, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(approved_files)



class DisapproveFileViewSet(viewsets.ViewSet):
    """
        DisapproveFileViewSet to disapprove a file
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def disapprove_file(self, request):
        """
            function to diaspprove a file
        """
        data = request.data
        file_id = data.get("file_id")
        status_value = data.get("status_value")
        disapprove_reason = data.get("disapprove_reason")
        file = Files.objects.filter(id=file_id).first()
        if not disapprove_reason:
            return CustomResponse({"message": "Please give reason of disapproval."}, status=status.HTTP_400_BAD_REQUEST)
        if not file:
            return CustomResponse({"message": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 1:
            c = Files.objects.filter(id=file_id).update(is_file_disapproved=True,is_admin_approved=False, disapproved_reason=disapprove_reason)
            disapproved_file = Files.objects.filter(id=file_id).first()
            print("disss", disapproved_file.disapproved_count)
            disapproved_file.disapproved_count=1
            disapproved_file.save() 
            return CustomResponse({"message": "File disapproved successfully"}, status=status_code.HTTP_200_OK)
        else:
            return CustomResponse({"message": "Please provide valid status value."}, status=status.HTTP_400_BAD_REQUEST)
        

    def list_disapproved_file(self, request, id):
        """
            function to give list of disapproved files
        """
        page_size = request.GET.get('page_size', '')
        disapproved_files = Files.objects.filter(project_id=id, is_admin_approved=False,is_file_disapproved=True, submitted_to_admin=True, is_edited=True, is_deleted=False).all().values('id','file_name','thumbnail','deleted_at')
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(disapproved_files, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(disapproved_files)
    
    def view_disapproved_file(self, request, id):
        """
            function to view disapproved files
        """
        if not Files.objects.filter(id=id):
            return CustomResponse({"message":"file not found"}, status=status.HTTP_400_BAD_REQUEST)
        if Files.objects.filter(id=id, is_file_disapproved=False):
            return CustomResponse({"message":"this file is not disapproved"}, status=status.HTTP_400_BAD_REQUEST)
        disapproved_file = Files.objects.filter(id=id,is_admin_approved=False, is_file_disapproved=True, is_deleted=False).all().values('id', 'file_name', 'thumbnail','manufacturer_name','manufacturing_number','quantity','project_details','additional_details','recording', 'location', 'location_points','is_file_disapproved')
        return CustomResponse(disapproved_file)
    
    def approve(self, request):
        """
            function to approve to deny disapprovedfiles
        """
        data = request.data
        file_id = data.get("file_id")
        status_value = data.get("status_value")
        file = Files.objects.filter(id=file_id).first()

        if not file:
            return CustomResponse({"message": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        if status_value==1:
            Files.objects.filter(id=file_id).update(is_admin_approved=True,submitted_to_admin=True,is_edited=False,is_file_disapproved=False, disapproved_count=0, disapproved_reason=None)
            return CustomResponse ({"message": "File Approved Successfully"}, status=status.HTTP_200_OK)
        if status_value==2:
            if file.disapproved_count<=4:
                # c = Files.objects.filter(id=file_id).update(is_file_disapproved=True,is_admin_approved=False)
                disapproved_file = Files.objects.filter(id=file_id).first()
                print("disss", disapproved_file.disapproved_count)
                disapproved_file.disapproved_count=disapproved_file.disapproved_count+1
                disapproved_file.save()
                print("disss2", disapproved_file.disapproved_count)
                Files.objects.filter(id=file_id).update(is_admin_approved=False,submitted_to_admin=False, is_edited=False) #this will happen only when file is denied for 5 times, if file will be denied for 6th time, then - is_admin_approved = false , submitted_to_admin = false, is_edited = false, is_deleted = True
                return CustomResponse ({"message": "File Approval Denied Successfully"}, status=status.HTTP_200_OK)
            else:
                file.is_deleted=True
                file.save()
        else:
            return CustomResponse ({"message": "Please Provide Valid Status Value"}, status=status.HTTP_400_BAD_REQUEST)


class MarkedForDeletedFilesViewSet(viewsets.ViewSet):
    """
        MarkedForDeletedFilesViewSet to get the list of marked for deleted files
    """    
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def list(self, request, id):
        """
            function to give list of mark for deleted files
        """
        page_size = request.GET.get('page_size', '')   
        files = Files.objects.filter(project_id=id, is_marked_deleted=True).all().values('id','file_name','thumbnail','deleted_at')
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(files)
    
    def approve(self, request):
        """
            function to approve to deny the marked for deleted files
        """
        data = request.data
        # file_id = data.get("file_id")
        file_id = data.get("file_id", [])
        status_value = data.get("status_value")
        if not file_id:
                return CustomResponse({"message": "Please select file"}, status=status_code.HTTP_400_BAD_REQUEST)
        # if not file:
        #     return CustomResponse({"message": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        for i in file_id:
            print("i=",i)
            if status_value==1:
                Files.objects.filter(id=i).update(is_marked_deleted=False, is_deleted=True)
        
                # return CustomResponse ({"message": "File Deleted Request Approved Successfully"}, status=status.HTTP_200_OK)
            if status_value==2:
                Files.objects.filter(id=i).update(is_marked_deleted=False)
                # return CustomResponse ({"message": "File Delete Request Denied Successfully"}, status=status.HTTP_200_OK)
        if status_value==1:
            return CustomResponse ({"message": "File Deleted Request Approved Successfully"}, status=status.HTTP_200_OK)
        if status_value==2:
            return CustomResponse ({"message": "File Delete Request Denied Successfully"}, status=status.HTTP_200_OK)
        else:
            return CustomResponse ({"message": "Please Provide Valid Status Value"}, status=status.HTTP_400_BAD_REQUEST)


class EditUserDetailsViewSet(viewsets.ViewSet):
    """
        EditUserDetailsViewSet to edit the details of userss
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)

    def update(self, request, id):
        """
            function to update the details of users
        """
        data = request.data
        company = data.get("company")
        if not company:
            return CustomResponse({"message": "Please Enter New Company Name."}, status=status_code.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(id=id, user_role=2).first()
        if not user:
            return CustomResponse({"message": "User Not Found."}, status=status_code.HTTP_400_BAD_REQUEST)
        
        if not Company.objects.filter(name=company).exists():
            created_company = Company.objects.create(name = company)
            UserCompany.objects.filter(user_id=id).update(company_id=created_company.id)
        else:
            c = Company.objects.filter(name=company).first()
            UserCompany.objects.filter(user_id=id).update(company_id=c.id)

        return CustomResponse({"message": "Company Edited Successfully."}, status=status_code.HTTP_200_OK)


class UnapprovedUsersViewSet(viewsets.ViewSet):
    """
        UnapprovedUsersViewSet to give list of unapproved users
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def unapproved_users_list(self, request):
        """
        Function to get the list of unapproved users
        """
        page_size = request.GET.get('page_size', '')
        request_type = request.GET.get('request_type', None)

        if request_type == '1':
            users = (
                User.objects
                .filter(is_admin_approved=False, is_email_verified=True, user_role=2)
                .exclude(email=None)
                .order_by('-id', '-created_at')
                .distinct('id')
                .values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name')
            )
        elif request_type == '2':
            users = (
                User.objects
                .filter(user_role=2, is_edited=True)
                .exclude(email=None)
                .order_by('-id', '-created_at')
                .distinct('id')
                .values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name')
            )
        else:
            users = (
                User.objects
                .filter(is_admin_approved=False, is_email_verified=True, user_role=2)
                .exclude(email=None)
                .order_by('-id', '-created_at')
                .distinct('id')
                .values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name')
            )

        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(users, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(users, status=status_code.HTTP_200_OK)

        # base_query = (
        #     User.objects
        #     .filter(is_email_verified=True, user_role=2)
        #     .exclude(email=None)
        #     .order_by('-id', '-created_at')
        #     .values('id', 'full_name', 'profile_pic', 'email', 'user_company', 'user_company__company__name', 'company_name', 'is_admin_approved', 'is_edited')
        # )

        # if request_type == '1':
        #     users = base_query.filter(is_admin_approved=False)
        # elif request_type == '2':
        #     users = base_query.filter(is_edited=True)
        # else:
        #     users = base_query.filter(is_admin_approved=False)

        # page = None
        # if page_size:
        #     pagination_class = self.pagination_class()
        #     page = pagination_class.paginate_queryset(users, request)
        # if page is not None:
        #     return CustomResponse(pagination_class.get_paginated_response(page).data)
        # return CustomResponse(users, status=status_code.HTTP_200_OK)
    

    def approve_requested_user(self, request):
        """
            Function to approve the users
        """
        data = request.data
        user_id = data.get("user_id")
        status_value = data.get("status_value")
        new_company = data.get("new_company")

        user = User.objects.filter(id=user_id).first()

        if not user:
            return CustomResponse({"message": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            if status_value == 2:
                # Deny request
                if user.is_edited:
                    # If the user is edited, reset the company to the previous one
                    if user.company_name!=None:
                        print("userrr", user.company_name)
                        # existing_company = Company.objects.filter(name=user.company_name).first()
                        # UserCompany.objects.filter(user_id=user_id).update(company_id=existing_company.id)
                    user.is_edited = False  # Reset the is_edited flag
                    user.company_name=None
                    user.save()
                else:
                    # If the user is new, just delete the user
                    user.delete()

                return CustomResponse({"message": "User Denied Successfully"}, status=status_code.HTTP_200_OK)
            elif status_value == 1:
                # Approve request
                user.is_admin_approved = True
                user.is_edited = False  # Reset the is_edited flag
                user.save()

                if new_company:
                    # If new_company is provided, update the user's company
                    if not Company.objects.filter(name=new_company).exists():
                        # If the company doesn't exist, create a new one
                        created_company = Company.objects.create(name=new_company)
                        if UserCompany.objects.filter(user_id=user_id).exists():
                            UserCompany.objects.filter(user_id=user_id).update(company_id=created_company.id)
                        else:
                            UserCompany.objects.create(user_id=user_id, company_id=created_company.id)
                    else:
                        # If the company exists, update user's company
                        c = Company.objects.filter(name=new_company).first()
                        UserCompany.objects.filter(user_id=user_id).update(company_id=c.id)
                else:
                    # If new_company is not provided, use the existing company_name
                    if user.company_name:
                        existing_company = Company.objects.create(name=user.company_name)
                        if UserCompany.objects.filter(user_id=user_id).exists():
                            UserCompany.objects.filter(user_id=user_id).update(company_id=existing_company.id)
                        else:
                            UserCompany.objects.create(user_id=user_id, company_id=existing_company.id)

                # Clear the user's company_name
                user.company_name = None
                user.save()

                return CustomResponse({"message": "User Approved by Admin"}, status=status_code.HTTP_200_OK)
            else:
                return CustomResponse({"message": "Please give the right value in status value"}, status=status.HTTP_400_BAD_REQUEST)
            

class ProjectViewSet(viewsets.ViewSet):
    """
        ProjectViewSet to see the details and create project
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def create(self, request):
        """
            method to create project
        """
        data = request.data
        project_name = data.get("project_name")
        project_number = data.get("project_number")
        company_id = data.get("company_id")
        assigned_to = data.get("assigned_to", [])  # Default to an empty list if not provided
        site_name = data.get("site_name")

        # Validations
        if not project_name:
            return CustomResponse({"message": "Please provide project_name"}, status=status.HTTP_400_BAD_REQUEST)
        if not project_number:
            return CustomResponse({"message": "Please provide project_number"}, status=status.HTTP_400_BAD_REQUEST)
       
        if Project.objects.filter(project_name=project_name).exists():
            return CustomResponse({"message": "Project of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if Project.objects.filter(project_number=project_number).exists():
            return CustomResponse({"message": "Project Number already exists"}, status=status.HTTP_400_BAD_REQUEST)
        company = Company.objects.filter(id=company_id).first()

        if Site.objects.filter(name=site_name.lower()).exists():
            site = Site.objects.filter(name=site_name.lower()).first()
            print("site", site)
        else:
            site = Site.objects.create(name=site_name.lower())
            print("site2", site)


        # Create project without assigning users
        project = Project.objects.create(site_id_id=site.id, project_name=project_name, project_number=project_number, created_by_id=request.user.id,is_admin_approved=True)

        if site_name.lower()=='pm2':
            project.is_internal=True
            project.save()
        else:
            project.is_internal=False
            project.save()

        # Assign users to the project
        for id in assigned_to:
            user = User.objects.filter(id=id).first()
            if user:
                project.users.add(user)  
            print(id)

        return CustomResponse({"message": "Project created successfully", "project_id": project.id}, status=status.HTTP_200_OK)
    

    def project_list(self, request):
        """
            method to search and list projects
        """
        name = request.GET.get('name', None)
        page_size = request.GET.get('page_size', '')
        project_type = request.GET.get('project_type', None)

        if project_type =='1':
            projects = Project.objects.filter(is_admin_approved=True, is_marked_deleted=False, is_internal=True).annotate(
            num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
        ).values('id', 'project_name', 'created_by__full_name', 'num_files','site_id_id','site_id__name').order_by("-created_at")
            
        elif project_type == '2':
            projects = Project.objects.filter(is_admin_approved=True, is_marked_deleted=False, is_internal=False).annotate(
            num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
        ).values('id', 'project_name', 'created_by__full_name', 'num_files','site_id_id','site_id__name').order_by("-created_at")
            
            
        else:
            projects = Project.objects.filter(is_admin_approved=True, is_marked_deleted=False).annotate(
            num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
        ).values('id', 'project_name', 'created_by__full_name', 'num_files', 'site_id_id','site_id__name').order_by("-created_at")

        if name:
            projects = projects.filter(project_name__icontains=name)

        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(projects, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(projects)   
    
    queryset = Project.objects.all()

    def project_details(self, request, pk=None):  
        """
            method to retrieve project
        """
        project = get_object_or_404(self.queryset, pk=pk)
        serializer = ProjectDetailSerializer(project)

        return CustomResponse(serializer.data)
    
    def project_approve(self, request):
        """
            method to approve projects
        """
        data = request.data
        project_id = data.get("project_id")
        project_name = data.get("project_name")
        project_number = data.get("project_number")
        company_id = data.get("company_id")
        assigned_to = data.get("assigned_to", [])
        site_name = data.get("site_name")
        status_value = data.get("status_value")

        if not Project.objects.filter(id=project_id).first():
            return CustomResponse({"message": "Project of this id does not exist"}, status=status.HTTP_400_BAD_REQUEST)

        if status_value == 2:
            Project.objects.filter(id=project_id).delete()
            return CustomResponse({"message": "Project Request Denied Successfully"}, status=status_code.HTTP_200_OK)

        if not project_name:
            return CustomResponse({"message": "Please provide project_name"}, status=status.HTTP_400_BAD_REQUEST)
        if not project_number:
            return CustomResponse({"message": "Please provide project_number"}, status=status.HTTP_400_BAD_REQUEST)
        
        if company_id:
            c = Company.objects.filter(id=company_id).first()

        if site_name:
            if Site.objects.filter(name=site_name.lower()).exists():
                site = Site.objects.filter(name=site_name.lower()).first()
                print("site", site)
            else:
                site = Site.objects.create(name=site_name.lower())
                print("site2", site)

            if site_name.lower()=='pm2':
                Project.objects.filter(id=project_id).update(is_internal=True)
            else:
                Project.objects.filter(id=project_id).update(is_internal=False)

            Project.objects.filter(id=project_id).update(site_id_id=site.id)

        if status_value == 1:
            if Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).exists():
                if assigned_to:
                    project = Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).first()
                    for id in assigned_to:
                        print("id",id)
                        user = User.objects.filter(id=id).first()
                        if user:
                            print("user",user)
                            project.users.add(user)
                            project.is_admin_approved = True
                            project.save()

                            # Push Notification to users who created the project
                            title = f"Project Approved by Admin"
                            message = f"Hello!! Your project '{project_name}' has been approved by Admin."
                            data = {
                                "title": title,
                                "message": message,
                            }

                            notifyer = user
                            if notifyer.is_notification_enabled == True:
                                notification = UserNotification.objects.create(user=user, title=title, message=message)
                                notification.save()
                                data.update({"notification_id": str(notification.id)})

                                send_notification_bulk(
                                    user_ids=[user.id], title=title, message=message, data=data)

                    return CustomResponse({"message": "Project approved successfully"})
                else:
                    project = Project.objects.filter(id=project_id).first()
                    project.is_admin_approved = True
                    project.save()

                    # Push Notification to users who created the project
                    title = f"Project Approved by Admin"
                    message = f"Hello!! Your project '{project_name}' has been approved by Admin."
                    data = {
                        "title": title,
                        "message": message,
                    }

                    notifyer = project.created_by
                    if notifyer.is_notification_enabled == True:
                        notification = UserNotification.objects.create(user=notifyer, title=title, message=message)
                        notification.save()
                        data.update({"notification_id": str(notification.id)})

                        send_notification_bulk(
                            user_ids=[notifyer.id], title=title, message=message, data=data)

                    return CustomResponse({"message": "Project approved successfully"})
            else:
                if Project.objects.filter(project_name=project_name).exclude(id=project_id).exists():
                    return CustomResponse({"message": "Project of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
                elif Project.objects.filter(project_number=project_number).exclude(id=project_id).exists():
                    return CustomResponse({"message": "Project Number of this name already exists"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    if assigned_to:
                        project = Project.objects.filter(id=project_id).update(project_name=project_name, project_number=project_number)
                        project = Project.objects.filter(id=project_id).first()
                        for id in assigned_to:
                            user = User.objects.filter(id=id).first()
                            if user:
                                project.users.add(user)
                                project.is_admin_approved = True
                                project.save()
                                # Push Notification to users who created the project
                                title = f"Admin Assigned you a Project"
                                message = f"Hello!! Admin Assigned you a project named '{project_name}'."
                                data = {
                                    "title": title,
                                    "message": message,
                                }

                                # notifyer = user
                                # if notifyer.is_notification_enabled == True:
                                notification = UserNotification.objects.create(user=user, title=title, message=message)
                                notification.save()
                                data.update({"notification_id": str(notification.id)})

                                send_notification_bulk(
                                    user_ids=[user.id], title=title, message=message, data=data)
                        return CustomResponse({"message": "Project approved successfully"})
                    else:
                        log.info("comes")
                        project=Project.objects.filter(id=project_id).update(project_name=project_name, project_number=project_number)
                        project=Project.objects.filter(id=project_id).first()
                        project.is_admin_approved = True
                        created_by_id = project.created_by
                        project.save()
                        # Push Notification to users who created the project
                        title = f"Project Approved by Admin"
                        message = f"Hello!! Your project '{project_name}' has been approved by Admin."
                        data = {
                            "title": title,
                            "message": message,
                        }

                        # notifyer = user
                        # if notifyer.is_notification_enabled == True:
                        c = Project.objects.filter(id=project_id).first()
                        print("c===", c.created_by.id)
                        notifyer = User.objects.filter(id=c.created_by.id).first()
                        notification = UserNotification.objects.create(user=created_by_id, title=title, message=message)
                        log.info("notification")
                        log.info(notification)
                        notification.save()
                        data.update({"notification_id": str(notification.id)})
                        log.info("Data")
                        log.info(data)
                        print("aaaaaaaa", notifyer.is_notification_enabled)
                        if notifyer.is_notification_enabled == True:
                            send_notification_bulk(
                                user_ids=[created_by_id.id], title=title, message=message, data=data)
                        return CustomResponse({"message": "Project approved successfully"})
    

class AssignToUsersViewSet(viewsets.ViewSet):
    """
        AssignToUsersViewSet to give the list of users associated to a particular id
    """

    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def users_list(self, request, id):
        """
            function to give list of users of a particular company
        """
        name = request.GET.get('name', None)
        page_size = request.GET.get('page_size', '')
        users = UserCompany.objects.filter(company_id=id).all().values('user_id','user__full_name', 'user__email').order_by('-created_at')
        if name:
            users = users.filter(user__full_name__icontains=name)
        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(users, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(users)
    

class ManageManufacturerNameViewSet(viewsets.ViewSet):
    """
        ManageManufacturerNameViewSet to manage Manufacturer Name
    """
    permission_classes = (IsAuthenticated, CheckAdminOrSubAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def create(self, request):
        """
            function to create Manufacturer
        """
        data = request.data
        manufacturer_name = data.get("manufacturer_name")

        if not manufacturer_name:
            return CustomResponse({"message": "Please Enter Manufacturer Name"}, status=status_code.HTTP_400_BAD_REQUEST)
        
        if ManufacturerName.objects.filter(name=manufacturer_name).exists():
            return CustomResponse({"message": "This Manufacturer Name already exists"}, status=status_code.HTTP_400_BAD_REQUEST)
        else:
            manufacturer = ManufacturerName.objects.create(name=manufacturer_name, added_by=1)
            return CustomResponse({"message": "Manufacturer Name added successfully","manufacturer_name_id":manufacturer.id}, status=status_code.HTTP_200_OK)
        
    
    def update(self, request):
        """
            function to update manufacturer name
        """
        data = request.data
        id = data.get("id")
        new_manufacturer_name = data.get("new_manufacturer_name")
        manufacturer = ManufacturerName.objects.filter(id=id).first()
        if not manufacturer:
            return CustomResponse({"message": "This Manufacturer Name Does Not Exist"}, status=status_code.HTTP_400_BAD_REQUEST)
        
        if not new_manufacturer_name:
            return CustomResponse({"message": "Please Enter New Manufacturer Name"}, status=status_code.HTTP_400_BAD_REQUEST)
        
        new_manufacturer = ManufacturerName.objects.filter(id=id).update(name = new_manufacturer_name)
        return CustomResponse({"message": "Manufacturer Name updated successfully"}, status=status_code.HTTP_200_OK)
    

    def retrieve(self, request, id):
        """
            function to retrieve details of Manufacturer
        """
        manufacturer = ManufacturerName.objects.filter(id=id).all().values('id','name','is_active', 'added_by')
        return CustomResponse(manufacturer)
    
    def manufacturer_list(self, request):
        """
            function to search and give list of manufacturer names
        """
        page_size = request.GET.get('page_size', '')
        name = request.GET.get('name', '')
        manufacturer_type = request.GET.get('manufacturer_type', None)

        if manufacturer_type == '1':
            manufacturer = ManufacturerName.objects.filter(added_by=1).all().values('id','name','added_by')

        if manufacturer_type == '2':
            manufacturer = ManufacturerName.objects.filter(added_by=2).all().values('id','name','added_by')
        
        else:
            manufacturer = ManufacturerName.objects.all().values('id','name','added_by')

        if name:
            manufacturer = manufacturer.filter(name__icontains=name)

        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(manufacturer, request)
        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(manufacturer, status=status_code.HTTP_200_OK)
    
    def delete_manufacturer(self, request):
        """
            function to delete manufacturer name
        """
        id = request.GET.get('id')
        # data = request.data
        # id = data.get("id")
        if not id:
            return CustomResponse({"message": "Please Select Manufacturer"}, status=status_code.HTTP_400_BAD_REQUEST)
        manufacturer = ManufacturerName.objects.filter(id=id).first()
        if not manufacturer:
            return CustomResponse({"message": "Manufacturer Not Found"}, status=status_code.HTTP_400_BAD_REQUEST)
        
        manufacturer.delete()
        return CustomResponse({"message": "Manufacturer Deleted Successfully"}, status=status_code.HTTP_200_OK)


class FilesViewSet(viewsets.ViewSet):
    """
        FilesViewSet to create and update files from admin side
    """

    def list_manufacturer(self, request):
        """
            function to give list of manufacturers
        """
        name = request.GET.get('name', None)
        manufacturers = ManufacturerName.objects.all().values('id','name')
        if name:
            manufacturers = manufacturers.filter(name__icontains=name)
        return CustomResponse(manufacturers)
        # manufacturer = ManufacturerName.objects.all().values('id','name')
        # return CustomResponse(manufacturer)
    
    def create_file_admin(self, request):
        """
            method to create file
        """
        data = request.data
        thumbnail = data.get("thumbnail")
        file_name = data.get("file_name")
        manual_manufacturer_name = data.get('manual_manufacturer_name')
        manufacturer_name = data.get("manufacturer_name")
        manufacturing_number = data.get("manufacturing_number")
        project_id = data.get("project_id")
        location = data.get("location")
        quantity = data.get("quantity")
        project_details = data.get("project_details")
        recording = data.get('recording')
        additional_details = data.get("additional_details")
        location_points = data.get('location_points')

        if Files.objects.filter(manufacturing_number=manufacturing_number).exists():
             return CustomResponse({"message": "This manufacturing number already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if manual_manufacturer_name:
            new_manufacturer = ManufacturerName.objects.create(name=manual_manufacturer_name)
            print("newwwwww", new_manufacturer.id)
            file = Files.objects.create(manufacturer_name_id=new_manufacturer.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location,file_name=file_name, recording=recording, location_points=location_points,is_admin_approved=True)
            return CustomResponse({"message": "File Created with new Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)
        else:
            file = Files.objects.create(file_name=file_name, thumbnail=thumbnail, manufacturing_number=manufacturing_number, project_id=project_id, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, recording=recording, location_points=location_points, is_admin_approved=True)
            return CustomResponse({"message": "File created with existing Manufacturer Successfully", "file_id": file.id}, status=status_code.HTTP_200_OK)



# For reading data of manufacturer names and storing in the database

class UploadexcelViewSet(viewsets.ViewSet):
     def create(self, request):
        try:
            print("tryy")
            # print(request.__dir__())
            request_file = request.FILES.get("test")
            excel_data = pd.read_excel(request_file,engine='openpyxl', na_filter=False)
            print(excel_data.columns)
            for index,val in excel_data.iterrows():
                print("index",index, val)
                mit,_=ManufacturerName.objects.get_or_create(name=val.get("MFGName"))
                mit.save()
                print(mit)

        except Exception as e:
            log.info("error")
            log.info(e)
            # return CustomResponse({"message": e})
            print("error:", e)
        return CustomResponse({"message": "Excel file uploaded Successfully"})


