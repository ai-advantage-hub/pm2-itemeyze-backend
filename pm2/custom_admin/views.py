from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, mixins, generics, filters
from custom_admin.serializers import AdminLoginSerializer,AdminResetPasswordSerializer
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from users.models import *
from django.contrib.auth.hashers import check_password
from custom_admin.models import *
from core.response import CustomResponse

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
        User.objects.filter(id=request.user.id).update(full_name=full_name,email=email)
        return CustomResponse({"message": "profile updated sucessfully"})

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
        user=Company.objects.all().values()
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





