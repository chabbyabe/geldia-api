from django.urls import include, path
from dj_rest_auth.views import (
    LoginView,
    LogoutView,
    UserDetailsView,
    PasswordChangeView,
)
from rest_framework_simplejwt.views import TokenVerifyView
from users.views import UserRegisterView, UserSettingsViewSet
from rest_framework import routers
urlpatterns = []

dj_rest_auth_urls = [
    path("login/", LoginView.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("user/", UserDetailsView.as_view(), name="rest_user_details"),
    path("password/change/", PasswordChangeView.as_view(), name="rest_password_change"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

auth_urls = [
    path("auth/", include(dj_rest_auth_urls)),
    path("auth/register", UserRegisterView.as_view(), name="rest_register"),
]

router = routers.SimpleRouter()
router.register(r'settings', UserSettingsViewSet, basename='settings')

urlpatterns = [
    path('', include(router.urls)),
]

urlpatterns += auth_urls
