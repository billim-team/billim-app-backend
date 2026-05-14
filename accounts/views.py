from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework import status

# 시리얼라이저 임포트
from .serializers import RegisterSerializer, LoginSerializer


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = False  # 가입 시 비활성화 상태
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            current_site = get_current_site(request)

            verification_link = f"http://{current_site.domain}/accounts/activate/{uid}/{token}/"
            send_mail(
                '회원가입 인증 메일입니다',
                f'아래 링크를 클릭하여 계정을 활성화하세요:\n{verification_link}',
                'admin@billim.com',
                [user.email],
            )
            return Response({"message": "인증 메일을 보냈습니다."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivateView(APIView):
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


@method_decorator(csrf_exempt, name='dispatch')  # CSRF 보안 검사를 이 뷰에서만 잠시 끕니다.
class LoginView(APIView):
    serializer_class = LoginSerializer
    # 이 뷰에서는 세션 인증을 잠시 제외하고 기본 인증만 허용하여 폼을 깨웁니다.
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        # 폼 렌더링을 위해 비어있는 시리얼라이저를 context와 함께 전달
        serializer = self.serializer_class()
        return Response({"message": "로그인하세요."}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data.get('username')
            password = serializer.validated_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)  # 브라우저 세션 로그인
                    token, _ = Token.objects.get_or_create(user=user)
                    return Response({"token": token.key}, status=status.HTTP_200_OK)
                return Response({"message": "이메일 인증 필요"}, status=401)
            return Response({"message": "로그인 실패"}, status=400)
        return Response(serializer.errors, status=400)


def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')