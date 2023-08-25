from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins, generics, filters
from custom_admin.serializers import AdminLoginSerializer,AdminResetPasswordSerializer, ForgotPasswordSerializer, ProjectDetailSerializer
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from users.models import Company, UserCompany, User,Project,Files
from django.contrib.auth.hashers import check_password
from custom_admin.models import *
from core.response import CustomResponse
from django.db.models import Count
from core.common_utils import generate_otp, send_verification_email
from core.permissions import CheckAdminRoleStatusPermission
from rest_framework.permissions import IsAuthenticated
from users.models import OTP
from django.utils import timezone
from django.shortcuts import get_object_or_404


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
        if not otp:
            return CustomResponse({"message":"Please provide otp"})
        if not new_password:
            return CustomResponse({"message":"Please provide new_password"})
        if not confirm_password:
            return CustomResponse({"message":"Please provide confirm_password"})
        

        user=OTP.objects.filter(otp=otp,otp_type=3).first()
        if not user:
            return CustomResponse({"message": "Wrong OTP"})
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
        if not user:
            return CustomResponse({"message": "OTP incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_password:
            return CustomResponse({"message": "Both Password are not same"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            admin_user = User.objects.filter(id=user.user_id).first()
            admin_user.set_password(confirm_password) 
            admin_user.save()
            return CustomResponse({"message": "Password Changed sucessfully"}, status=status.HTTP_200_OK)


class AdminProfileViewSet(viewsets.ViewSet):
    """
    this view is for admin frofile listing, admin profile updte and admin change password

    """
    def list(self, request):
        user=User.objects.filter(id=request.user.id).all().values("full_name","email","profile_pic")
        return CustomResponse(user[0])
    
    def update(self, request):
        data = request.data
        full_name=data.get("full_name")
        email=data.get("email")
        profile_pic=data.get("profile_pic")
        if not full_name:
            return CustomResponse({"message": "Please provide full name."})
        if profile_pic:
            User.objects.filter(id=request.user.id).update(profile_pic=profile_pic)


        if full_name:
            User.objects.filter(id=request.user.id).update(full_name=full_name)
        if email:
            otp = generate_otp()
            OTP.objects.update_or_create(user_id=request.user.id,otp=otp,otp_type=1)
        try:
            send_verification_email(email, otp)
        except BaseException:
            pass

        User.objects.filter(id=request.user.id).update(email=email,is_email_verified=False)
        return CustomResponse({"message": "profile updated sucessfully"}, status=status.HTTP_200_OK)
    
    def validate(self, request):
        data = request.data
        otp=data.get("otp")
        if not otp:
            return CustomResponse({"message":"Please provide otp"})
        user=OTP.objects.filter(otp_type=1,is_used=False,otp=otp).first()
        if not user:
            return CustomResponse({"message": "Wrong OTP"})
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
        if not user:
            return CustomResponse({"message": "OTP incorrect"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            User.objects.filter(id=user.user_id).update(is_email_verified=True)
            OTP.objects.filter(otp_type=1,otp=otp).update(is_used=True)
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
        data = request.data
        type=data.get("type")
        user=ContentManagement.objects.filter(content_type=type).all().values("content")
        return CustomResponse(user, status=status.HTTP_200_OK)
    
    def update(self, request):
        data = request.data
        type=data.get("type")
        content=data.get("content")
        if not content:
            return CustomResponse({"message": "Please provide content."})

        c=ContentManagement.objects.filter(content_type=type).update(content=content)
        if not c:
            ContentManagement.objects.create(content_type=type,content=content)
        return CustomResponse({"message": "Details Updated Successfully."}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        data = request.data
        type=data.get("type")
        ContentManagement.objects.filter(content_type=type).delete()
        return CustomResponse({"message": "Details deleted successfully."}, status=status.HTTP_200_OK)

    

class CompanyNameView(viewsets.ViewSet):

    def create(self, request):
        user=Company.objects.all().values('id','name')
        return CustomResponse(user)
    

class ManageCompanyView(viewsets.ViewSet):
    """
        This view is of crud operations for manage company
    """

    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    

    def create(self, request):
        """
            method to create the company
        """
        data = request.data
        company_title = data.get("company_title")

        if not company_title:
            return CustomResponse({"message": "Please provide company name"})

        if Company.objects.filter(name=company_title).exists():
            return CustomResponse({"message": "this company name already registered"})
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
        id=data.get("id")
        company_title=data.get("company_title")
        if not company_title:
            return CustomResponse({"message":"Please provide company name"})
        if Company.objects.filter(name=company_title).exists():
            return CustomResponse({"message":"this company name already registered"})
        else:
            Company.objects.filter(id=id).update(name=company_title)
            return CustomResponse({"message":"company name updated"})
    

    def delete(self, request):
        """
            delete method to permanently delete the company.
        """
        data = request.data
        id=data.get("id")
        c =  Company.objects.filter(id=id).first()
        if not c:
            return CustomResponse({"message":"company Does not exist"})
        Company.objects.filter(id=id).delete()
        return CustomResponse({"message":"company Deleted sucessfully"})
    

    def search(self, request):
        """
            method to list and search for the company.
        """
        company_name = request.GET.get('company_name', None)
        user = Company.objects.annotate(num_users=Count('company')).values('id', 'name', 'num_users', 'is_active')
        if company_name:
            user = user.filter(name__icontains=company_name)
            if not user:
                return CustomResponse({"message":"Data not found"})

            return CustomResponse(user)
        else:
            return CustomResponse(user)
    
    def status(self, request):
        """
            method to change status for the company.
        """
        data = request.data
        id=data.get("id")
        status=data.get("status")

        company=Company.objects.filter(id=id).first()
        if not company:
            return CustomResponse({"message":"Company dont exist for this ID"})

        if status==1:
            Company.objects.filter(id=id).update(is_active=True)
            return CustomResponse({"message":"Status Activated sucessfully"})
        else:
            Company.objects.filter(id=id).update(is_active=False)
            return CustomResponse({"message":"Status dectivated sucessfully"})



class ManageProjectViewSet(viewsets.ViewSet):

    """
        This view is of crud operations for manage Project
    """

    def search(self, request):
        name = request.GET.get('name', None)
        projects = Project.objects.annotate(num_files=Count('project_files')).values('id','project_name', 'created_by__full_name', 'num_files')
        if name:
            projects=projects.filter(project_name__icontains=name)
            if not projects:
                return CustomResponse({"message":"Data not found"})

            return CustomResponse(projects)
        else:
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
            return Response({'message': 'Project not found'})

    def create(self, request):
        data = request.data
        project_name = data.get("project_name")
        project_number = data.get("project_number")
        assigned_to = data.get("assigned_to", [])  # Default to an empty list if not provided

        # Validations
        if not project_name:
            return CustomResponse({"message": "Please provide project_name"})
        if not project_number:
            return CustomResponse({"message": "Please provide project_number"})
        if not assigned_to:
            return CustomResponse({"message": "Please provide assigned_to"})
        if Project.objects.filter(project_name=project_name).exists():
            return CustomResponse({"message": "Project of this name already exists"})
        if Project.objects.filter(project_number=project_number).exists():
            return CustomResponse({"message": "Project Number of this name already exists"})

        # Create project without assigning users
        project = Project.objects.create(project_name=project_name, project_number=project_number, created_by_id=request.user.id)

        # Assign users to the project
        for email in assigned_to:
            user = User.objects.filter(email=email).first()
            if user:
                project.users.add(user)  
            print(email)

        return CustomResponse({"message": "Project created successfully"})
    
    def file_create(self, request):
        data = request.data
        manufacturer_name = data.get("manufacturer_name")
        manufacturing_number = data.get("manufacturing_number")
        project_id = data.get("project_id")
        location = data.get("location")
        quantity = data.get("quantity")
        project_details = data.get("project_details")
        additional_details = data.get("additional_details")
        if Files.objects.filter(manufacturing_number=manufacturing_number).exists():
             return CustomResponse({"message": "This File name already exists"})
        else:
            Files.objects.create(manufacturing_number=manufacturing_number,project_id=project_id,location=location,manufacturer_name_id=manufacturer_name,quantity=quantity,project_details=project_details,additional_details=additional_details)
            return CustomResponse({"message": "File created sucessfully"})



        
    


        







        
    

    