# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.forms import CheckboxSelectMultiple
from accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_interests_set')

    fieldsets = [
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('추가 설정 항목', {
            'fields': ('profile_image', 'interests', 'is_interests_set')
        }),
    ]

    # [핵심 추가] ManyToManyField인 interests 필드의 UI를 가로형 체크박스로 변경합니다.
    formfield_overrides = {
        User.interests.field.__class__: {'widget': CheckboxSelectMultiple},
    }