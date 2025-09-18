from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Perfil", {"fields": ("perfil",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + ((None, {"fields": ("perfil",)}),)
    list_display = ("username", "email", "perfil", "is_active", "is_staff")
    list_filter = ("perfil", "is_active", "is_staff")
    search_fields = ("username", "email")
