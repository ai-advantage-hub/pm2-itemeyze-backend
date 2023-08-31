from django.shortcuts import render
from rest_framework import views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as status_code
from .response import CustomResponse
from .exception import CustomException
import boto3
import uuid
import os
from core.common_utils import check_file_size as core_utils
from config.local import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME

# Create your views here.
class UploadFileView(views.APIView):
    """
        UploadFileView
            This class contains the logic of file upload into the S3 bucket. Only authenticated users can
        perform respective operation.

        Inherits: APIView
    """
    parser_classes = (MultiPartParser,)
    image_content = "file"

    def post(self, request):
        """
                post method used to upload file into S3 bucket.
            :param request:
            :return: response
        """
        images = []
        result = []
        if not request.data.getlist("file"):
            return CustomResponse({"message" : "No file data found"}, status=status_code.HTTP_400_BAD_REQUEST)
        result = request.data.getlist("file")
        for upload in result:
            s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
                                aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
            file_name, file_extension = os.path.splitext(upload.name)
            file_full_name = upload.name
            updated_filename = file_full_name.replace(' ', '_')
            if file_extension.lower() in [".jpg", ".jpeg", ".png"]:
                path_key = "image/{}_{}".format(uuid.uuid4(), updated_filename)
            elif file_extension.lower() in [".mp3"]:
                path_key = "audio/{}_{}".format(uuid.uuid4(), updated_filename)
            else:
                return CustomResponse({"message" :"Please provide valid file."},
                                                 status=status_code.HTTP_400_BAD_REQUEST)
            bool_val = core_utils.check_file_size(upload)
            if not bool_val:
                return CustomResponse({"message" :"File size must be less than or equal to 7 MB."},
                                            status=status_code.HTTP_400_BAD_REQUEST)
            try:
                s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(
                    upload, path_key)
            except Exception:
                return CustomResponse({"message" : "Something went wrong during file uploading."},
                                                 status=status_code.HTTP_400_BAD_REQUEST),
                                
            created_url = 'https://s3.amazonaws.com/'+path_key
            data = {'name': path_key, 'url': created_url}
            images.append(data)
        return CustomResponse(images)
