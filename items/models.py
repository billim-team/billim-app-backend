from django.db import models
from django.contrib.auth.models import User


# 1 카테고리 테이블
class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=100)

    def __str__(self):
        return self.category_name


# 2 물품 테이블
class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_column='owner_id')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, db_column='category_id')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price_day = models.IntegerField()

    def __str__(self):
        return self.title


# 3 물품 이미지 테이블
class ItemImage(models.Model):
    image_id = models.AutoField(primary_key=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, db_column='item_id', related_name='images')

    # 🚨 CharField 대신 ImageField로 변경하여 실제 파일 업로드가 가능하게 만듭니다.
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    status_info = models.TextField(blank=True, null=True)  # AI 상태 분석 결과

    def __str__(self):
        return f"Image {self.image_id} for Item {self.item_id}"