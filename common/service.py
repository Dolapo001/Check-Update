# Create more services in other apps with this template
# Use services in other apps to make your views short and clean
# Perform business logic, processing and complex queries in them
# Use model managers too for mini database queries

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status

from .response_handler import ResponseHandler


class BaseService:
    def __init__(self, model):
        self.model = model

    def validate_objects(self, ids):
        objects = self.model.objects.filter(id__in=ids)
        if not objects.exists():
            return ResponseHandler.error(
                "Object not found.", status_code=status.HTTP_404_NOT_FOUND
            )
        return objects

    def create_object(self, **kwargs):
        return self.model.objects.create(**kwargs)

    def get_object(self, obj_id):
        try:
            return self.model.objects.get(id=obj_id)
        except ObjectDoesNotExist:
            return ResponseHandler.error(
                "Object not found.", status_code=status.HTTP_404_NOT_FOUND
            )
