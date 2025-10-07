from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """カスタムユーザーモデル"""
    email = models.EmailField('メールアドレス', blank=True, null=True)
    department = models.CharField('部署', max_length=100, blank=True)
    phone = models.CharField('電話番号', max_length=20, blank=True)
    is_manager = models.BooleanField('マネージャー権限', default=False)
    is_viewer = models.BooleanField('閲覧者権限', default=False, help_text='全員の案件を閲覧できますが編集はできません')
    
    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'
    
    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.last_name} {self.first_name}".strip()
        return self.username
