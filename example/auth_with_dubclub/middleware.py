from django.contrib.auth.middleware import get_user
from django.core.handlers.wsgi import WSGIRequest
from django.utils.deprecation import MiddlewareMixin


class LoadUserInfoMiddleware(MiddlewareMixin):
    """
    simply calls the load_dubclub_user_info method on the user object to fetch the user's
    dubclub info so it will be ready for use
    """

    def process_request(self, request: WSGIRequest) -> None:
        if hasattr(request, "session"):
            user = get_user(request)
            load_user_info = getattr(user, "load_user_info", None)
            if user and load_user_info:
                load_user_info(force=True)
