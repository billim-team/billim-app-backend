from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from items.models import Category  # 관심 카테고리 연동을 위해 임포트

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email')

    def create(self, validated_data):
        # 유저 생성 시 비활성화 상태로 만들기 (이메일 인증 전까지)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=True  # 인증 전에는 로그인 불가 (0516-근데 일단 개발 중에는 True로 바꿈)
        )
        return user


# ==========================================
# 로그인 시 유저 객체를 검증하고 뷰로 넘겨주는 로직
# ==========================================
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            # 장고 내장 기능을 통해 아이디/비번 검증
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError("이름 또는 비밀번호가 잘못되었습니다.")
            if not user.is_active:
                raise serializers.ValidationError("이메일 인증이 필요한 계정입니다.")
        else:
            raise serializers.ValidationError("아이디와 비밀번호를 모두 입력해주세요.")

        # 뷰(views.py)에서 유저의 플래그 값을 꺼낼 수 있도록 검증된 데이터에 유저 객체를 심어둡니다.
        attrs['user'] = user
        return attrs


# ==========================================
# 🚨 [수정 완료] DRF 웹 화면 전용 체크박스 스타일 적용
# ==========================================
class UserProfileSerializer(serializers.ModelSerializer):
    """MY -> 설정 화면에서 내 프로필 정보를 조회하고 관심사를 수정할 때 사용하는 시리얼라이저"""

    # 💡 style 옵션을 부여하여 DRF 브라우저 HTML 폼 렌더링 방식을 멀티 셀렉트 박스에서 체크박스로 전환합니다.
    interests = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all(),
        required=False,
        style={'base_template': 'checkbox_multiple.html'}  # 🚨 이 스타일 옵션이 추가되었습니다!
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'interests', 'is_interests_set']
        read_only_fields = ['username', 'email', 'is_interests_set']

    def update(self, instance, validated_data):
        # 1. 프론트엔드에서 보낸 관심사 ID 리스트를 쏙 빼냅니다.
        interests_data = validated_data.pop('interests', None)

        # 2. 일반 필드(닉네임 등 변경 사항이 있다면)를 먼저 업데이트합니다.
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # 3. [핵심] ManyToManyField 데이터를 .set() 문법을 통해 다중 중복 저장합니다.
        if interests_data is not None:
            instance.interests.set(interests_data)

            # 관심사 리스트에 항목이 하나라도 담겨서 들어왔다면 온보딩 성공으로 간주하고 플래그를 True로 바꿉니다.
            if len(interests_data) > 0:
                instance.is_interests_set = True

        instance.save()
        return instance