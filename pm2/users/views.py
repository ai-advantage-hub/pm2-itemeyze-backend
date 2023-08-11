from django.shortcuts import render
from rest_framework import mixins, viewsets, generics, filters
from rest_framework.response import Response
from .models import User, OTP
from .serializers import SignupSerializer
from rest_framework.authtoken.models import Token
from core.common_utils import generate_otp, send_forgot_password_email
from core.response import CustomResponse


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
        return CustomResponse({"message": "OTP sent Successfully to your email", "user_id": user_obj.id})
    

class ReSendOtpViewSet(viewsets.ViewSet):
    """
        ReSendOtpViewSet used for resending the otp on email  
    """
    def create(self,request):
        data = request.data
        email=data.get("email")
        user=User.objects.filter(email=email).first()
        print(user.email)
        otp = generate_otp()
        OTP.objects.update(user=user,otp=otp,otp_type=1)
        try:
            send_forgot_password_email(user.email, otp)
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
        user_id=data.get('user_id')
        user = OTP.objects.filter(user_id=user_id).first()
        if user.otp == otp:
            return CustomResponse({"message" : "OTP Verified, User created Successfully"})
        else:
            return CustomResponse({"message" : "Incorrect OTP"})
        

