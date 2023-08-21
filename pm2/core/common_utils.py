import logging
import math
import random
import sendgrid
from django.template.loader import render_to_string
from sendgrid.helpers.mail import Content, Email, Mail, To, From
from config.local import FROM_NAME, FROM_EMAIL, SEND_GRID_API_KEY
from sendgrid.helpers.mail import Content, Email, Mail, To
from users.templates import *


def send_signup_verification_email(email, otp):
    """
        function to send the verification email.
    """
    try:
        logging.info("try")
        ctx_dict = {"email": email, "otp": otp}
        html_template = "signup_verification.html"
        subject = "OTP verification"

    except Exception as e:
        logging.info("error" + str(e))


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
        pass
