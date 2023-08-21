from rest_framework.exceptions import APIException


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
