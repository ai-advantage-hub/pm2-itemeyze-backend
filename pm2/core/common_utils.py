import logging
import math
import random
import sendgrid
from django.template.loader import render_to_string
from sendgrid.helpers.mail import Content, Email, Mail, To, From
from config.local import FROM_NAME, FROM_EMAIL, SEND_GRID_API_KEY
from sendgrid.helpers.mail import Content, Email, Mail, To
from users.templates import *
from fcm_django.models import FCMDevice
from core.messages import VARIABLES
from users.models import User, UserNotification
# from users.serializers import NotificationListSerializer
from django.db import transaction
from fcm_django.models import FCMDevice
from django.core.exceptions import ObjectDoesNotExist
from firebase_admin.messaging import Message, Notification
from pyfcm import FCMNotification
from config.local import *
from firebase_admin.messaging import Message, Notification, APNSPayload, Aps, APNSConfig



def generate_otp():
    """
        function to generate a 4 digit random OTP.
    """
    digits = [i for i in range(0, 10)]
    random_str = ""
    for i in range(4):
        index = math.floor(random.random() * 10)
        random_str += str(digits[index])
    otp = random_str
    return otp


def send_html_mail_to_single_user(subject, email, html_template, ctx_dict):
    """
        method used to send the email.
        :param subject:
        :param email:
        :param html_template:
        :param ctxt_dict:
        :return:
        """
    email_body = render_to_string(html_template, ctx_dict)
    send_grid = sendgrid.SendGridAPIClient(api_key=SEND_GRID_API_KEY)
    from_email = Email(FROM_EMAIL)
    to_email = To(email)
    mail_subject = subject
    content = Content("text/html", email_body)
    mail = Mail(from_email, to_email, mail_subject, content)
    try:
        send_grid.client.mail.send.post(request_body=mail.get())
        print("success")
    except Exception as e:
        print(e)
        print("ERROR_IN_SENDING_MAIL")
    return True


def send_verification_email(email, otp):
    """to send verification email"""
    try:
        ctx_dict = {"email": email, "verification_code": otp}
        html_template = "forgot_password.html"
        subject = "YOUR LOGIN OTP"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def send_verification_link(email, otp):
    """to send verification email"""
    user = User.objects.filter(email=email).first()
    c = user.full_name
    try:
        reset_link = f"http://d29zp2hclzhanw.cloudfront.net/reset-password?otp={otp}"
        ctx_dict = {"email": c, "verification_code": otp, "reset_link": reset_link}
        html_template = "forgot_password_admin.html"
        subject = "YOUR LOGIN Link"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def send_subadmin_credentials(email, temporary_password):
    # user = User.objects.filter(email=email).first()
    # c = user.full_name
    try:
        # subject = 'Your Subadmin Credentials'
        # message = f'Your subadmin credentials are:\n\nEmail: {email}\nPassword: {temporary_password}'
        # from_email = Email(FROM_EMAIL)  # Replace with your email address or use settings variable
        # recipient_list = To(email)
        ctx_dict = {"email": email, "temporary_password": temporary_password}
        html_template = "send_subadmin.html"
        subject = "You are Subadmin now"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)

        #send_html_mail_to_single_user(subject, message, from_email, recipient_list)
    except Exception as e:
        print("error", e)    


def check_file_size(file_obj):
    """
        check_file_size function to check the size of files
    """
    try:
        file_obj_size = file_obj.size
        file_in_mb = file_obj_size / 1000000

        if file_in_mb <= 7:
            return True
        return False
    except Exception:
        return False


def update_or_create_fcm_detail(user, registration_id, device_type):
    """
        method used to save the fcm device token details
    :param user:
    :param device_type:
    :param registration_id:
    """
    device = FCMDevice.objects.filter(
        type=device_type, registration_id=registration_id).first()
    if not device:
        user_device = FCMDevice.objects.filter(
            user=user).order_by('date_created')
        device_count = user_device.count()
        if device_count == VARIABLES.get('MAX_LOGIN_FCM_TOKEN'):
            user_device.first().delete()
        FCMDevice.objects.create(
            type=device_type, registration_id=registration_id, active=True, user=user)
    else:
        device.active = True
        device.user = user
        device.save()

    FCMDevice.objects.update_or_create(type=device_type, registration_id=registration_id, defaults={
        "active": True,
        "user": user
    })
    return True


# def new_send_notification(user_ids, title, message, data):
#     try:
#         FCM_SERVER_KEY = FCM_DJANGO_SETTINGS['FCM_SERVER_KEY']
#         push_service = FCMNotification(api_key=FCM_SERVER_KEY)
        
#         # Create a list to store registration_ids
#         fcm_tokens = []

#         # Fetch UserNotification objects and their associated FCM tokens
#         with transaction.atomic():
#             for user_id in user_ids:
#                 try:
#                     # Get the user's FCMDevice
#                     user_notification = UserNotification.objects.create(
#                         user_id=user_id,
#                         title=title,
#                         message=message,
#                     )
#                     serializer = NotificationListSerializer(user_notification)
#                     # Serialize the notification
#                     notification_data = serializer.data
#                     data_message = {**data, **notification_data}
                    
#                     fcm_device = FCMDevice.objects.get(user=user_id, active=True)
#                     fcm_tokens.append(fcm_device.registration_id)
#                 except ObjectDoesNotExist:
#                     pass

#         # Send the notification to the devices
#         result = push_service.notify_multiple_devices(
#             registration_ids=fcm_tokens,
#             message_title=title,
#             message_body=message,
#             data_message=data_message,
#         )

#         return result
#     except Exception as e:
#         print("Exception:", e)
#         pass

# def send_notification(user_ids, title, message, data):
#     try:
#         logging.info("try")
#         logging.info(message)
#         user_obj = User.objects.filter(id__in=user_ids).first()
#         devices = FCMDevice.objects.select_related(
#             'user').filter(user__in=user_ids, active=True)
#         logging.info("devices", devices)
#         logging.info(devices)
#         message = Message(
#             notification=Notification(title=title, body=message, image="url"),
#             data=data
#         )
#         if user_obj.is_notification_enabled == True:
#             result = devices.send_message(message)
#         else:
#             result = True
#         logging.info(result)
#         return result
#     except Exception as e:
#         logging.info(e)
#         logging.info("HEREError", e)
#     return True

def send_notification(user_ids, title, message, data, sound):
    """
        method used to send the notifications.
    :param user_id:
    :param title:
    :param message:
    :param data:
    :param alert_type:
    """
    try:
        print(message)
        devices = FCMDevice.objects.select_related(
            'user').filter(user__in=user_ids, active=True)
        logging.info(devices)
        ios = APNSConfig(payload=APNSPayload(aps=Aps(sound=sound)))
        message = Message(
            notification=Notification(title=title, body=message, image="url"),
            data=data,
            apns=ios
        )
        result = devices.send_message(message)
        logging.info(result)
        return result
    except Exception as e:
        logging.info("HEREError", e)
    return True