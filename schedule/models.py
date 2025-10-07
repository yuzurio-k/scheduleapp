from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Field(models.Model):
    """分野モデル"""
    name = models.CharField('分野名', max_length=50, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='登録者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='登録日時')

    class Meta:
        verbose_name = '分野'
        verbose_name_plural = '分野'
        ordering = ['name']

    def __str__(self):
        return self.name

class Project(models.Model):
    """案件モデル"""
    name = models.CharField('案件名', max_length=200)
    manufacturing_number = models.CharField('製造番号', max_length=100)
    due_date = models.DateField('納期', null=True, blank=True)
    description = models.TextField('詳細', blank=True)
    is_completed = models.BooleanField('完了フラグ', default=False)
    completed_at = models.DateTimeField('完了日時', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='登録者', related_name='created_projects')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='担当者', related_name='assigned_projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '案件'
        verbose_name_plural = '案件'

    def __str__(self):
        return f'{self.name} ({self.manufacturing_number})'
    
    def toggle_completion(self):
        """完了状態を切り替える"""
        from django.utils import timezone
        if self.is_completed:
            self.is_completed = False
            self.completed_at = None
        else:
            self.is_completed = True
            self.completed_at = timezone.now()
        self.save()
    
    def has_schedules(self):
        """スケジュールが存在するかどうかを返す"""
        return self.schedule_set.exists()
    
    def can_be_deleted(self):
        """削除可能かどうかを返す（スケジュールが存在しない場合のみ削除可能）"""
        return not self.has_schedules()


class Schedule(models.Model):
    """スケジュールモデル"""
    STATUS_CHOICES = [
        ('pending', '予定'),
        ('in_progress', '進行中'),
        ('completed', '完了'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='案件')
    field = models.ForeignKey(Field, on_delete=models.CASCADE, verbose_name='分野')
    start_date = models.DateField('開始日')
    end_date = models.DateField('終了日')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField('詳細', blank=True)
    completed_at = models.DateTimeField('完了日時', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'スケジュール'
        verbose_name_plural = 'スケジュール'

    def __str__(self):
        return f'{self.project.name} - {self.field.name}'

    @property
    def duration_days(self):
        """期間（日数）を計算"""
        return (self.end_date - self.start_date).days + 1

    def update_status_by_date(self):
        """現在の日付に基づいてステータスを自動更新（完了以外）"""
        from django.utils import timezone
        
        if self.status == 'completed':
            return  # 完了済みは自動更新しない
            
        today = timezone.now().date()
        
        if today < self.start_date:
            self.status = 'pending'
        elif today >= self.start_date:
            # 開始日以降は終了日を過ぎても進行中のまま（手動完了のみ）
            self.status = 'in_progress'
            
    def toggle_completion(self):
        """完了状態を切り替える"""
        from django.utils import timezone
        
        if self.status == 'completed':
            # 完了から戻す：日付ベースでステータスを設定
            today = timezone.now().date()
            if today < self.start_date:
                self.status = 'pending'
            elif today >= self.start_date:
                # 開始日以降は終了日を過ぎても進行中に戻す
                self.status = 'in_progress'
            self.completed_at = None
        else:
            # 完了にする
            self.status = 'completed'
            self.completed_at = timezone.now()
