from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import mixins, viewsets, generics, filters
from rest_framework.response import Response
from .models import User
from .serializers import SignupSerializer
from rest_framework.authtoken.models import Token


# class SignUpViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
#     """ Signup view where user provides basic information and should be able to signup"""

#     serializer_class = SignupSerializer  # Use the serializer you created

#     def create(self, request, *args, **kwargs):
#         """ Method for user signup"""
#         data = request.data

#         serializer = self.get_serializer(data=data)
#         serializer.is_valid(raise_exception=True)

#         user_obj = serializer.save()
#         token, created = Token.objects.get_or_create(user=user_obj)
#         return Response({"message": "User Registered Successfully", "user_id": user_obj.id})

class SignUpViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """ Signup view where user provides basic information and should be able to signup"""

    serializer_class = SignupSerializer  # Use the serializer you created

    def create(self, request, *args, **kwargs):
        """ Method for user signup"""
        data = request.data

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        user_obj = serializer.save()
        return Response({"message": "User Registered Successfully", "user_id": user_obj.id})
