from django.contrib.auth.models import User
from .serializers import RegisterSerializer
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework.views import APIView
from rest_framework.response import Response


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # 1. 인증용 토큰 및 링크 생성
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            current_site = get_current_site(request)

            # 2. 이메일 발송
            verification_link = f"http://{current_site.domain}/accounts/activate/{uid}/{token}/"
            send_mail(
                '회원가입 인증 메일입니다',
                f'아래 링크를 클릭하여 계정을 활성화하세요:\n{verification_link}',
                'admin@billim.com',
                [user.email],
            )
            return Response({"message": "인증 메일을 보냈습니다."}, status=201)
        return Response(serializer.errors, status=400)

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
            return Response({"message": "유효하지 않은 토큰입니다."}, status=400)


# accounts/views.py 상단에 추가
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token


# accounts/views.py 맨 아래에 추가
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        # 유저 인증
        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                # 토큰 생성 또는 기존 토큰 가져오기
                token, _ = Token.objects.get_or_create(user=user)
                return Response({"token": token.key}, status=200)
            else:
                return Response({"message": "이메일 인증이 필요합니다."}, status=401)
        else:
            return Response({"message": "아이디 또는 비밀번호가 틀렸습니다."}, status=400)