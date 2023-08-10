from django.db import models

# Create your models here.

class BaseModel(models.Model):
    """
    Core models to save the common properties such as:
        created_at,
        updated_at,
        last_modified_by
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated At")

    class Meta:
        """Meta class"""

        abstract = True
        verbose_name = "BaseModel"