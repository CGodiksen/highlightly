from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError

from users.models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(max_length=128)

    def validate(self, data: dict) -> dict:
        data = super(LoginSerializer, self).validate(data)
        user: User | None = authenticate(email=data["email"].lower(), password=data["password"])

        if not user:
            raise ValidationError("Unable to login with provided credentials.", code=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            raise ValidationError("User account not active.", code=status.HTTP_400_BAD_REQUEST)

        data["user"] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)

    class Meta:
        model = User
        fields = ["id", "email", "is_staff", "is_active", "last_login", "date_joined"]
