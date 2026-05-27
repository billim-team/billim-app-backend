from django.contrib.auth.models import AbstractUser
from django.db import models
from items.models import Category


# 1. 유저 테이블 (정의서 명칭: user)
class User(AbstractUser):
    # 정의서 표준 필수 칼럼 추가
    nickname = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    trust_score = models.FloatField(default=36.5)  # 매너 온도 기본값 설정

    # 기존 작업 중 추가하셨던 유용한 필드들 완벽 유지
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    interests = models.ManyToManyField(Category, blank=True, related_name='interested_users')
    is_interests_set = models.BooleanField(default=False)

    class Meta:
        db_table = 'user'  # MySQL 테이블 이름을 정의서 명칭인 'user'로 강제

    def __str__(self):
        return self.username


# 2. 지역 테이블 (정의서 명칭: location)
class Location(models.Model):
    location_id = models.AutoField(primary_key=True)
    state = models.CharField(max_length=50)  # 시/도
    city = models.CharField(max_length=50)  # 구/군
    town = models.CharField(max_length=50)  # 동/읍/면

    class Meta:
        db_table = 'location'

    def __str__(self):
        return f"{self.state} {self.city} {self.town}"


# 3. 회원 활동 지역 테이블 (정의서 명칭: user_locations)
class UserLocation(models.Model):
    user_location_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='user_locations')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, db_column='location_id')
    is_primary = models.BooleanField(default=True)  # 대표 활동지 여부 (기본값 True)

    class Meta:
        db_table = 'user_locations'

    def __str__(self):
        return f"{self.user.username}의 활동지 - {self.location.town}"