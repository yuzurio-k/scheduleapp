from django import forms
from django.contrib.auth import get_user_model
from .models import Project, Schedule, Field

User = get_user_model()

class UserManagementForm(forms.ModelForm):
    """マネージャー用のユーザー管理フォーム"""
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'department', 'phone', 'is_manager', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_manager': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class UserProfileForm(forms.ModelForm):
    """一般ユーザー用のプロフィール編集フォーム"""
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'department', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'manufacturing_number', 'due_date', 'assigned_to', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturing_number': forms.TextInput(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # 担当者の選択肢を設定
            if user.is_manager or user.is_superuser:
                # マネージャーは全ユーザーから選択可能（スーパーユーザー除く）
                self.fields['assigned_to'].queryset = User.objects.filter(is_active=True, is_superuser=False).order_by('last_name', 'first_name', 'username')
            else:
                # 一般ユーザーは自分のみ
                self.fields['assigned_to'].queryset = User.objects.filter(id=user.id)
                self.fields['assigned_to'].widget.attrs['readonly'] = True
            
            # 初期値を現在のユーザーに設定
            if not self.instance.pk:  # 新規作成時のみ
                self.fields['assigned_to'].initial = user

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['project', 'field', 'start_date', 'end_date', 'description']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'field': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 完了状態でない場合は常に日付ベースでステータスを自動設定
        if instance.status != 'completed':
            instance.update_status_by_date()
        
        if commit:
            instance.save()
        return instance

class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '分野名を入力'}),
        }