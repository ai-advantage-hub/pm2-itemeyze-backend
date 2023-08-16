from django.db import models

class ContentManagement(models.Model):
    TERMS = 1
    ABOUT = 2

    CONTENT_CHOICES = (
        (TERMS, 'Terms and Conditions'),
        (ABOUT, 'About the App'),
    )

    content_type = models.PositiveIntegerField(choices=CONTENT_CHOICES)
    content = models.TextField()

