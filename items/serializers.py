from rest_framework import serializers
from .models import Item, Category, ItemImage


# 카테고리 시리얼라이저
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['category_id', 'category_name']


# 물품 이미지 시리얼라이저
class ItemImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemImage
        fields = ['image_id', 'image_url', 'status_info']


# 물품 시리얼라이저
class ItemSerializer(serializers.ModelSerializer):
    owner_name = serializers.ReadOnlyField(source='owner.username')
    images = ItemImageSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = [
            'item_id', 'owner_name', 'category', 'title',
            'description', 'price_day', 'images'
        ]

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)