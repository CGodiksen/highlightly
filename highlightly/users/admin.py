from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def _create_user(self, email: str, password: str, is_staff: bool, is_superuser: bool, is_active: bool,
                     **extra_fields) -> "User":
        now = timezone.now()
        email = self.normalize_email(email)

        user = self.model(email=email, is_active=is_active, is_staff=is_staff, is_superuser=is_superuser,
                          last_login=now, date_joined=now, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_user(self, email: str, password: str, **extra_fields) -> "User":
        return self._create_user(email, password, False, False, False, **extra_fields)

    def create_superuser(self, email: str, password: str, **extra_fields) -> "User":
        return self._create_user(email, password, True, True, True, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True, db_index=True, verbose_name="email address")
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name="user_profile", on_delete=models.CASCADE)
    first_name = models.CharField(max_length=64, validators=[MinLengthValidator(2)])
    last_name = models.CharField(max_length=64, validators=[MinLengthValidator(2)])

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"
