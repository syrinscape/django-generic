from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

class UserQuerySet(models.query.QuerySet):
    def _filter_or_exclude(self, *args, **kwargs):
        """
        Force email to lowercase. We assume it is stored in lowercase because
        case insensitive lookups (via `iexact`) are crazy slow.
        """
        if 'email' in kwargs:
            kwargs['email'] = kwargs.pop('email').lower()
        return super(UserQuerySet, self)._filter_or_exclude(*args, **kwargs)

    def active(self):
        return self.filter(is_active=True)


class EmailBasedUserManager(BaseUserManager):
    def get_queryset(self):
        return UserQuerySet(self.model, using=self._db)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.validate_unique()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        user = self.create_user(email, password=password, **extra_fields)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.validate_unique()
        user.save(using=self._db)
        return user

    def active(self):
        return self.get_queryset().active()


class EmailBasedUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _('email address'), unique=True, max_length=255, db_index=True)
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('first_name', 'last_name')

    objects = EmailBasedUserManager()

    class Meta:
        abstract = True
        ordering = ('last_name', 'first_name', 'email',)

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return u' '.join(filter(bool, [self.first_name, self.last_name]))

    def get_short_name(self):
        return self.first_name

    def save(self, *args, **kwargs):
        # Force to lowercase for faster case insensitive lookups.
        if self.email:
            self.email = self.email.lower()
        super(EmailBasedUser, self).save(*args, **kwargs)
