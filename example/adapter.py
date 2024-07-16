# set in settings/base.py:
# SOCIALACCOUNT_ADAPTER = 'wag_auth.adapter.InternalSocialAccountAdapter'
# SOCIALACCOUNT_STORE_TOKENS = True

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount import app_settings


class InternalSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        populate the user with data from the oauth userinfo,
        this is different than the value in `data` because the
        value has been serialized and some values are not
        available, lucky for us the account.extra_data has all
        the data we need to setup the user
        """
        user = sociallogin.user
        account = sociallogin.account

        user.id = int(account.extra_data["sub"])
        user.username = "dcuser_" + account.extra_data["sub"]

        return user

    def save_user(self, request, sociallogin, form=None):
        """
        we are simply overriding this method to prevent the setting
        the password and ensure that sociallogin saves user and auth token
        """
        sociallogin.save(request)

    def get_app(self, request, provider):
        """
        here we are ensuring that an social app is created and
        stored, this ensure that sociallogin model will store and
        refresh the auth token when the user signs in.
        (see SocialToken.lookup & SocialToken.save(...) for
        condition to save token and update token)
        """
        # NOTE: Avoid loading models at top due to registry boot...
        from allauth.socialaccount.models import SocialApp

        config = app_settings.PROVIDERS.get(provider, {}).get("APP")

        app, _created = SocialApp.objects.get_or_create(
            provider=provider,
            defaults={
                "client_id": config.get("client_id"),
                "secret": config.get("secret"),
                "key": "1",  # oauth doesn't use the key, but it's has a not-null constraint
            },
        )
        return app
