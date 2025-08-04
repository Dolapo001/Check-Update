from rest_framework.response import Response
from rest_framework import status


class ResponseHandler:
    """
    Class to handle consistent API responses and exceptions
    """

    @staticmethod
    def success(message, data=None, status_code=status.HTTP_200_OK):
        """Standard success response"""
        return Response(
            {
                "status": "success",
                "message": message,
                "data": data,
            },
            status=status_code,
        )

    @staticmethod
    def error(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Standard error response"""
        return Response(
            {
                "status": "error",
                "message": message,
                "errors": errors,  # detailed validation or other errors
            },
            status=status_code,
        )
