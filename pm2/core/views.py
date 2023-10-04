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
import io 
from pydub import AudioSegment
from core.common_utils import check_file_size
from config.local import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME
from django.http import JsonResponse
from botocore.exceptions import NoCredentialsError
from urllib.parse import urlparse


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
            data = {'name': path_key, 'path': created_url}
            images.append(data)
        return CustomResponse(images)

    def compress_image(self, image):
        """
           compress_image method to compress the images 
        """
        try:
            print("Compressing image...")
            img = Image.open(image)
            print("Compressing image 2...")
            img.thumbnail((800, 800))
            print("Compressing image 3...")
            output_buffer = BytesIO()
            print("Compressing image 4...")
            img.save(output_buffer, format="png")
            output_buffer.seek(0)
            print("Compressed image...")
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


# class UploadAudioFileView(views.APIView):
#     """
#     UploadAudioFileView
#     This class contains the logic to generate pre-signed URLs for audio files in an S3 bucket.

#     Inherits: APIView
#     """

#     # def generate_signed_url(self, object_key):
#     #     try:
#     #         # Create an S3 client
#     #         s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
            
#     #         # Generate a pre-signed URL
#     #         url = s3.generate_presigned_url(
#     #             ClientMethod='get_object',
#     #             Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
#     #             ExpiresIn=36000000 # URL will expire in 1 hour (3600 seconds) - adjust as needed
#     #         )

#     #         return url
#     #     except Exception as e:
#     #         print(f"Error generating signed URL: {e}")
#     #         return None

#     # def post(self, request):
#     #     """
#     #     post method used to generate pre-signed URLs for audio files in S3 bucket.
#     #     :param request:
#     #     :return: response
#     #     """
#     #     audio_paths = request.data.getlist("path")
#     #     signed_urls = []

#     #     if not audio_paths:
#     #         return CustomResponse({"message": "No file paths provided"}, status=status_code.HTTP_400_BAD_REQUEST)

#     #     for audio_path in audio_paths:
#     #         try:
#     #             # Generate a pre-signed URL for the provided audio path
#     #             signed_url = self.generate_signed_url(audio_path)
#     #             if signed_url:
#     #                 signed_urls.append({"path": audio_path, "url": signed_url})
#     #             else:
#     #                 # Handle error if URL generation fails
#     #                 return CustomResponse({"message": f"Failed to generate a pre-signed URL for {audio_path}"},
#     #                                       status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)

#     #         except Exception as e:
#     #             print(f"Error generating signed URL for {audio_path}: {e}")
#     #             return CustomResponse({"message": f"Error generating signed URL for {audio_path}"},
#     #                                   status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)

#     #     return CustomResponse(signed_urls)

#     def generate_signed_url(self, full_url):
#         try:
#             # Create an S3 client
#             s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)

#             # Parse the full URL to extract the bucket and object key
#             parsed_url = urlparse(full_url)
#             bucket_name = parsed_url.netloc
#             object_key = parsed_url.path.lstrip('/')

#             # Generate a pre-signed URL
#             url = s3.generate_presigned_url(
#                 ClientMethod='get_object',
#                 Params={'Bucket': bucket_name, 'Key': object_key},
#                 ExpiresIn=3600  # URL will expire in 1 hour (3600 seconds) - adjust as needed
#             )

#             return url
#         except NoCredentialsError:
#             return None

#     def post(self, request):
#         data = request.data
#         object_path = data.get("object_path")

#         if not object_path:
#             return Response({"message": "Object path is required"}, status=status_code.HTTP_400_BAD_REQUEST)

#         signed_url = self.generate_signed_url(object_path)
        
#         if signed_url:
#             return Response({"signed_url": signed_url}, status=status_code.HTTP_200_OK)
#         else:
#             return Response({"message": "Failed to generate signed URL"}, status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)
        
# class GenerateAudioSignedURLView(views.APIView):
#     """
#     GenerateAudioSignedURLView
#     This class generates a signed URL for audio file upload to the S3 bucket.

#     Inherits: APIView
#     """

#     def post(self, request):
#         """
#         POST method used to generate a signed URL for audio file upload to S3.

#         :param request:
#         :return: Response containing the signed URL.
#         """
#         file_path = request.data.get("file_path")

#         if not file_path:
#             return Response({"message": "File path is required"}, status=status_code.HTTP_400_BAD_REQUEST)

#         # Check if the file extension is .mp3
#         file_extension = os.path.splitext(file_path)[1].lower()
#         if file_extension != ".mp3":
#             return Response({"message": "Invalid file extension"}, status=status_code.HTTP_400_BAD_REQUEST)

#         s3_client = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
#                                  aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)

#         content_type = "audio/mpeg"  # Set the content type for audio files

#         try:
#             signed_url = s3_client.generate_presigned_url(
#                 'put_object',
#                 Params={
#                     'Bucket': AWS_STORAGE_BUCKET_NAME,
#                     'Key': file_path,
#                     'ContentType': content_type
#                 },
#                 ExpiresIn=3600  # You can adjust the expiration time as needed
#             )
#         except Exception as e:
#             return Response({"message": str(e)}, status=status_code.HTTP_500_INTERNAL_SERVER_ERROR)

#         return Response({"signed_url": signed_url}, status=status_code.HTTP_200_OK)


# class UploadFileView(views.APIView):
#     """
#     UploadFileView: This class contains the logic of file upload into the S3 bucket.
#     Only authenticated users can perform respective operations.
#     Inherits: APIView
#     """
#     parser_classes = (MultiPartParser,)
#     image_content = "file"

#     def generate_signed_url(self, object_key):
#         try:
#             # Create an S3 client
#             s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
            
#             # Generate a pre-signed URL
#             url = s3.generate_presigned_url(
#                 ClientMethod='get_object',
#                 Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
#                 ExpiresIn=3600000  # URL will expire in 1 hour (3600 seconds) - adjust as needed
#             )

#             return url
#         except NoCredentialsError:
#             return None

#     def post(self, request):
#         """
#         POST method used to upload files into an S3 bucket.
#         :param request:
#         :return: response
#         """
#         images = []
#         result = []
#         if not request.data.get("file"):
#             return CustomResponse({"message": "No file data found"}, status=status_code.HTTP_400_BAD_REQUEST)
#         result = request.data.getlist("file")
#         for upload in result:
#             s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
#             # Extract and convert the file extension to lowercase
#             file_extension = os.path.splitext(upload.name)[1].lower()
#             file_full_name = upload.name
#             updated_filename = file_full_name.replace(' ', '_')
#             if file_extension in [".jpg", ".jpeg", ".png"]:
#                 path_key = "image/{}_{}".format(uuid.uuid4(), updated_filename)
#                 # Compress the image
#                 compressed_image = self.compress_image(upload)
#                 if not compressed_image:
#                     return CustomResponse({"message": "Failed to compress image"}, status=status_code.HTTP_400_BAD_REQUEST)
#                 upload = compressed_image
#             elif file_extension in [".mp3"]:
#                 path_key = "audio/{}_{}".format(uuid.uuid4(), updated_filename)
#                 # Compress the audio (if needed)
#                 compressed_audio = self.compress_audio(upload)
#                 if not compressed_audio:
#                     return CustomResponse({"message": "Failed to compress audio"}, status=status_code.HTTP_400_BAD_REQUEST)
#                 upload = compressed_audio
#             else:
#                 return CustomResponse({"message": "Please provide a valid file."},
#                                     status=status_code.HTTP_400_BAD_REQUEST)

#             try:
#                 s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(upload, path_key)
#             except Exception:
#                 return CustomResponse({"message": "Something went wrong during file uploading."},
#                                     status=status_code.HTTP_400_BAD_REQUEST)

#             created_url = 'https://' + AWS_STORAGE_BUCKET_NAME + '.s3.amazonaws.com/' + path_key

#             # Generate a pre-signed URL for the uploaded file
#             print("path_key===", path_key)
#             pre_signed_url = self.generate_signed_url(path_key)

#             # Include the pre-signed URL in the response
#             data = {'name': path_key, 'url': pre_signed_url}
#             images.append(data)
#         return CustomResponse(images)

#     def compress_image(self, image):
#         """
#            compress_image method to compress the images 
#         """
#         try:
#             print("Compressing image...")
#             img = Image.open(image)
#             print("Compressing image 2...")
#             img.thumbnail((800, 800))
#             print("Compressing image 3...")
#             output_buffer = BytesIO()
#             print("Compressing image 4...")
#             img.save(output_buffer, format="png")
#             output_buffer.seek(0)
#             print("Compressed image...")
#             return output_buffer
#         except Exception:
#             return None

#     def compress_audio(self, audio):
#         """
#             compress_audio method to compress the audio
#         """
#         try:
#             sound = AudioSegment.from_file(audio)
#             compressed_audio = sound.set_frame_rate(22050)
#             output_buffer = BytesIO()
#             compressed_audio.export(output_buffer, format="mp3")
#             return output_buffer
#         except Exception:
#             return None

class UploadAudioFileView(views.APIView):
    """
    UploadAudioFileView: This class contains the logic of audio file upload into the S3 bucket.
    Only authenticated users can perform respective operations.
    Inherits: APIView
    """
    parser_classes = (MultiPartParser,)

    def generate_signed_url(self, object_key):
        try:
            # Create an S3 client
            s3 = boto3.client('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID, aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY, region_name=AWS_S3_REGION_NAME)
            
            # Generate a pre-signed URL
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': AWS_STORAGE_BUCKET_NAME, 'Key': object_key},
                ExpiresIn=3600000  # URL will expire in 1 hour (3600 seconds) - adjust as needed
            )

            return url
        except NoCredentialsError:
            return None

    def post(self, request):
        """
        POST method used to generate pre-signed URLs for audio files.
        :param request:
        :return: response
        """
        audios = []
        if not request.data.getlist("file_path"):
            return CustomResponse({"message": "No file path data found"}, status=status_code.HTTP_400_BAD_REQUEST)
        file_paths = request.data.getlist("file_path")
        for file_path in file_paths:
            # Extract the object key from the provided file path
            object_key = urlparse(file_path).path.lstrip('/')
            
            # Generate a pre-signed URL for the object key
            pre_signed_url = self.generate_signed_url(object_key)

            # Include the pre-signed URL in the response
            data = {'file_path': file_path, 'url': pre_signed_url}
            audios.append(data)
        return CustomResponse(audios)




