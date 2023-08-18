from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins, generics, filters
from custom_admin.serializers import AdminLoginSerializer,AdminResetPasswordSerializer, ForgotPasswordSerializer
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from users.models import *
from django.contrib.auth.hashers import check_password
from custom_admin.models import *
from core.response import CustomResponse
from django.db.models import Count
from core.common_utils import generate_otp, send_verification_email


class AdminLoginView(viewsets.ViewSet):
    """
        this view to for admin to login
    """

    def create(self, request):
        serializer = AdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            return CustomResponse({"token": token.key})
        else:
            return CustomResponse(serializer.errors)

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
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"})
        if not user:
            return CustomResponse({"message": "OTP incorrect"})
        if new_password != confirm_password:
            return CustomResponse({"message": "Both Password are not same"})
        else:
            admin_user = User.objects.filter(id=user.user_id).first()
            admin_user.set_password(confirm_password) 
            admin_user.save()
            return CustomResponse({"message": "Password Changed sucessfully"})

# class AdminResetPasswordView(viewsets.ViewSet):

#     def create(self, request):

#         data = request.data
#         old_password = data.get("old_password")
#         new_password = data.get("new_password")
#         confirm_password = data.get("confirm_password")

#         admin_user = User.objects.filter(id=request.user.id).first()

#         if not admin_user:
#             return CustomResponse({"message": "Admin user not found."})

#         if not check_password(old_password, admin_user.password):
#             return CustomResponse({"message": "Old password is incorrect."})

#         if new_password == confirm_password:
#             admin_user.set_password(confirm_password) 
#             admin_user.save()
#             return CustomResponse({"message": "Password updated successfully."})
#         else:
#             return CustomResponse({"message": "Both passwords are not the same."})

class AdminProfileViewSet(viewsets.ViewSet):
    """
    this view is for admin frofile listing,admin prifile updte and admin change password

    """
    def list(self, request):
        user=User.objects.filter(id=request.user.id).all().values("full_name","email")
        return CustomResponse(user[0])
    
    def update(self, request):
        data = request.data
        full_name=data.get("full_name")
        email=data.get("email")
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
            

        return CustomResponse({"message": "profile updated sucessfully"})
    
    def validate(self, request):
        data = request.data
        otp=data.get("otp")
        if not otp:
            return CustomResponse({"message":"Please provide otp"})
        user=OTP.objects.filter(otp_type=1,is_used=False,otp=otp).first()
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"})
        if not user:
            return CustomResponse({"message": "OTP incorrect"})
        else:
            User.objects.filter(id=user.user_id).update(is_email_verified=True)
            OTP.objects.filter(otp_type=1,otp=otp).update(is_used=True)
            return CustomResponse({"message": "email verified"})

    def create(self, request):
        serializer = AdminResetPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.update_password()
            return CustomResponse({"message": "Password updated successfully."})
        else:
            return CustomResponse(serializer.errors)

            
class ContentManagementViewSet(viewsets.ViewSet):
    """
    this view is for content management like view content,update content,and delete content
    """

    def list(self, request):
        data = request.data
        type=data.get("type")
        user=ContentManagement.objects.filter(content_type=type).all().values("content")
        return CustomResponse(user)
    
    def update(self, request):
        data = request.data
        type=data.get("type")
        content=data.get("content")
        c=ContentManagement.objects.filter(content_type=type).update(content=content)
        if not c:
            ContentManagement.objects.create(content_type=type,content=content)
        return CustomResponse({"message": "data successfully."})
    
    def delete(self, request):
        data = request.data
        type=data.get("type")
        ContentManagement.objects.filter(content_type=type).delete()
        return CustomResponse({"message": "data deleted successfully."})

    

class CompanyNameView(viewsets.ViewSet):

    def create(self, request):
        user=Company.objects.all().values('name')
        return CustomResponse(user)
    
# class AdminprofileView(viewsets.ViewSet):

#     def create(self, request):
#         user=User.objects.filter(id=request.user.id).all().values("full_name","email")
#         return CustomResponse(user[0])
    
# class AdminprofileUpdateView(viewsets.ViewSet):

#     def create(self, request):
#         data = request.data
#         full_name=data.get("full_name")
#         email=data.get("email")
#         User.objects.filter(id=request.user.id).update(full_name=full_name,email=email)
#         return CustomResponse({"message": "profile updated sucessfully"})



class ManageCompanyView(viewsets.ViewSet):
    """
    this view is of crud operations of manage company
    """

    # def list(self, request):
    #     user = Company.objects.annotate(num_users=Count('usercompany')).values('name', 'num_users', 'is_active')
    #     return CustomResponse(user)
    
    def create(self, request):
        data = request.data
        company_title=data.get("company_title")
        if not company_title:
            return CustomResponse({"message":"Please provide company name"})

        if Company.objects.filter(name=company_title).exists():
            return CustomResponse({"message":"this company name already registered"})
        else:
            Company.objects.create(name=company_title)
            return CustomResponse({"message":"company added sucesfully"})
    
    def update(self, request):
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
        data = request.data
        id=data.get("id")
        Company.objects.filter(id=id).delete()
        return CustomResponse({"message":"company Deleted sucessfully"})
    
    # def search(self,request):
    #     company_name = request.GET.get('company_name', None)
    #     user = Company.objects.annotate(num_users=Count('usercompany')).values('name', 'num_users', 'is_active')
    #     if company_name:
    #         user=user.filter(name__icontains=company_name)
    #         return CustomResponse(user)
    #     else:
    #         return CustomResponse(user)

    def search(self, request):
        company_name = request.GET.get('company_name', None)
        user = Company.objects.annotate(num_users=Count('company')).values('name', 'num_users', 'is_active')
        if company_name:
            user = user.filter(name__icontains=company_name)
            return CustomResponse(user)
        else:
            return CustomResponse(user)

