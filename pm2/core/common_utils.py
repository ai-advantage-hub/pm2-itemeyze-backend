import logging
import math
import random
import boto3
# import sendgrid
from firebase_admin.messaging import Message, Notification
# from sendgrid.helpers.mail import Content, Email, Mail, To, From
from django.template.loader import render_to_string

from config.local import (
    APP_LOGO,
    AWS_S3_ACCESS_KEY_ID,
    AWS_S3_SECRET_ACCESS_KEY,
    FROM_NAME,
    FROM_EMAIL,
    MANAGE_REQUEST_LINK,
    RESET_PASSWORD_LINK,
)
from core.messages import VARIABLES
from users.models import User
from fcm_django.models import FCMDevice
from users.templates import *

log = logging.getLogger(__name__)


def generate_otp():
    """
    Function to generate a 4-digit random OTP.
    """
    return ''.join(random.choices('0123456789', k=4))


def send_html_mail_to_single_user(subject, email, html_template, ctx_dict):
    """
        Method used to send the email.
        :param subject:
        :param email:
        :param html_template:
        :param ctx_dict:
    """
    logging.info("send email to user")
    email_body = render_to_string(html_template, ctx_dict)
    # SES Configuration
    AWS_REGION = "us-east-1"
    CHARSET = "UTF-8"
    client = boto3.client('ses', region_name=AWS_REGION, 
                          aws_access_key_id=AWS_S3_ACCESS_KEY_ID, 
                          aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
    SENDER = f"{FROM_NAME} <{FROM_EMAIL}>"
    try:
        print("in try")
        response = client.send_email(
            Destination={
                'ToAddresses': [email], # Recipient email address
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': email_body,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': subject,
                },
            },
            Source=SENDER, # Sender's email address
        )
        logging.info("Email sent! Message ID:"),
        print("email sent")
        logging.info(response['MessageId'])
    except Exception as e:
        print("in except")
        logging.info("exception:", e)
        logging.info("ERROR_IN_SENDING_MAIL")
    return True


def send_html_mail_to_multiple_users(subject, emails, html_template, ctx_dict):
    """
        Method used to send the email.
        :param subject:
        :param email:
        :param html_template:
        :param ctx_dict:
    """
    logging.info("send email to mutiple user")
    email_body = render_to_string(html_template, ctx_dict)
    # SES Configuration
    AWS_REGION = "us-east-1"
    CHARSET = "UTF-8"
    client = boto3.client('ses', region_name=AWS_REGION, 
                          aws_access_key_id=AWS_S3_ACCESS_KEY_ID, 
                          aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
    SENDER = f"{FROM_NAME} <{FROM_EMAIL}>"
    try:
        print("in try")
        response = client.send_email(
            Destination={
                'ToAddresses': emails, # List of recipient email addresses
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': email_body,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': subject,
                },
            },
            Source=SENDER, # Sender's email address
        )
        logging.info("Email sent! Message ID:"),
        print("email sent")
        logging.info(response['MessageId'])
    except Exception as e:
        print("in except")
        logging.info("exception:", e)
        logging.info("ERROR_IN_SENDING_MAIL")
    return True


def send_verification_email(email, otp):
    """
        method used to send verification email
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"email": email, "verification_code": otp, "logo_link": logo_link}
        html_template = "forgot_password.html"
        subject = "YOUR LOGIN OTP"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def send_onboarding_request_email(user_email, name, company_name):
    """
        method used to send onboarding request email
    """
    try:
        logo_link = APP_LOGO
        admin_url = MANAGE_REQUEST_LINK
        ctx_dict = {
            "email": user_email,
            "name": name,
            "company_name": company_name,
            "logo_link": logo_link,
            "admin_url": admin_url
        }
        html_template = "onboarding_request.html"
        subject = "New User || Onboarding Request"
        admin_email = list(User.objects.filter(user_role=1, is_active=True, is_deleted=False).values_list('email', flat=True))
        if admin_email:
            send_html_mail_to_multiple_users(subject, admin_email, html_template, ctx_dict)
        else:
            logging.info(f"No active admin users found to send the onboarding request email.")
    except Exception as e:
        print("error", e)
        logging.info(f"Error sending onboarding request email: {e}")


def send_edit_profile_verification_email(email, otp, old_email):
    """
        method used to send verification email 
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"email": email, "verification_code": otp, "old_email": old_email, "logo_link": logo_link}
        html_template = "edit_email_verification.html"
        subject = "YOUR OTP VERIFICATION FOR NEW EMAIL"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def send_reset_password_email(email):
    """
        method used to send reset password email
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"email": email, "logo_link": logo_link}
        html_template = "password_reset.html"
        subject = "YOUR ACCOUNT PASSWORD WAS CHANGED"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def send_images_on_email(link,email):
    """
        method used to send images link on email
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"link": link, "logo_link": logo_link}
        html_template = "images_download_template.html"
        subject = "Image download link"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def send_verification_link(email, otp):
    """
        method used to send verification email
    """
    user = User.objects.filter(email=email).first()
    c = user.full_name
    try:
        reset_link = f"{RESET_PASSWORD_LINK}={otp}"
        logo_link = APP_LOGO
        ctx_dict = {"email": c, "verification_code": otp, "reset_link": reset_link, "logo_link":logo_link}
        html_template = "forgot_password_admin.html"
        subject = "YOUR LOGIN Link"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def send_subadmin_credentials(email, temporary_password):
    """
        method used to send email to newly created subadmins
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"email": email, "temporary_password": temporary_password, "logo_link": logo_link}
        html_template = "send_subadmin.html"
        subject = "You are Subadmin now"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)

    except Exception as e:
        print("error", e)    


def send_updated_subadmin_credentials(old_email, email):
    """
        method used to send email to those subadmin whose credentials are changed
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"old_email": old_email, "new_email": email, "logo_link": logo_link}
        html_template = "update_subadmin.html"
        subject = "You are Subadmin now"
        send_html_mail_to_single_user(subject, old_email, html_template, ctx_dict)
        print("email sentttttt")

    except Exception as e:
        print("error", e) 


def logged_out_users(email):
    """
        method used to send email to those users whose company is deactivated by admin
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"email": email, "logo_link": logo_link}
        html_template = "log_out_users.html"
        subject = "Company has been Deactivated by Admin"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)

    except Exception as e:
        print("error", e)


def subadmin_deleted(email):
    """
        method used to send email to deactivated subadmins
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"email": email, "logo_link": logo_link}
        html_template = "subadmin_deleted.html"
        subject = "Subadmin Account Deleted by Admin"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)

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


def send_notification_bulk(user_ids, title, message, data):
    """
    method used to send notifications in bulk.
    :param user_ids:
    :param title
    :param message
    :param data
    :return:
    """
    try:
        log.info("UserIds")
        log.info(user_ids)
        devices = FCMDevice.objects.select_related(
        'user').filter(user__in=user_ids, active=True)
        log.info("devices")
        log.info(devices)
        message = Message(
        notification=Notification(title=title, body=message, image="url"),
        data=data,
        )
        log.info("message")
        log.info(message)
        devices.send_message(message)
        print("device=====",devices)
        log.info("Devices")
        log.info(devices)
    except Exception as e:
        print("HEREError", e)
    return True


def send_company_approve_to_user(email,company_name):
    """
        method used to send approve company to user
    """
    try:
        logo_link = APP_LOGO
        ctx_dict = {"company_name": company_name, "logo_link": logo_link}
        html_template = "approve_company.html"
        subject = f"YOUR COMPANY {company_name} HAS BEEN APPROVED"
        send_html_mail_to_single_user(subject, email, html_template, ctx_dict)
    except Exception as e:
        print("error", e)


def get_content_type(file_extension):
    """
    Get the content type based on the file extension.

    :param file_extension: The file extension (e.g., '.jpg', '.pdf').
    :return: The corresponding content type.
    """
    content_type_mapping = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        # Add more mappings as needed
    }

    # Use the mapping or default to 'application/octet-stream' if the extension is not recognized
    return content_type_mapping.get(file_extension.lower(), 'application/octet-stream')
