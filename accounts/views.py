# noinspection PyProtectedMember
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status, generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# noinspection PyRelativeImports,PyUnresolvedReferences
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer

User = get_user_model()


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    authentication_classes = []
    permission_classes = []

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def get(self, request, *args, **kwargs):
        return Response({"message": "회원가입 정보를 아래 입력창에 채워주세요."}, status=status.HTTP_200_OK)

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = True
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            current_site = get_current_site(request)

            # noinspection HttpUrlsUsage
            verification_link = f"http://{current_site.domain}/accounts/activate/{uid}/{token}/"
            send_mail(
                '회원가입 인증 메일입니다',
                f'아래 링크를 클릭하여 계정이 활성화하세요:\n{verification_link}',
                'admin@billim.com',
                [user.email],
            )
            return Response({"message": "회원가입이 완료되었습니다! 즉시 로그인이 가능합니다."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivateView(APIView):
    # noinspection PyMethodMayBeStatic
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"message": "계정이 활성화되었습니다!"})
        else:
            return Response({"message": "유효하지 않은 토큰입니다."}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    authentication_classes = []
    permission_classes = []

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def get(self, request, *args, **kwargs):
        return Response({"message": "로그인 아이디와 비밀번호를 입력하세요."}, status=status.HTTP_200_OK)

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            password = serializer.validated_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    token, _ = Token.objects.get_or_create(user=user)

                    is_interests_set = bool(getattr(user, 'is_interests_set', False))

                    # noinspection PyTypeChecker
                    response_data = {
                        "token": str(token.key),
                        "is_interests_set": is_interests_set
                    }
                    return Response(response_data, status=status.HTTP_200_OK)

                return Response({"message": "이메일 인증 필요"}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({"message": "로그인 실패 (아이디나 비밀번호를 확인하세요)"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# noinspection PyUnusedLocal
def logout_view(request):
    """로그아웃 처리 함수"""
    logout(request)
    return redirect('/accounts/login/')


class MySettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        instance = serializer.save()
        if hasattr(instance, 'is_interests_set') and not instance.is_interests_set:
            instance.is_interests_set = True
            instance.save()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # 🚨 이 줄 바로 위에 정밀 타격 주석을 명시하여 타입 에러를 100% 강제 진정시킵니다.
        # noinspection PyTypeChecker
        data['is_interests_set'] = bool(getattr(self.user, 'is_interests_set', False))
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer