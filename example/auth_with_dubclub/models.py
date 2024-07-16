import logging
import requests
from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from allauth.socialaccount.models import SocialToken
from dubclub_allauth.views import DubClubOAuth2Adapter
from django.utils import timezone

logger = logging.getLogger(__name__)

SILENTLY_NO_SET_ATTR = {
    # "username",
    "first_name",
    "last_name",
    "is_superuser",
    "is_staff",
    "last_login",
    "email",
    "date_joined",
    "password",
    # "is_active",
}


def tag_group_name(name):
    """
    we would want to group names for dubclub tags are
    prefixed with dctag: to detect them from other
    groups an application could have
    """
    return "dctag:" + name


class User(AbstractUser):
    user_info = None
    id = models.IntegerField(
        primary_key=True, unique=True, help_text="User ID reference from DubClub"
    )

    @property
    def __dict__(self):
        data = super().__dict__
        data.pop("user_info", None)
        data.update(self.user_info or {})
        return data

    def __str__(self) -> str:
        if not self.user_info:
            return f"{self.username} (unloaded)"
        return f"{self.username} (loaded)"

    def __setattr__(self, name: str, value: any) -> None:
        """
        silently ignore setting these attributes, this is because the
        social account provider tries to set these values in multiple different places
        we are just going to ignore it because we will get the truth from the dubclub api
        """
        if name not in SILENTLY_NO_SET_ATTR:
            return super().__setattr__(name, value)
        logger.debug(f"prevented setting {name} to {value}")

    @property
    def token(self):
        try:
            return SocialToken.objects.get(
                account__user=self,
                expires_at__gt=timezone.now(),
            )
        except SocialToken.DoesNotExist:
            return None

    def update_groups(self, user_info):
        """
        overwrite the user's groups based on their userinfo
        """
        groups = []
        for tag in user_info.get("tags", []):
            group_name = tag_group_name(tag)
            try:
                group_local = Group.objects.get(name=group_name)
                groups.append(group_local)
            except Group.DoesNotExist:
                logger.warning(
                    f"could not find group with name {group_name} for dubclub tag {tag}"
                )

        # overwrite the user's groups with the new groups
        self.groups.set(groups)

    def update_fields(self, user_info):
        """
        the username and is_active are two fields we
        can't get rid of because of wagtail forms expect
        valid model fields, so we have to update them
        here
        """
        # self.username = user_info.get("username") # probably not safe to do so on wagtail side
        self.is_active = user_info.get("is_active")
        self.save()

    def load_user_info(self, force=False):
        """
        fetch the user info from dubclub oauth

        """
        token = self.token

        if not token:
            logger.warning(f"no token found for user {self}")
            return None

        if not self.user_info or force:
            # we just need the userinfo url
            profile_url = DubClubOAuth2Adapter(request=None).profile_url
            resp = requests.get(
                profile_url,
                params={"access_token": self.token.token},
            )
            resp.raise_for_status()
            extra_data = resp.json()
            # safety check, to make sure we are not fetching the wrong user
            if int(extra_data["sub"]) != self.id:
                raise ValueError("User mismatch: userinfo sub does not match user id")

            self.update_groups(extra_data)
            self.update_fields(extra_data)
            self.user_info = extra_data

        return self.user_info

    def user_info_value(self, key):
        if self.user_info:
            return self.user_info.get(key, None)

    def refresh_from_db(self, using=None, fields=None, **kwargs):
        self.load_user_info(force=True)

    @property
    def first_name(self):
        return self.user_info_value("given_name")

    @property
    def last_name(self):
        return self.user_info_value("family_name")

    @property
    def is_superuser(self):
        return self.user_info_value("is_superuser")

    @property
    def is_staff(self):
        return self.user_info_value("is_staff")

    @property
    def last_login(self):
        return self.user_info_value("last_login")

    @property
    def email(self):
        return self.user_info_value("email")

    @property
    def password(self):
        return None

    @property
    def date_joined(self):
        return self.user_info_value("date_joined")
