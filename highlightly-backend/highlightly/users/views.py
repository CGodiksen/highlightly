from datetime import timedelta

from django.utils import timezone
from knox.models import AuthToken
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from users import serializers
from users.models import User


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = serializers.LoginSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: User = serializer.validated_data["user"]
        _, token = AuthToken.objects.create(user, timedelta(hours=10))

        user.last_login = timezone.now()
        user.save()

        return Response({"token": token}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    @staticmethod
    def post(request: Request) -> Response:
        request._auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RetrieveMeView(APIView):
    serializer_class = serializers.UserSerializer

    def get(self, request: Request) -> Response:
        return Response(self.serializer_class(request.user).data)
