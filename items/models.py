from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

# 1 카테고리 테이블
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100) # NN

    def __str__(self):
        return self.category_name

# 2 물품 테이블
class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_column='owner_id') # FK, NN
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category_id') # FK, NN
    title = models.CharField(max_length=255) # NN (대여 게시글 제목)
    description = models.TextField(blank=True, null=True) # 선택 사항
    price_day = models.IntegerField() # NN (1일 기준 대여료)

    def __str__(self):
        return self.title

# 3 물품 이미지 테이블
class ItemImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id', related_name='images') # FK, NN
    image_url = models.CharField(max_length=500) # NN
    status_info = models.TextField(blank=True, null=True) # AI 상태 분석 결과