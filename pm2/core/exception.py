from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

class CustomException(APIException):
    """
        class used to handle the custom exception.
    """
    # public fields
    detail = None
    status_code = None
    location = None

    # calling constructor
    def __init__(self, status_code, message, location):
        """
            constructor used to override the public field
        :param status_code:
        :param message:
        :param location:
        """
        # override public fields
        CustomException.status_code = status_code
        CustomException.detail = message
        CustomException.location = location


def get_error_message(message: str):
    """
        method used to get custom error message.
    :param message:
    :return:
    """
    location = None
    while message.__class__ != list:
        location = list(message)[0]
        message = message[list(message)[0]]
    return location, message[0]


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    if response is not None and 'detail' in response.data:
        message = response.data['detail']
        error = {'location': 'server', 'message': message}
        response.data = {'status': response.status_code, 'error': error}
    else:
        try:
            errors = response.data
            error_location = list(errors.keys())[0]
            message = errors[error_location]
            # get location and message of error
            location, message = get_error_message(message)
            if location is not None:
                error_location = location

            if error_location == 'non_field_errors' or error_location == '':
                error_location = 'server'
            error = {'location': error_location, 'message': message}
            response.data = {'status': response.status_code, 'error': error}
        except Exception as _:
            pass
    return response