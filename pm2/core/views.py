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
from PIL import Image
from io import BytesIO
from pydub import AudioSegment
from core.common_utils import check_file_size
from config.local import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME

# Create your views here.
# class UploadFileView(views.APIView):
#     """
#         UploadFileView
#             This class contains the logic of file upload into the S3 bucket. Only authenticated users can
#         perform respective operation.

#         Inherits: APIView
#     """
#     parser_classes = (MultiPartParser,)
#     image_content = "file"

#     def post(self, request):
#         """
#                 post method used to upload file into S3 bucket.
#             :param request:
#             :return: response
#         """
#         images = []
#         result = []
#         if not request.data.getlist("file"):
#             return CustomResponse({"message" : "No file data found"}, status=status_code.HTTP_400_BAD_REQUEST)
#         result = request.data.getlist("file")
#         for upload in result:
#             s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
#                                 aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
#             file_name, file_extension = os.path.splitext(upload.name)
#             file_full_name = upload.name
#             updated_filename = file_full_name.replace(' ', '_')
#             if file_extension.lower() in [".jpg", ".jpeg", ".png"]:
#                 path_key = "image/{}_{}".format(uuid.uuid4(), updated_filename)
#             elif file_extension.lower() in [".mp3"]:
#                 path_key = "audio/{}_{}".format(uuid.uuid4(), updated_filename)
#             else:
#                 return CustomResponse({"message" :"Please provide valid file."},
#                                                  status=status_code.HTTP_400_BAD_REQUEST)
#             bool_val = check_file_size(upload)
#             if not bool_val:
#                 return CustomResponse({"message" :"File size must be less than or equal to 7 MB."},
#                                             status=status_code.HTTP_400_BAD_REQUEST)
#             try:
#                 s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(
#                     upload, path_key)
#             except Exception:
#                 return CustomResponse({"message" : "Something went wrong during file uploading."},
#                                                  status=status_code.HTTP_400_BAD_REQUEST),
                                
#             created_url = 'https://'+AWS_STORAGE_BUCKET_NAME+'.s3.amazonaws.com/'+path_key
#             data = {'name': path_key, 'url': created_url}
#             images.append(data)
#         return CustomResponse(images)

class UploadFileView(views.APIView):
    """
    UploadFileView: This class contains the logic of file upload into the S3 bucket.
    Only authenticated users can perform respective operations.
    Inherits: APIView
    """
    parser_classes = (MultiPartParser,)
    image_content = "file"

    def post(self, request):
        """
        POST method used to upload files into an S3 bucket.
        :param request:
        :return: response
        """
        images = []
        result = []
        if not request.data.getlist("file"):
            return CustomResponse({"message": "No file data found"}, status=status_code.HTTP_400_BAD_REQUEST)
        result = request.data.getlist("file")
        for upload in result:
            s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
            file_name, file_extension = os.path.splitext(upload.name)
            file_full_name = upload.name
            updated_filename = file_full_name.replace(' ', '_')
            if file_extension.lower() in [".jpg", ".jpeg", ".png"]:
                path_key = "image/{}_{}".format(uuid.uuid4(), updated_filename)
                # Compress the image
                compressed_image = self.compress_image(upload)
                if not compressed_image:
                    return CustomResponse({"message": "Failed to compress image"}, status=status_code.HTTP_400_BAD_REQUEST)
                upload = compressed_image
            elif file_extension.lower() in [".mp3"]:
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
            data = {'name': path_key, 'url': created_url}
            images.append(data)
        return CustomResponse(images)

    def compress_image(self, image):
        """
           compress_image method to compress the images 
        """
        try:
            img = Image.open(image)
            img.thumbnail((800, 800))
            output_buffer = BytesIO()
            img.save(output_buffer, format="JPEG")
            return output_buffer
        except Exception as e:
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
        except Exception as e:
            return None