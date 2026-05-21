from django.contrib.auth.models import AbstractUser
from django.db import models
from items.models import Category


class User(AbstractUser):
    # 유저 프로필 이미지 (선택 사항, 필요 없다면 제외 가능)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    # 🚨 유저가 다중 선택할 수 있는 관심 카테고리
    interests = models.ManyToManyField(Category, blank=True, related_name='interested_users')

    # 🚨 첫 로그인 후 관심사를 설정했는지 체크하는 플래그 (기본값 False)
    is_interests_set = models.BooleanField(default=False)