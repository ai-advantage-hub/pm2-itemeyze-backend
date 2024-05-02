from django.db import models
from django.contrib.auth.models import AbstractBaseUser, UserManager, BaseUserManager
from django.utils import timezone
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField

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
    SUB_ADMIN = 3

    ROLE = (
        (ADMIN, "Admin"),
        (USER, "User"),
        (SUB_ADMIN, "Sub Admin")
    )

    full_name = models.CharField(max_length=50, blank=False, null=True, verbose_name='Full Name')
    email = models.EmailField("Email", max_length=70, unique=True, blank=True, null=True)
    company_name = models.CharField(max_length=255, null = True, blank=True, verbose_name='company_name')
    user_role = models.IntegerField("User role", choices=ROLE, default=USER)
    profile_pic = models.CharField(blank=True, null=True, max_length=254)
    phone_number = models.CharField("Phone Number", max_length=15, blank=True, null=True) 
    
    is_active = models.BooleanField(default=True)
    is_email_verified = models.BooleanField(default=False)
    is_admin_approved = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_notification_enabled = models.BooleanField(default=True)    
    modules_accessible = ArrayField(models.CharField(max_length=254, verbose_name="accessible_modules"), null=True, blank=True)    


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
            self.expired_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = "OTP"
        verbose_name = 'AccountVerification'
        verbose_name_plural = 'AccountVerifications'


class Company(BaseModel): 
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    # Add more fields if necessary

    def __str__(self):
        return self.name
    

class UserCompany(BaseModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_company')

    def __str__(self):
        return f"{self.user.email} - {self.company.name}"


class Site(BaseModel): 
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Project(BaseModel):
    """
        Project model to save project details
    """
    users = models.ManyToManyField(User,blank=True,related_name='assigned_projects')
    project_name = models.CharField(max_length=255, unique=False, null=True)
    project_description = models.TextField(null=True)
    is_admin_approved = models.BooleanField(default=False, null=True)
    is_marked_deleted = models.BooleanField(default = False, null=True)
    project_number = models.TextField(verbose_name="project number", null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_by_project', null=True)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Project_Deleted_At")
    site_id = models.ForeignKey(Site,blank=True,on_delete=models.CASCADE, related_name='site_id', null=True)
    is_internal = models.BooleanField(default=False, null=True)
    company = models.ForeignKey(Company,on_delete=models.SET_NULL, related_name='company_id', null=True)

    def __str__(self):
        return self.project_name
    
    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

    class Meta:
        db_table = "Project"
        verbose_name = "Project"
        verbose_name_plural = "Projects"


class ManufacturerName(BaseModel):
    ADMIN = 1
    USER = 2

    AddedBy = (
        (ADMIN, "Admin"),
        (USER, "User")
    )

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    added_by = models.IntegerField("User role", choices=AddedBy, default=ADMIN)
    users = models.ForeignKey(User, on_delete=models.CASCADE, related_name='added_by_users', null=True)
    is_read = models.BooleanField(default=False, verbose_name='is_admin_read')

    def __str__(self):
        return self.name
    

class Files(BaseModel):
    """
        ProjecDetails model to see the details of the projects
    """
    class DisapprovedType(models.IntegerChoices):
        """
            disapproved status type Models used for the disapproved status
        """
        No = 0
        PENDING = 1
        RESUBMITTED = 2

    # manufacturer_name = models.ForeignKey(ManufacturerName, on_delete=models.CASCADE, related_name='name_manufacture', null=True)
    manufacturer_name = models.ForeignKey(ManufacturerName,on_delete=models.SET_NULL,related_name='name_manufacture',null=True)
    name_manufacturer = models.CharField(blank=True, null=True, max_length=254, verbose_name='nae_manufacturer')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_files')
    manual_manufacturer_name = models.CharField(blank=True, null=True, max_length=254, verbose_name='manual_name')
    file_name = models.CharField(blank=True, null=True, max_length=254)
    thumbnail = models.TextField(blank=True, null=True)
    manufacturing_number = models.CharField(max_length=254,null=True)
    quantity = models.IntegerField(default=0,blank=True, null=True, verbose_name='Quantity')
    project_details = models.TextField(null=True, blank=True, verbose_name='Project Details')
    additional_details = models.TextField(null=True, blank=True, verbose_name='Additional Details')
    recording = models.CharField(max_length=254, null=True, blank=True, verbose_name='Recording')
    location = models.CharField(max_length=255, null = True)
    location_points = models.PointField(blank=True, null=True, verbose_name='User Coordinate')
    is_admin_approved = models.BooleanField(default=False, null=True)
    is_file_disapproved = models.BooleanField(default=False, null=True)
    disapproved_reason = models.TextField(null=True, blank=True, verbose_name='disapproved_reason')
    submitted_to_admin = models.BooleanField(default=False, null=True)
    is_marked_deleted = models.BooleanField(default = False, null=True)
    is_deleted = models.BooleanField(default = False, null=True)
    is_edited = models.BooleanField(default = False, null=True)
    disapproved_file_is_edited = models.BooleanField(default = False, null=True)
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="File_Deleted_At")
    disapproved_on = models.DateTimeField(null=True, blank=True, verbose_name="File_Disapproved_on")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_by_file', null=True)
    disapproved_count = models.IntegerField(default=0,blank=True, null=True, verbose_name='diaspproved_count')
    disapproved_status= models.IntegerField(choices=DisapprovedType.choices,default=0,verbose_name='disapproved_status', null=True)
    secondary_image = models.TextField(blank=True, null=True)
    
    # Add other fields as needed

    def __str__(self):
        return f"Details for {self.project.project_name}"
    
    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

    def soft_disapproved(self):
        self.disapproved_on = timezone.now()
        self.save()

    class Meta:
        db_table = "ProjectDetails"
        verbose_name = "Project Details"
        verbose_name_plural = "Project Details"


class UserNotification(BaseModel):
    """
        UserNotification model used for sending Notifications to Users
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notification')
    title = models.CharField(max_length=100, verbose_name='Title')
    message = models.CharField(max_length=1000, verbose_name='Message')
    is_read = models.BooleanField(default=False, verbose_name='is_read')
    
    def __str__(self):
        return self.title

class TempProject(BaseModel):
    """
        Project model to save project details
    """
    users = models.ManyToManyField(User,blank=True,related_name='temp_assigned_projects')
    project_name = models.CharField(max_length=255, unique=False, null=True)
    project_number = models.TextField(verbose_name="project number", null=True)
    site = models.ForeignKey(Site,blank=True,on_delete=models.CASCADE, related_name='temp_site_id', null=True)
    is_internal = models.BooleanField(default=False, null=True)
    company = models.ForeignKey(Company,on_delete=models.SET_NULL, related_name='temp_company_id', null=True)
    class Meta:
        db_table = "temp_project"
        verbose_name = "TemporaryProject"
        verbose_name_plural = "Temporary Projects"

class Settings(BaseModel):
    """
       Settings model used to define basic settings of the project
    """
    name = models.CharField(max_length=255, unique=False, null=True)
    value = models.TextField(verbose_name="project number", null=True)
    class Meta:
        db_table = "settings"
        verbose_name = "Settings"
        verbose_name_plural = "Settings"
