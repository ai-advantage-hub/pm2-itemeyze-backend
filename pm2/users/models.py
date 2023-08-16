from django.db import models
from django.contrib.auth.models import AbstractBaseUser, UserManager, BaseUserManager
from django.utils import timezone



# Assuming core.models contains BaseModel
from core.models import BaseModel

class MyUserManager(BaseUserManager):
    """
    Inherits: BaseUserManager class
    """

    def create_user(self, email, password=None):
        """
        Create user with given email and password.
        :param email:
        :param password:
        :return:
        """
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email))
        # set_password is used set password in encrypted form.
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user
    

class ActiveUserManager(UserManager):
    def get_queryset(self):
        return super(ActiveUserManager, self).get_queryset().filter(is_active=True, is_deleted=False)


class ActiveObjectsManager(UserManager):
    def get_queryset(self):
        return super(ActiveObjectsManager, self).get_queryset().filter(is_deleted=False)


class User(AbstractBaseUser, BaseModel):
    ADMIN = 1
    USER = 2

    ROLE = (
        (ADMIN, "Admin"),
        (USER, "User")
    )

    full_name = models.CharField(max_length=50, blank=False, null=True, verbose_name='Full Name')
    email = models.EmailField("Email", max_length=70, unique=True, blank=True, null=True)
    user_role = models.IntegerField("User role", choices=ROLE, default=USER)
    
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    is_admin_approved = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  # Added this field
    
    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()
    all_delete_objects = UserManager()
    my_user_manager = MyUserManager()

    USERNAME_FIELD = 'email'

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['id']
        index_together = ["full_name", "email", "updated_at"]  


class OTP(BaseModel):
    """
        Model to save OTP sent to user
    """
    class VerificationType(models.IntegerChoices):
        """
            VerificationType Models used for the token_type
        """
        EMAIL_VERIFICATION = 1
        RESEND_LINK = 2
        FORGOT_PASSWORD = 3

    user = models.ForeignKey(
        User, blank=False, on_delete=models.CASCADE, related_name="otp_value")
    otp = models.CharField(max_length=100, null=True, blank=True)
    otp_type = models.IntegerField("OTP type", choices=VerificationType.choices, null=True)

    is_used = models.BooleanField(default=False)
    expired_at = models.DateTimeField(
        blank=True, null=True, verbose_name='Expired At')
    
    def save(self, *args, **kwargs):
        if not self.id:
            self.expired_at = timezone.now() + timezone.timedelta(minutes=1)
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = "OTP"
        verbose_name = 'AccountVerification'
        verbose_name_plural = 'AccountVerifications'


class Company(models.Model): 
    name = models.CharField(max_length=255)
    # Add more fields if necessary

    def __str__(self):
        return self.name
    

class UserCompany(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.email} - {self.company.name}"
    

# class Project(BaseModel):
#     """
#         Project model to save project details
#     """
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     project_name = models.CharField(max_length=255, unique=True)
#     project_description = models.TextField()
#     is_admin_approved = models.BooleanField(default=False)
#     is_deleted = models.BooleanField(default = False)
#     # created_on = models.DateTimeField(auto_now_add=True)
#     # updated_on = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return self.project_name

#     class Meta:
#         db_table = "Project"
#         verbose_name = "Project"
#         verbose_name_plural = "Projects"


# class ProjectDetails(models.Model):
#     """
#         ProjecDetails model to see the details of the projects
#     """
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='details')
#     thumbnail = models.ImageField(upload_to='project_thumbnails/', blank=True, null=True)
#     manufacturing_number = models.CharField(max_length=255)
#     #created_on = models.DateTimeField(auto_now_add=True)
#     location = models.CharField(max_length=255)
#     # Add other fields as needed

#     def __str__(self):
#         return f"Details for {self.project.project_name}"

#     class Meta:
#         db_table = "ProjectDetails"
#         verbose_name = "Project Details"
#         verbose_name_plural = "Project Details"