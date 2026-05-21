import os
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

# 시리얼라이저 임포트 (UserProfileSerializer 추가)
from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer

# 장고가 현재 활성화해서 사용 중인 유저 모델을 동적으로 가져옵니다.
User = get_user_model()


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
    authentication_classes = []
    permission_classes = []

    def get(self, request):
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

                    # 🚨 [중요 수정] 로그인 성공 시 토큰과 함께 관심사 설정 여부(Flag)를 반환합니다.
                    # 프론트엔드는 이 값을 보고 온보딩(관심사 선택창)으로 보낼지 홈화면으로 보낼지 분기합니다.
                    return Response({
                        "token": token.key,
                        "is_interests_set": user.is_interests_set
                    }, status=status.HTTP_200_OK)

                return Response({"message": "이메일 인증 필요"}, status=401)
            return Response({"message": "로그인 실패"}, status=400)
        return Response(serializer.errors, status=400)


def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')


# ==========================================
# [새로 추가] 마이페이지 및 설정 창 조회/수정 통합 뷰
# ==========================================
class MySettingsView(generics.RetrieveUpdateAPIView):
    """
    MY -> 설정 화면에서 내 프로필 정보를 조회(GET)하고 관심사를 수정(PUT/PATCH)하는 API
    최초 로그인 후 뜨는 관심사 설정창 저장용으로도 공용 사용됩니다.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # URL에서 유저 ID를 따로 받지 않고, 현재 토큰으로 인증된 로그인 유저 본인의 객체를 반환합니다.
        # 타인의 ID를 악용해 정보를 변조하는 보안 취약점을 방어합니다.
        return self.request.user

    def perform_update(self, serializer):
        # 유저가 관심사 등을 수정하여 저장하면 데이터베이스를 업데이트합니다.
        instance = serializer.save()

        # 첫 관심사 저장을 완료한 것이라면 플래그를 True로 변경 후 최종 저장합니다.
        if not instance.is_interests_set:
            instance.is_interests_set = True
            instance.save()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # 로그인 성공 시 유저의 실제 관심사 설정 플래그를 응답에 포함
        data['is_interests_set'] = self.user.is_interests_set
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer