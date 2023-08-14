from django.shortcuts import render
from rest_framework import mixins, viewsets, generics, filters
from rest_framework.response import Response
from .models import User, OTP
from .serializers import SignupSerializer, UserLoginSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
from rest_framework.authtoken.models import Token
from core.common_utils import generate_otp, send_verification_email
from core.response import CustomResponse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework import status as status_code
from django.utils import timezone




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

        user_obj = serializer.save()
        return CustomResponse({"message": "OTP sent Successfully to your email"})
    

class ReSendOtpViewSet(viewsets.ViewSet):
    """
        ReSendOtpViewSet used for resending the otp on email  
    """
    def create(self,request):
        data = request.data
        email=data.get("email")
        user=User.objects.filter(email=email).first()
        otp = generate_otp()
        OTP.objects.update(user=user,otp=otp,otp_type=1)
        try:
            send_verification_email(user.email, otp)
        except Exception as e:
            print(e)
        pass
    
        return CustomResponse({"message":"OTP Send Sucessfully", "otp":otp})
    

class VerifyOTPViewSet(viewsets.ViewSet):
    """
        VerifyOTPViewSet used for verifying the otp  
    """
    def create(self,request):
        data=request.data
        otp=data.get('otp')
        user = OTP.objects.filter(otp=otp).first()
        if not user:
            return CustomResponse({"message" : "Wrong OTP"})
        if user.expired_at and user.expired_at < timezone.now():
            return CustomResponse({"message": "OTP expired"})
        else:
            user_id = user.user_id
            User.objects.filter(id=user_id).update(is_email_verified=True)
            return CustomResponse({"message" : "OTP Verified, User created Successfully" , "user_id": user_id})


class UserLoginViewSet(viewsets.ViewSet):
    """
        UserLoginViewSet for User Login
    """
    def create(self, request):
        serializer = UserLoginSerializer(data=request.data)
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
    """
       ResetPasswordViewSet will be used for reseting the password 
    """
    serializer_class = ResetPasswordSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        if not user:
            return CustomResponse({"message": "User not found."})

        serializer.update(user, serializer.validated_data)

        return CustomResponse({"message": "Password reset successfully."})
