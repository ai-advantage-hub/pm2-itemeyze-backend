from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins, generics, filters
from custom_admin.serializers import AdminLoginSerializer,AdminResetPasswordSerializer, ForgotPasswordSerializer, ProjectDetailSerializer,FilesSerializer,FilesPointSerializer
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from users.models import Company, UserCompany, User,Project,Files
from django.contrib.auth.hashers import check_password
from custom_admin.models import *
from core.response import CustomResponse
from django.db.models import Count
from core.common_utils import generate_otp, send_verification_email, send_subadmin_credentials
from core.permissions import CheckAdminRoleStatusPermission
from rest_framework.permissions import IsAuthenticated
from users.models import OTP
from django.utils import timezone
from django.shortcuts import get_object_or_404
import pandas as pd
from rest_framework.decorators import action
import os
import csv
from django.http import HttpResponse
from config.local import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
import boto3
import uuid
from rest_framework import status as status_code
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from core.pagination import CustomPagination
from django.db import transaction




class AdminLoginView(viewsets.ViewSet):
    """
        this view to for admin to login
    """

    def create(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return CustomResponse({"token": token.key}, status=status.HTTP_200_OK)
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

    def create(self, request):
        data = request.data
        otp = data.get("otp")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")
        email = data.get("email")
        if not otp:
            return CustomResponse({"message": "Please provide otp"}, status=status.HTTP_400_BAD_REQUEST)
        if not new_password:
            return CustomResponse({"message": "Please provide new_password"}, status=status.HTTP_400_BAD_REQUEST)
        if not confirm_password:
            return CustomResponse({"message": "Please provide confirm_password"}, status=status.HTTP_400_BAD_REQUEST)
        # if not email:
        #     return CustomResponse({"message":"Please provide email"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = OTP.objects.filter(otp=otp,otp_type=3).first()
        if not user:
            return CustomResponse({"message": "Wrong OTP"}, status=status.HTTP_400_BAD_REQUEST)
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
        if not user:
            return CustomResponse({"message": "OTP incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return CustomResponse({"message": "Both Password are not same"}, status=status.HTTP_400_BAD_REQUEST)
        
            # c=User.objects.filter(email=email).first()
            # if not c:
            #     return CustomResponse({"message": "No user found with the provided email"}, status=status.HTTP_400_BAD_REQUEST)
            # if c.id == user.user_id:
        admin_user = User.objects.filter(id=user.user_id).first()
        admin_user.set_password(confirm_password)
        admin_user.is_email_verified = True 
        admin_user.save()
        return CustomResponse({"message": "Password Changed successfully"}, status=status.HTTP_200_OK)
            # else:
            #     return CustomResponse({"message": "OTP is not matching with Email"}, status=status.HTTP_400_BAD_REQUEST)


class AdminProfileViewSet(viewsets.ViewSet):
    """
    this view is for admin profile listing, admin profile update and admin change password

    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def list(self, request):
        user = User.objects.filter(id=request.user.id).all().values("full_name", "email", "profile_pic")
        print(user)
        return CustomResponse(user)

    def update(self, request):
        data = request.data
        full_name = data.get("full_name")
        email = data.get("email")
        profile_pic = data.get("profile_pic")

        # Validate full name
        if not full_name:
            return CustomResponse({"message": "Please provide full name."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if email already exists, but ignore the current user's email
        if email and User.objects.filter(email=email).exclude(id=request.user.id).exists():
            return CustomResponse({"message": "Email already exists."}, status=status.HTTP_400_BAD_REQUEST)    

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

        # Perform the update in a single query
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

    # def create(self, request):
    #     serializer = AdminResetPasswordSerializer(data=request.data, context={'request': request})
    #     if serializer.is_valid():
    #         serializer.update_password()
    #         return CustomResponse({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
    #     else:
    #         return CustomResponse({"message": "Error Occurred"}, status=status.HTTP_400_BAD_REQUEST)
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
        # data = request.data
        # type=data.get("type")
        type = request.GET.get('type')
        user=ContentManagement.objects.filter(content_type=type).all().values("content")
        return CustomResponse(user, status=status.HTTP_200_OK)
    
    def update(self, request):
        data = request.data
        type = data.get("type")
        content = data.get("content")
        if not content:
            return CustomResponse({"message": "Please provide content."}, status=status.HTTP_400_BAD_REQUEST)

        c = ContentManagement.objects.filter(content_type=type).update(content=content)
        if not c:
            ContentManagement.objects.create(content_type=type, content=content)
        return CustomResponse({"message": "Details Updated Successfully."}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        data = request.data
        type = data.get("type")
        #type = request.GET.get('type')
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

    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
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
            #Company.objects.create(name=company_title)
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
        # data = request.data
        # id=data.get("id")
        id = request.GET.get('id')
        c = Company.objects.filter(id=id).first()
        if not c:
            return CustomResponse({"message": "company Does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        Company.objects.filter(id=id).delete()
        return CustomResponse({"message": "company Deleted successfully"})
    
    # def search(self, request):
    #     """
    #         method to list and search for the company.
    #     """
    #     company_name = request.GET.get('company_name', None)
    #     is_active = request.GET.get('is_active', None)
    #     user = Company.objects.annotate(num_users=Count('company')).values('id', 'name', 'num_users', 'is_active')
    #     if company_name:
    #         user = user.filter(name__icontains=company_name)
    #         # if not user:
    #         #     return CustomResponse({"message":"Data not found"}, status=status.HTTP_400_BAD_REQUEST)
    #     if is_active:
    #         if is_active == "true":
    #             user = user.filter(is_active=True)
    #         if is_active == "false":
    #             user = user.filter(is_active=False)
        
    #     return CustomResponse(user)

    # def search(self, request):
    #     """
    #     Method to list and search for the company.
    #     """
    #     company_name = request.GET.get('company_name', None)
    #     is_active = request.GET.get('is_active', None)
    #     page = request.GET.get('page', 1)  # Get the requested page number from the request
    #     per_page = request.GET.get('per_page', 10)  # Get the requested number of items per page
    #     # Query the companies
    #     companies = Company.objects.annotate(num_users=Count('company')).values('id', 'name', 'num_users', 'is_active')
    #     if company_name:
    #         companies = companies.filter(name__icontains=company_name)
    #     if is_active:
    #         if is_active == "true":
    #             companies = companies.filter(is_active=True)
    #         elif is_active == "false":
    #             companies = companies.filter(is_active=False)
    #     # Apply pagination
    #     paginator = Paginator(companies, per_page)
    #     try:
    #         paginated_companies = paginator.page(page)
    #     except PageNotAnInteger:
    #         paginated_companies = paginator.page(1)
    #     except EmptyPage:
    #         return CustomResponse({"message": "There are no more Companies."}, status=status_code.HTTP_404_NOT_FOUND)
    #     if not paginated_companies:
    #         return CustomResponse({"message": "No Data Found."}, status=status.HTTP_400_BAD_REQUEST)

    #     # Return paginated results
    #     results = {
    #         "data": list(paginated_companies),
    #     }

    #     return CustomResponse(results)

    def search(self, request):
        """
        Method to list and search for the company.
        """
        company_name = request.GET.get('company_name', None)
        is_active = request.GET.get('is_active', None)
        page_size = request.GET.get('page_size', '')

        # Query the companies
        companies = Company.objects.annotate(num_users=Count('company')).values('id', 'name', 'num_users', 'is_active')

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
            return CustomResponse({"message": "Status Activated successfully"})
        if status_value == 2:
            Company.objects.filter(id=id).update(is_active=False)
            return CustomResponse({"message": "Status deactivated successfully"})


class ManageProjectViewSet(viewsets.ViewSet):

    """
        This view is of crud operations for manage Project
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    # def search(self, request):
    #     name = request.GET.get('name', None)
    #     #projects = Project.objects.filter(is_admin_approved=True).annotate(num_files=Count('project_files')).values('id','project_name', 'created_by__full_name', 'num_files')
    #     projects = Project.objects.filter(is_admin_approved=True).annotate(
    #         num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
    #     ).values('id', 'project_name', 'created_by__full_name', 'num_files')
    #     if name:
    #         projects = projects.filter(project_name__icontains=name)
    #         # if not projects:
    #         #     return CustomResponse({"message":"Data not found"}, status=status.HTTP_400_BAD_REQUEST)

    #         return CustomResponse(projects)
    #     else:
    #         return CustomResponse(projects)

    # def search(self, request):
    #     name = request.GET.get('name', None)
    #     page = request.GET.get('page', 1)  # Get the requested page number from the request
    #     per_page = request.GET.get('per_page', 10)  # Get the requested number of items per page

    #     # Query the projects
    #     projects = Project.objects.filter(is_admin_approved=True).annotate(
    #         num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
    #     ).values('id', 'project_name', 'created_by__full_name', 'num_files')

    #     if name:
    #         projects = projects.filter(project_name__icontains=name)

    #     # Apply pagination
    #     paginator = Paginator(projects, per_page)
        
    #     try:
    #         paginated_projects = paginator.page(page)
    #     except PageNotAnInteger:
    #         paginated_projects = paginator.page(1)
    #     except EmptyPage:
    #         return CustomResponse({"message": "There are no more Projects."}, status=status_code.HTTP_404_NOT_FOUND)

    #     if not paginated_projects:
    #         return CustomResponse({"message": "No Data Found."}, status=status.HTTP_400_BAD_REQUEST)

    #     # Return paginated results
    #     results = {
    #         "data": list(paginated_projects),
    #     }

    #     return CustomResponse(results)     

    def search(self, request):
        name = request.GET.get('name', None)
        page_size = request.GET.get('page_size', '')

        # Query the projects
        projects = Project.objects.filter(is_admin_approved=True).annotate(
            num_files=Count('project_files', filter=Q(project_files__is_admin_approved=True))
        ).values('id', 'project_name', 'created_by__full_name', 'num_files')

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
        project = get_object_or_404(self.queryset, pk=pk)
        serializer = ProjectDetailSerializer(project)

        return CustomResponse(serializer.data)
    
    def destroy(self, request, id):
        try:
            instance = Project.objects.get(id=id)
            instance.delete()
            return Response({'message': 'Project deleted successfully'})
        except Project.DoesNotExist:
            return Response({'message': 'Project not found'}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        data = request.data
        project_name = data.get("project_name")
        project_number = data.get("project_number")
        assigned_to = data.get("assigned_to", [])  # Default to an empty list if not provided

        # Validations
        if not project_name:
            return CustomResponse({"message": "Please provide project_name"}, status=status.HTTP_400_BAD_REQUEST)
        if not project_number:
            return CustomResponse({"message": "Please provide project_number"}, status=status.HTTP_400_BAD_REQUEST)
        # if not assigned_to:
        #     return CustomResponse({"message": "Please provide assigned_to"}, status=status.HTTP_400_BAD_REQUEST)
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

        return CustomResponse({"message": "Project created successfully", "project_id": project.id})
    
    def file_create(self, request):
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
        additional_details = data.get("additional_details")
        location_points = data.get('location_points')

        if Files.objects.filter(manufacturing_number=manufacturing_number).exists():
             return CustomResponse({"message": "This manufacturing number already exists"}, status=status.HTTP_400_BAD_REQUEST)
        if manual_manufacturer_name:
            new_user = User.objects.create(full_name=manual_manufacturer_name)
            print("newwwwww", new_user.id)
            file = Files.objects.create(manufacturer_name_id=new_user.id, manual_manufacturer_name=manual_manufacturer_name, project_id=project_id, manufacturing_number=manufacturing_number, quantity=quantity, project_details=project_details, additional_details=additional_details,location=location,file_name=file_name, location_points=location_points,is_admin_approved=True)
            # c = str(project_id)+'_'+str(file.id)+'_'+'filename'
            # print("ccccccccc",c)
            # b = Files.objects.filter(id=file.id).update(file_name=c)
            # print("new filleeeee", file)
            return CustomResponse({"message": "File Created with new user Successfully", "file_id": file.id})
        else:
            file = Files.objects.create(file_name=file_name, thumbnail=thumbnail, manufacturing_number=manufacturing_number, project_id=project_id, location=location, manufacturer_name_id=manufacturer_name, quantity=quantity, project_details=project_details, additional_details=additional_details, location_points=location_points, is_admin_approved=True)
            return CustomResponse({"message": "File created successfully", "file_id": file.id})
        
    def un_approved_project(self, request):
        projects = Project.objects.filter(is_admin_approved=False).annotate(num_files=Count('project_files')).values('id', 'project_name', 'created_by__full_name', 'num_files','created_at')
        return CustomResponse(projects)
    
    def un_approved_project_count(self, request):
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

    def approve_project(self, request):
        data = request.data
        project_id = data.get("project_id")
        project_name = data.get("project_name")
        project_number = data.get("project_number")
        assigned_to = data.get("assigned_to", [])
        status_value = data.get("status_value")

        # if status == 2:
        #     Project.objects.filter(id=project_id).delete()
        #     return CustomResponse({"message": "Project deleted"})
        if not Project.objects.filter(id=project_id).first():
            return CustomResponse({"message": "Project of this id dont exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        if status_value == 2:
            Project.objects.filter(id=project_id).delete()
            return CustomResponse({"message": "Project deleted"})
        
        if not project_name:
            return CustomResponse({"message": "Please provide project_name"}, status=status.HTTP_400_BAD_REQUEST)
        if not project_number:
            return CustomResponse({"message": "Please provide project_number"}, status=status.HTTP_400_BAD_REQUEST)
        
        # if status_value == 2:
        #     Project.objects.filter(id=project_id).delete()
        #     return CustomResponse({"message": "Project deleted"})
        
        if status_value == 1:
        
            if Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).exists():
                if assigned_to:
                    project = Project.objects.filter(id=project_id, project_name=project_name, project_number=project_number).first()
                    # user = User.objects.filter(email=assigned_to).first()
                    # project.users.add(user)
                    # project.is_admin_approved=True
                    # project.save()
                    for email in assigned_to:
                        user = User.objects.filter(email=email).first()
                        if user:
                            project.users.add(user)
                            project.is_admin_approved = True
                            project.save() 
                    return CustomResponse({"message": "Project approved successfully"})
                else:
                    project=Project.objects.filter(id=project_id).first()
                    project.is_admin_approved = True
                    project.save()
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
                        # user = User.objects.filter(email=assigned_to).first()
                        # project.users.add(user)
                        # project.is_admin_approved=True
                        # project.save()
                        for email in assigned_to:
                            user = User.objects.filter(email=email).first()
                            if user:
                                project.users.add(user)
                                project.is_admin_approved = True
                                project.save()
                        return CustomResponse({"message": "Project approved successfully"})
                    else:
                        project=Project.objects.filter(id=project_id).update(project_name=project_name, project_number=project_number)
                        project=Project.objects.filter(id=project_id).first()
                        project.is_admin_approved = True
                        project.save()
                        return CustomResponse({"message": "Project approved successfully"})
    # def approve_project(self, request):
    #     data = request.data
    #     project_id = data.get("project_id")
    #     project_name = data.get("project_name")
    #     project_number = data.get("project_number")
    #     assigned_to = data.get("assigned_to", [])
    #     status = data.get("status")

    #     project = Project.objects.filter(id=project_id).first()

    #     if not project:
    #         return CustomResponse({"message": "Project of this id does not exist"})

    #     if status == 2:
    #         project.delete()
    #         return CustomResponse({"message": "Project deleted"})

    #     if not project_name:
    #         return CustomResponse({"message": "Please provide project_name"})
    #     if not project_number:
    #         return CustomResponse({"message": "Please provide project_number"})

    #     if status == 1:
    #         if Project.objects.filter(project_name=project_name).exclude(id=project_id).exists():
    #             return CustomResponse({"message": "Project of this name already exists"})
    #         elif Project.objects.filter(project_number=project_number).exclude(id=project_id).exists():
    #             return CustomResponse({"message": "Project Number of this name already exists"})

    #         project.project_name = project_name
    #         project.project_number = project_number
    #         project.is_admin_approved = True
    #         if assigned_to:
    #             for email in assigned_to:
    #                 user = User.objects.filter(email=email).first()
    #                 if user:
    #                     project.users.add(user)
    #         project.save()
    #         return CustomResponse({"message": "Project approved successfully"})

    # def un_approved_file(self, request, id):
    #     file = Files.objects.filter(project_id=id, is_admin_approved=False).all().values('file_name', 'id', 'thumbnail', 'created_at')
    #     return CustomResponse(file)

    def un_approved_file(self, request, id):
        page_size = request.GET.get('page_size', '')
        
        # Query unapproved files
        files = Files.objects.filter(project_id=id, is_admin_approved=False).all().values('file_name', 'id', 'thumbnail', 'created_at')
        
        page = None

        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(files, request)

        if page is not None:
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        return CustomResponse(files)

    def un_approved_project(self, request):
        page_size = request.GET.get('page_size', '')
        projects = Project.objects.filter(is_admin_approved=False).annotate(num_files=Count('project_files')).values('id', 'project_name', 'created_by__full_name', 'num_files','created_at')
        page = None
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(projects, request)
        if page is not None:
        # serializer = self.action_serializers.get(self.action)(instance=projects, many=True)
            return CustomResponse(pagination_class.get_paginated_response(page).data)
        return CustomResponse(projects)
    
    def un_approved_files_count(self, request, id):
        file = Files.objects.filter(project_id=id, is_admin_approved=False).count()
        return CustomResponse(file)
    
    # def un_approved_file(self, request, id):
    #     unapproved_files = Files.objects.filter(project_id=id, is_admin_approved=False).all().values('file_name', 'id', 'thumbnail', 'created_at')
    #     count = unapproved_files.count()
    #     response_data = {
    #         "unapproved_files": list(unapproved_files),
    #         "count": count
    #     }
    #     return CustomResponse(response_data)
    
    def view_file(self, request, id):
        file = Files.objects.filter(id=id)
        if not file.exists():
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        serialized_file = FilesPointSerializer(file, many=True).data
        return CustomResponse(serialized_file)
    
    def destroy_file(self, request, id):
        file = Files.objects.filter(id=id).first()
        if not file:
            return CustomResponse({"message": "File not found"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            file.delete()
            return CustomResponse({"message": "File deleted successfully"})
        
    def update_file(self, request, *args, **kwargs):
        queryset = Files.objects.all()
        pk = self.kwargs.get('pk')
        instance = queryset.filter(pk=pk).first()

        if instance is None:
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = FilesSerializer(instance, data=request.data, partial=True)
        
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return CustomResponse(serializer.data, status=status.HTTP_200_OK)
        else:
            return CustomResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def approve_file(self, request):
        data = request.data
        id = data.get("id")
        status_value = data.get("status_value")

        file = Files.objects.filter(id=id).first()
        if not file:
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 2:
            file.delete()
            return CustomResponse({"message": "File deleted successfully"})
        else:
            file.is_admin_approved = True
            file.save()
            User.objects.filter(id=file.manufacturer_name.id).update(is_admin_approved=True)
            return CustomResponse({"message": "File approved by the admin"})
        
    def delete_file_list(self, request, id):
        file = Files.objects.filter(project_id=id, is_marked_deleted=True).all().values("id", "file_name")
        return CustomResponse(file)
    
    def delete_file_admin(self, request):
        data = request.data
        id = data.get("id")
        status_value = data.get("status_value")
        file = Files.objects.filter(id=id).first()
        if not file:
            return CustomResponse({"message": "File dont exist"}, status=status.HTTP_400_BAD_REQUEST)
        if status_value == 1:
            file.delete()
            return CustomResponse({"message": "File deleted successfully"})
        else:
            file.is_marked_deleted = False
            file.save()
            return CustomResponse({"message": "File delete denied by admin"})
    
    def view_file_unapproved(self, request, id):
        file = Files.objects.filter(id=id)
        if not file.exists():
            return CustomResponse({"error": "File not found."}, status=status.HTTP_400_BAD_REQUEST)
        serialized_file = FilesPointSerializer(file, many=True).data
        return CustomResponse(serialized_file)
    
        
    # @action(detail=True, methods=['get'])
    # def save_to_csv(self, request, pk=None):
    # # Retrieve the serialized data
    #     queryset = Project.objects.all()
    #     project = get_object_or_404(queryset, pk=pk)
    #     serializer = ProjectDetailSerializer(project)
    #     serialized_data = serializer.data

    #     # Check and create directory if it doesn't exist
    #     export_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    #     if not os.path.exists(export_dir):
    #         os.makedirs(export_dir)

    #     # Define path for the CSV file
    #     csv_path = os.path.join(export_dir, f'project_detail_{pk}.csv')

    #     with open(csv_path, 'w', newline='') as csvfile:
    #         writer = csv.writer(csvfile)

    #         # Write the headers to the CSV
    #         headers = [
    #             'project_name', 'project_number', 'created_at', 'created_by', 'file_name', 'thumbnail',
    #             'manufacturing_number', 'quantity', 'project_details', 'additional_details', 
    #             'recording', 'location', 'location_points'
    #         ]
    #         writer.writerow(headers)

    #         # Write the data to the CSV
    #         for file in serialized_data['files']:
    #             row_data = [
    #                 serialized_data['project_name'], 
    #                 serialized_data['project_number'], 
    #                 serialized_data['created_at'],
    #                 serialized_data['created_by']
    #             ]
    #             for field in headers[3:]:  # start from 'file_name'
    #                 row_data.append(file.get(field, ''))
    #             writer.writerow(row_data)

    #     return Response({'file_path': csv_path}, status=status.HTTP_201_CREATED)
        
    @action(detail=True, methods=['get'])
    def save_to_csv(self, request, pk=None):
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
        This view is of crud operations for manage Subadmin
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def search(self, request):
        """
            function for listing and searching of subadmin
        """
        query = request.GET.get('query', None)
        is_active = request.GET.get('is_active', None)
        page_size = request.GET.get('page_size', '') # Obtain the page_size parameter

        users_query = User.all_objects.filter(user_role=3).values('id', 'full_name', 'email', 'is_active', 'phone_number', 'modules_accessible')
        if query:
            users_query = users_query.filter(full_name__icontains=query)

        if is_active:
            if is_active == "true":
                users_query = users_query.filter(is_active=True)
            elif is_active == "false":
                users_query = users_query.filter(is_active=False)
    
        page = None
        if page_size: # Check for page_size
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(users_query, request)
    
        if page is not None: # If page is paginated, return paginated response
            return CustomResponse(pagination_class.get_paginated_response(page).data)

        data = {
            "users": users_query
        }
        return CustomResponse(data)
    
    def retrieve(self, request, id):
        """
            function to retrieve subadmin
        """
        sub_admin=User.objects.filter(id=id, user_role=3).all().values('full_name', 'email', 'phone_number', 'created_at', 'modules_accessible')
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

        if User.objects.filter(email=email).exists():
            return CustomResponse({"message": "Email Already Exists"})
        if User.objects.filter(phone_number=phone_number).exists():
            return CustomResponse({"message": "Phone Number Already Exists"})
        with transaction.atomic():
            sub_admin = User.objects.create(full_name=full_name, email=email, phone_number=phone_number, user_role=3)
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
            return CustomResponse({"message": "Subadmin created Successfully", "id":d.id})
        
    def edit_subadmin(self, request, id):
        """
            function to edit details of subadmin
        """
        data = request.data
        full_name = data.get('full_name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        modules_accessible = data.get("modules_accessible", [])

        sub_admin = User.all_objects.filter(id=id, user_role=3).first()
        if not sub_admin:
            return CustomResponse({"message": "Subadmin not found"}, status=status.HTTP_404_NOT_FOUND)
        if full_name:
            sub_admin.full_name = full_name
        if email:
            sub_admin.email = email
        if phone_number:
            sub_admin.phone_number = phone_number
        if modules_accessible:
            sub_admin.modules_accessible = modules_accessible

        sub_admin.save()

        return CustomResponse({"message": "Subadmin details updated successfully"}, status=status.HTTP_200_OK)
    
    def update(self, request, id):
        """
            function to delete the subadmin
        """
        sub_admin = User.all_objects.filter(id=id, user_role=3).first()
        if not sub_admin:
            return CustomResponse({"message": "Subadmin not found."}, status=status_code.HTTP_404_NOT_FOUND)
        sub_admin.email = None
        sub_admin.is_deleted = True
        sub_admin.save()
            
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

        total_users = User.objects.filter(user_role=User.USER, **filters).count()
        total_subadmins = User.objects.filter(user_role=User.SUB_ADMIN, **filters).count()
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

    def get(self, request, *args, **kwargs):
        search_query = request.query_params.get('search', None)
        
        users_query = User.objects.filter(user_role=2)
        
        if search_query:
            users_query = users_query.filter(email__icontains=search_query)
        
        users = users_query.values('id', 'email')
        
        return CustomResponse(users)

        
class AdminNameViewset(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def get(self, request, *args, **kwargs):
        name = User.objects.filter(id=request.user.id).all().values('id', 'full_name')
        return CustomResponse(name)              


            






            
        


            







            
        

        